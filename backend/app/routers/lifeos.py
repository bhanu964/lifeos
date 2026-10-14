import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models.action import (
    ActionExecutionResponse,
    ActionStatus,
    ActionType,
    DraftRequest,
    DraftResponse,
    NotificationTestRequest,
    PlanRequest,
    PlanResponse,
    StagedAction,
    TelegramNotificationRecord,
)
from app.models.workflow import WorkflowRecord
from app.services.action_service import ActionService
from app.services.lyzr_service import LyzrService
from app.services.memory_service import MemoryService
from app.services.notification_service import NotificationService
from app.services.operator_service import OperatorService
from app.services.telegram_service import TelegramService
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["LifeOS Operator"])


def get_lyzr_service() -> LyzrService:
    return LyzrService()


def get_memory_service() -> MemoryService:
    return MemoryService()


def get_telegram_service() -> TelegramService:
    return TelegramService()


def get_notification_service(
    lyzr_service: LyzrService = Depends(get_lyzr_service),
    memory_service: MemoryService = Depends(get_memory_service),
) -> NotificationService:
    return NotificationService(lyzr_service=lyzr_service, memory_service=memory_service)


def get_action_service(
    lyzr_service: LyzrService = Depends(get_lyzr_service),
    memory_service: MemoryService = Depends(get_memory_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> ActionService:
    return ActionService(
        lyzr_service=lyzr_service,
        memory_service=memory_service,
        notification_service=notification_service,
    )


def get_operator_service(
    lyzr_service: LyzrService = Depends(get_lyzr_service),
    memory_service: MemoryService = Depends(get_memory_service),
    action_service: ActionService = Depends(get_action_service),
) -> OperatorService:
    return OperatorService(
        lyzr_service=lyzr_service,
        memory_service=memory_service,
        action_service=action_service,
    )


_workflow_service_instance: Optional[WorkflowService] = None


def get_workflow_service(
    memory_service: MemoryService = Depends(get_memory_service),
    lyzr_service: LyzrService = Depends(get_lyzr_service),
    action_service: ActionService = Depends(get_action_service),
    notification_service: NotificationService = Depends(get_notification_service),
    telegram_service: TelegramService = Depends(get_telegram_service),
) -> WorkflowService:
    global _workflow_service_instance
    if _workflow_service_instance is None:
        _workflow_service_instance = WorkflowService(
            memory_service=memory_service,
            lyzr_service=lyzr_service,
            action_service=action_service,
            notification_service=notification_service,
            telegram_service=telegram_service,
        )
    return _workflow_service_instance


@router.post("/lifeos/plan", response_model=PlanResponse, summary="Generate daily plan and stage action proposals")
async def plan_day(
    request: PlanRequest,
    operator_service: OperatorService = Depends(get_operator_service),
):
    """
    Executes the LifeOS Daily Operator workflow:
    1. Understands user voice/text intent.
    2. Retrieves personal context from Qdrant Cloud.
    3. Reads live Google Calendar events via Composio.
    4. Reads live Google Tasks via Composio.
    5. Lyzr Manager synthesizes an optimal daily plan.
    6. Stages proposed actions with explicit parameters for human approval.
    """
    try:
        return await operator_service.plan_daily_operator(request)
    except Exception as exc:
        logger.error("Error executing LifeOS daily planning: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Planning execution error: {str(exc)}")


@router.post("/lifeos/draft", response_model=DraftResponse, summary="Draft email using personal context and stage action")
async def draft_email(
    request: DraftRequest,
    operator_service: OperatorService = Depends(get_operator_service),
):
    """
    Stages a Gmail draft based on natural language instructions,
    retrieving user context from Qdrant, using Lyzr to format subject and body.
    Requires explicit human confirmation before creating the actual draft in Gmail.
    """
    try:
        return await operator_service.prepare_gmail_draft(request)
    except Exception as exc:
        logger.error("Error drafting email: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Email drafting error: {str(exc)}")


@router.get("/notifications", response_model=List[TelegramNotificationRecord], summary="List recent Telegram notifications")
async def list_notifications(
    limit: int = Query(default=30, ge=1, le=100),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """List real recent notification deliveries and statuses."""
    return notification_service.list_notifications(limit=limit)


@router.post("/notifications/test", response_model=TelegramNotificationRecord, summary="Send test Telegram notification")
async def send_test_notification(
    request: NotificationTestRequest,
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Send a test notification to Telegram to verify integration."""
    import uuid
    fake_action = StagedAction(
        action_id=f"test-{uuid.uuid4().hex[:6]}",
        uid=request.uid,
        action_type=ActionType.CREATE_TASK,
        title=request.message,
        description="Test notification payload for verification",
        parameters={"telegram_chat_id": request.chat_id} if request.chat_id else {},
        expires_at=datetime.now(timezone.utc).isoformat(),
        idempotency_key=f"test:{uuid.uuid4().hex[:8]}",
    )
    return await notification_service.notify_action_success(fake_action, chat_id=request.chat_id)


@router.get("/actions", response_model=List[StagedAction], summary="List staged actions for user")
async def list_actions(
    uid: str = Query(..., min_length=1, description="Authenticated user identifier"),
    action_service: ActionService = Depends(get_action_service),
):
    """List all staged and historical actions belonging to the user."""
    return action_service.list_actions(uid=uid.strip())


@router.get("/actions/{action_id}", response_model=StagedAction, summary="Get details of a staged action")
async def get_action(
    action_id: str,
    uid: str = Query(..., min_length=1, description="Authenticated user identifier"),
    action_service: ActionService = Depends(get_action_service),
):
    """Retrieve details for a single staged action belonging to the user."""
    action = action_service.get_action(action_id=action_id, uid=uid.strip())
    if not action:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found.")
    return action


@router.post("/actions/{action_id}/confirm", response_model=ActionExecutionResponse, summary="Approve and execute a staged action")
async def confirm_action(
    action_id: str,
    uid: str = Query(..., min_length=1, description="Authenticated user identifier"),
    action_service: ActionService = Depends(get_action_service),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    Human-in-the-Loop Confirmation:
    Approves the staged action, verifies parameters, executes the verified integration,
    validates the result, and stores the completion record into Qdrant memory.
    """
    try:
        wf = workflow_service.get_workflow_by_action_id(action_id)
        if wf:
            await workflow_service.handle_telegram_approval(action_id, wf.workflow_id)
            res = next((r for r in wf.action_results if r.action_id == action_id), None)
            if res:
                return res
        return await action_service.confirm_and_execute(action_id=action_id, uid=uid.strip())
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error("Error executing action %s: %s", action_id, exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Integration execution error: {str(exc)}")


@router.post("/actions/{action_id}/reject", response_model=StagedAction, summary="Reject a staged action")
async def reject_action(
    action_id: str,
    uid: str = Query(..., min_length=1, description="Authenticated user identifier"),
    action_service: ActionService = Depends(get_action_service),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Reject and cancel a staged action proposal."""
    try:
        wf = workflow_service.get_workflow_by_action_id(action_id)
        if wf:
            await workflow_service.handle_telegram_rejection(action_id, wf.workflow_id)
        return action_service.reject_action(action_id=action_id, uid=uid.strip())
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.get("/lifeos/status", summary="Get service and integration status")
async def lifeos_status(
    memory_service: MemoryService = Depends(get_memory_service),
    lyzr_service: LyzrService = Depends(get_lyzr_service),
):
    """
    Returns accurate status for all connected integrations without exposing secrets.
    """
    qdrant_healthy = await memory_service.initialize()

    return {
        "status": "healthy",
        "app_name": "LifeOS — Personal AI Operator",
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "integrations": {
            "omi": {
                "status": "connected" if bool(settings.omi_api_key) else "unconfigured",
                "role": "Voice Webhook & Stream Ingestion",
            },
            "qdrant": {
                "status": "connected" if qdrant_healthy else "error",
                "role": "Persistent Personal Memory (384-d Cosine)",
                "collection": settings.qdrant_collection_name,
            },
            "lyzr_multi_agent": {
                "status": "connected" if bool(settings.lyzr_api_key) else "unconfigured",
                "role": "Manager & Specialist Coordination Triad",
                "manager_id": settings.lyzr_manager_agent_id,
            },
            "google_calendar": {
                "status": "connected" if bool(settings.google_calendar_credential_id) else "unconfigured",
                "provider": "Composio on Lyzr",
                "role": "Live Event Reading & Verified Creation",
            },
            "google_tasks": {
                "status": "connected" if bool(settings.google_tasks_credential_id) else "unconfigured",
                "provider": "Composio on Lyzr",
                "role": "Task Listing, Creation & Verification",
            },
            "gmail": {
                "status": "connected" if bool(settings.gmail_credential_id) else "unconfigured",
                "provider": "Composio on Lyzr",
                "role": "Email Reading & Staged Draft Creation",
                "mode": "Drafts Only (Never Auto-Send)",
            },
            "telegram": {
                "status": "connected" if bool(settings.telegram_credential_id) else "unconfigured",
                "provider": "Composio on Lyzr",
                "role": "Operator Notifications for Verified Events",
                "bot_username": settings.telegram_bot_username,
                "chat_id_configured": bool(settings.telegram_chat_id),
            },
            "twitter": {
                "status": "connected",
                "provider": "Composio on Lyzr",
                "role": "Social Updates (Optional)",
            },
        },
    }


# =========================================================================
# WORKFLOW OBSERVABILITY & REAL-TIME EVENT STREAMING (SSE)
# =========================================================================

@router.get("/workflows", response_model=List[WorkflowRecord], summary="List voice-triggered workflows")
async def list_workflows(
    uid: Optional[str] = Query(default=None, description="Optional user ID filter"),
    limit: int = Query(default=30, ge=1, le=100),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Returns recent voice-triggered operator workflows."""
    return workflow_service.list_workflows(user_id=uid, limit=limit)


@router.get("/workflows/latest", response_model=Optional[WorkflowRecord], summary="Get the latest voice workflow")
async def get_latest_workflow(
    uid: Optional[str] = Query(default=None, description="Optional user ID filter"),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Returns the most recent voice workflow."""
    return workflow_service.get_latest_workflow(user_id=uid)


@router.get("/workflows/{workflow_id}", response_model=WorkflowRecord, summary="Get full details of a workflow")
async def get_workflow_details(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Returns full trace, 10-node status, and execution evidence for a workflow."""
    wf = workflow_service.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    return wf


@router.get("/lifeos/events", summary="Server-Sent Events (SSE) stream for live workflow execution updates")
async def stream_workflow_events(
    request: Request,
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    Subscribes to live backend execution updates via Server-Sent Events (SSE).
    Pushes events whenever nodes change, agents complete, actions are staged or approved.
    """
    async def event_generator():
        q = workflow_service.subscribe()
        try:
            # Initial connection acknowledgement
            yield f"event: ping\ndata: {json.dumps({'status': 'connected', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=12.0)
                    yield f"event: message\ndata: {json.dumps(event.model_dump())}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield f"event: ping\ndata: {json.dumps({'keepalive': True})}\n\n"
        finally:
            workflow_service.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =========================================================================
# TELEGRAM BOT WEBHOOK & STATUS
# =========================================================================

@router.post("/telegram/webhook", summary="Telegram Bot webhook update receiver")
async def telegram_webhook(
    request: Request,
    telegram_service: TelegramService = Depends(get_telegram_service),
):
    """
    Receives Telegram updates:
    - callback_query: User tapped [Approve Draft] or [Reject Draft]
    - message: /start registration or clarification reply text
    """
    try:
        data = await request.json()
        result = await telegram_service.handle_update(data)
        return {"ok": True, "result": result}
    except Exception as exc:
        logger.error("Error processing Telegram webhook update: %s", exc, exc_info=True)
        return {"ok": False, "error": str(exc)}


@router.get("/telegram/status", summary="Get Telegram Bot connection and chat ID status")
async def telegram_bot_status(
    telegram_service: TelegramService = Depends(get_telegram_service),
):
    """Returns bot info, effective chat ID, and webhook URL without exposing secrets."""
    effective_chat = telegram_service.get_effective_chat_id()
    return {
        "bot_username": settings.telegram_bot_username,
        "bot_id": "8364330229",
        "has_token": bool(settings.telegram_bot_token),
        "effective_chat_id": effective_chat,
        "discovered_chat_ids": telegram_service._discovered_chat_ids,
        "webhook_url": f"{settings.public_base_url}/api/telegram/webhook",
    }
