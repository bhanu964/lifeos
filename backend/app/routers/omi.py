import logging
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from pydantic import ValidationError

from app.models.omi import (
    ConversationPayload,
    RealtimePayload,
    TranscriptSegment,
    OmiWebhookResponse,
)
from app.services.auth_service import AuthService
from app.services.omi_service import OmiService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/omi", tags=["Omi Webhooks"])


def get_omi_service() -> OmiService:
    """Dependency provider for OmiService."""
    return OmiService()


@router.post("/conversation", response_model=OmiWebhookResponse, summary="Ingest completed Omi conversation")
async def omi_conversation(
    payload: ConversationPayload,
    uid: Optional[str] = Query(default=None, description="Optional user identifier from query string"),
    omi_service: OmiService = Depends(get_omi_service),
):
    """
    Webhook endpoint called when an Omi listening session ends and generates a memory.
    Parses structured insights and transcript segments, and persists them into Qdrant.
    Does not run lengthy LLM reasoning inside the webhook.
    """
    try:
        result = await omi_service.process_conversation_webhook(
            payload=payload,
            uid_param=uid,
        )
        return OmiWebhookResponse(
            status=result["status"],
            message=result["message"],
            processed_count=result["processed_count"],
            memory_id=result.get("memory_id"),
            workflow_id=result.get("workflow_id"),
        )
    except Exception as exc:
        logger.error("Error processing Omi conversation webhook: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process conversation: {str(exc)}")


@router.post("/realtime", response_model=OmiWebhookResponse, summary="Ingest real-time streaming segments")
async def omi_realtime(
    request: Request,
    uid: Optional[str] = Query(default=None, description="User identifier from query string"),
    session_id: Optional[str] = Query(default=None, description="Session identifier from query string"),
    omi_service: OmiService = Depends(get_omi_service),
):
    """
    Webhook endpoint for real-time streaming chunks from Omi.
    Supports both { "session_id": "...", "segments": [...] } payloads and raw segment arrays.
    Deduplicates segments idempotently and stores them in Qdrant.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    segments: List[TranscriptSegment] = []
    active_session_id = session_id

    # Handle body as a dictionary or a list
    if isinstance(body, list):
        for item in body:
            try:
                segments.append(TranscriptSegment.model_validate(item))
            except ValidationError as ve:
                logger.warning("Skipping invalid segment in list: %s", ve)
    elif isinstance(body, dict):
        active_session_id = session_id or body.get("session_id")
        raw_segs = body.get("segments") or body.get("transcript_segments") or []
        for item in raw_segs:
            try:
                segments.append(TranscriptSegment.model_validate(item))
            except ValidationError as ve:
                logger.warning("Skipping invalid segment in dict: %s", ve)
    else:
        raise HTTPException(status_code=400, detail="Payload must be a JSON object or array")

    try:
        result = await omi_service.process_realtime_webhook(
            segments=segments,
            uid_param=uid,
            session_id_param=active_session_id,
        )
        return OmiWebhookResponse(
            status=result["status"],
            message=result["message"],
            processed_count=result["processed_count"],
            session_id=result.get("session_id"),
        )
    except Exception as exc:
        logger.error("Error processing Omi realtime webhook: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process realtime transcript: {str(exc)}")


@router.post("/v2/{webhook_token}/conversation", response_model=OmiWebhookResponse, summary="Ingest Omi conversation for specific user webhook token")
async def omi_conversation_v2(
    webhook_token: str,
    payload: ConversationPayload,
    omi_service: OmiService = Depends(get_omi_service),
):
    """
    Per-user authenticated webhook endpoint for Omi.
    Resolves tenant user from webhook token, ensuring full isolation.
    """
    user = AuthService.get_user_by_omi_token(webhook_token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or revoked Omi webhook token.")

    try:
        result = await omi_service.process_conversation_webhook(
            payload=payload,
            uid_param=user.id,
        )
        return OmiWebhookResponse(
            status=result["status"],
            message=result["message"],
            processed_count=result["processed_count"],
            memory_id=result.get("memory_id"),
            workflow_id=result.get("workflow_id"),
        )
    except Exception as exc:
        logger.error("Error processing Omi v2 conversation webhook for user %s: %s", user.id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process conversation: {str(exc)}")


@router.post("/v2/{webhook_token}/realtime", response_model=OmiWebhookResponse, summary="Ingest Omi realtime segments for specific user webhook token")
async def omi_realtime_v2(
    webhook_token: str,
    request: Request,
    session_id: Optional[str] = Query(default=None),
    omi_service: OmiService = Depends(get_omi_service),
):
    """
    Per-user authenticated realtime streaming endpoint for Omi.
    """
    user = AuthService.get_user_by_omi_token(webhook_token)
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or revoked Omi webhook token.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    segments: List[TranscriptSegment] = []
    active_session_id = session_id

    if isinstance(body, list):
        for item in body:
            try:
                segments.append(TranscriptSegment.model_validate(item))
            except ValidationError as ve:
                logger.warning("Skipping invalid segment in list: %s", ve)
    elif isinstance(body, dict):
        active_session_id = session_id or body.get("session_id")
        raw_segs = body.get("segments") or body.get("transcript_segments") or []
        for item in raw_segs:
            try:
                segments.append(TranscriptSegment.model_validate(item))
            except ValidationError as ve:
                logger.warning("Skipping invalid segment in dict: %s", ve)
    else:
        raise HTTPException(status_code=400, detail="Payload must be a JSON object or array")

    try:
        result = await omi_service.process_realtime_webhook(
            segments=segments,
            uid_param=user.id,
            session_id_param=active_session_id,
        )
        return OmiWebhookResponse(
            status=result["status"],
            message=result["message"],
            processed_count=result["processed_count"],
            session_id=result.get("session_id"),
        )
    except Exception as exc:
        logger.error("Error processing Omi v2 realtime webhook for user %s: %s", user.id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process realtime transcript: {str(exc)}")

