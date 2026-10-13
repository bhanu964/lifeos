from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.models.action import ActionStatus, ActionType, DraftRequest, StagedAction
from app.models.memory import MemoryItem
from app.routers.lifeos import (
    get_action_service,
    get_lyzr_service,
    get_memory_service,
    get_notification_service,
    get_operator_service,
)
from app.services.action_service import ActionService
from app.services.lyzr_service import LyzrService
from app.services.memory_service import MemoryService
from app.services.notification_service import NotificationService
from app.services.operator_service import OperatorService


@pytest.fixture
def mock_gmail_telegram_dependencies():
    mock_lyzr = MagicMock(spec=LyzrService)
    mock_lyzr.chat = AsyncMock(
        return_value={
            "response": "Subject: LifeOS Project Demo Ready\nBody:\nHi teammate, the demo is ready for review.",
            "agent_id": "6acdcd0f8a6a8741bd6df3df",
        }
    )
    mock_lyzr.list_calendar_events = AsyncMock(return_value=[])
    mock_lyzr.list_tasks = AsyncMock(return_value=[])
    mock_lyzr.create_task = AsyncMock(
        return_value={"id": "task-xyz-789", "title": "Finish hackathon demo", "successful": True}
    )
    mock_lyzr.create_gmail_draft = AsyncMock(
        return_value={
            "successful": True,
            "data": {
                "id": "draft-12345",
                "display_url": "https://mail.google.com/mail/u/0/#drafts/draft-12345",
                "message": {"id": "msg-999", "labelIds": ["DRAFT"]},
            },
        }
    )
    mock_lyzr.list_gmail_drafts = AsyncMock(
        return_value={
            "successful": True,
            "data": {"drafts": [{"id": "draft-12345"}]},
        }
    )
    mock_lyzr.send_telegram_message = AsyncMock(
        return_value={
            "successful": True,
            "data": {"ok": True, "result": {"message_id": 42}},
        }
    )
    mock_lyzr.get_telegram_bot_info = AsyncMock(
        return_value={
            "successful": True,
            "data": {"ok": True, "result": {"id": 8364330229, "username": "Ididhswkje_bot"}},
        }
    )

    mock_memory = MagicMock(spec=MemoryService)
    mock_memory.search_memories = AsyncMock(
        return_value=[
            MemoryItem(
                id="mem-1",
                uid="test-user",
                content="Teammate email is teammate@lifeos.ai. We need them to review the demo.",
                score=0.88,
            )
        ]
    )
    mock_memory.format_memories_for_prompt = MagicMock(
        return_value="[Memory #1] Teammate email is teammate@lifeos.ai."
    )
    mock_memory.store_memory = AsyncMock(
        return_value=MemoryItem(
            id="mem-draft-done",
            uid="test-user",
            content="LifeOS Verified Gmail Draft Created",
        )
    )
    mock_memory.initialize = AsyncMock(return_value=True)

    notification_service = NotificationService(lyzr_service=mock_lyzr, memory_service=mock_memory)
    action_service = ActionService(
        lyzr_service=mock_lyzr,
        memory_service=mock_memory,
        notification_service=notification_service,
    )
    operator_service = OperatorService(
        lyzr_service=mock_lyzr,
        memory_service=mock_memory,
        action_service=action_service,
    )

    return {
        "lyzr": mock_lyzr,
        "memory": mock_memory,
        "notification": notification_service,
        "actions": action_service,
        "operator": operator_service,
    }


@pytest.mark.asyncio
async def test_gmail_draft_staging_and_parameter_validation(mock_gmail_telegram_dependencies):
    action_service = mock_gmail_telegram_dependencies["actions"]

    staged = await action_service.stage_action(
        uid="user-test",
        action_type=ActionType.CREATE_GMAIL_DRAFT,
        title="Draft email to teammate",
        description="Demo ready for review",
        parameters={
            "recipient_email": "teammate@lifeos.ai",
            "subject": "LifeOS Demo Review",
            "body": "Hi, please review the demo tomorrow.",
        },
    )

    assert staged.action_id.startswith("act-")
    assert staged.action_type == ActionType.CREATE_GMAIL_DRAFT
    assert staged.status == ActionStatus.STAGED
    assert staged.parameters["recipient_email"] == "teammate@lifeos.ai"
    assert staged.parameters["subject"] == "LifeOS Demo Review"


@pytest.mark.asyncio
async def test_gmail_draft_missing_or_invalid_recipient_fails(mock_gmail_telegram_dependencies):
    action_service = mock_gmail_telegram_dependencies["actions"]

    # Invalid recipient without @
    staged = await action_service.stage_action(
        uid="user-test",
        action_type=ActionType.CREATE_GMAIL_DRAFT,
        title="Invalid email draft",
        description="Missing @",
        parameters={
            "recipient_email": "invalid-email-address",
            "subject": "Test",
            "body": "Hello",
        },
    )

    with pytest.raises(ValueError, match="Invalid or missing recipient email address"):
        await action_service.confirm_and_execute(action_id=staged.action_id, uid="user-test")


@pytest.mark.asyncio
async def test_gmail_draft_approval_and_verification(mock_gmail_telegram_dependencies):
    deps = mock_gmail_telegram_dependencies
    action_service = deps["actions"]

    staged = await action_service.stage_action(
        uid="user-test",
        action_type=ActionType.CREATE_GMAIL_DRAFT,
        title="Draft review email",
        description="Demo ready for review",
        parameters={
            "recipient_email": "teammate@lifeos.ai",
            "subject": "Demo Ready for Review",
            "body": "Hi teammate, please review.",
        },
    )

    app.dependency_overrides[get_action_service] = lambda: action_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(f"/api/actions/{staged.action_id}/confirm?uid=user-test")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert data["verified"] is True
        assert data["memory_id"] is not None

        # Verify Gmail tool was called with draft creation parameters
        deps["lyzr"].create_gmail_draft.assert_awaited_once_with(
            recipient_email="teammate@lifeos.ai",
            subject="Demo Ready for Review",
            body="Hi teammate, please review.",
            is_html=False,
        )

        # Verify Qdrant memory loopback
        deps["memory"].store_memory.assert_awaited()
        action_stored_calls = [
            c.kwargs for c in deps["memory"].store_memory.call_args_list
            if "LifeOS Verified Gmail Draft Created" in c.kwargs.get("content", "")
        ]
        assert len(action_stored_calls) >= 1
        assert action_stored_calls[0]["metadata"]["action_type"] == "create_gmail_draft"
        assert action_stored_calls[0]["metadata"]["verified"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_gmail_draft_rejection_never_calls_integration(mock_gmail_telegram_dependencies):
    deps = mock_gmail_telegram_dependencies
    action_service = deps["actions"]

    staged = await action_service.stage_action(
        uid="user-test",
        action_type=ActionType.CREATE_GMAIL_DRAFT,
        title="Unwanted draft",
        description="Spam draft",
        parameters={"recipient_email": "teammate@lifeos.ai"},
    )

    app.dependency_overrides[get_action_service] = lambda: action_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(f"/api/actions/{staged.action_id}/reject?uid=user-test")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "rejected"

        # Verify create_gmail_draft was NEVER called
        deps["lyzr"].create_gmail_draft.assert_not_awaited()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_telegram_notification_on_verified_success(mock_gmail_telegram_dependencies):
    deps = mock_gmail_telegram_dependencies
    action_service = deps["actions"]

    staged = await action_service.stage_action(
        uid="user-test",
        action_type=ActionType.CREATE_TASK,
        title="Finish hackathon demo",
        description="Deliver LifeOS presentation",
        parameters={"title": "Finish hackathon demo", "telegram_chat_id": "123456789"},
    )

    app.dependency_overrides[get_action_service] = lambda: action_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(f"/api/actions/{staged.action_id}/confirm?uid=user-test")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert data["notification"] is not None
        assert data["notification"]["status"] == "delivered"
        assert "LifeOS: Your Google Task was created and verified." in data["notification"]["text"]

        # Verify telegram message was sent with exact chat_id
        deps["lyzr"].send_telegram_message.assert_awaited_once()
        tg_args = deps["lyzr"].send_telegram_message.call_args.kwargs
        assert tg_args["chat_id"] == "123456789"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_telegram_notification_skipped_cleanly_when_no_chat_id(mock_gmail_telegram_dependencies, monkeypatch):
    deps = mock_gmail_telegram_dependencies
    action_service = deps["actions"]
    monkeypatch.setattr(settings, "telegram_chat_id", None)

    staged = await action_service.stage_action(
        uid="user-test",
        action_type=ActionType.CREATE_TASK,
        title="Task without Telegram chat id",
        description="No chat ID",
        parameters={"title": "Task without Telegram chat id"},
    )

    app.dependency_overrides[get_action_service] = lambda: action_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(f"/api/actions/{staged.action_id}/confirm?uid=user-test")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        # Notification was recorded as skipped without error
        assert data["notification"]["status"] == "skipped_no_chat_id"
        deps["lyzr"].send_telegram_message.assert_not_awaited()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_telegram_notification_duplicate_prevention(mock_gmail_telegram_dependencies):
    deps = mock_gmail_telegram_dependencies
    notification_service = deps["notification"]

    action = StagedAction(
        action_id="act-unique-test-1",
        uid="user-test",
        action_type=ActionType.CREATE_TASK,
        title="Demo task",
        description="Demo description",
        parameters={"telegram_chat_id": "123456789"},
        expires_at=datetime.now(timezone.utc).isoformat(),
        idempotency_key="unique-key-1",
    )

    # First send
    notif1 = await notification_service.notify_action_success(action, chat_id="123456789")
    assert notif1.status == "delivered"
    assert deps["lyzr"].send_telegram_message.await_count == 1

    # Second send for same action - must skip sending to Telegram API
    notif2 = await notification_service.notify_action_success(action, chat_id="123456789")
    assert notif2.notification_id == notif1.notification_id
    assert deps["lyzr"].send_telegram_message.await_count == 1  # Still 1


@pytest.mark.asyncio
async def test_combined_workflow_calendar_task_draft(mock_gmail_telegram_dependencies):
    deps = mock_gmail_telegram_dependencies
    operator_service = deps["operator"]

    app.dependency_overrides[get_operator_service] = lambda: operator_service

    # Natural language instruction requesting plan, task, draft, and notification
    payload = {
        "uid": "user-test",
        "prompt": "Check my calendar for tomorrow, prepare my daily plan, create a task for the project demo, draft an email asking my teammate to review it, and notify me on Telegram when the task is created.",
        "target_date": "2026-10-14",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/lifeos/plan", json=payload)
        assert res.status_code == 200
        data = res.json()

        staged_types = [a["action_type"] for a in data["staged_actions"]]
        assert ActionType.CREATE_TASK.value in staged_types
        assert ActionType.CREATE_GMAIL_DRAFT.value in staged_types

        # Find draft action
        draft_action = next(a for a in data["staged_actions"] if a["action_type"] == ActionType.CREATE_GMAIL_DRAFT.value)
        assert "review" in draft_action["title"].lower() or "email" in draft_action["title"].lower()
        assert "@" in draft_action["parameters"]["recipient_email"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_lifeos_draft_endpoint(mock_gmail_telegram_dependencies):
    deps = mock_gmail_telegram_dependencies
    app.dependency_overrides[get_operator_service] = lambda: deps["operator"]

    payload = {
        "uid": "user-test",
        "prompt": "Draft an email to teammate@lifeos.ai asking them to review the demo tomorrow.",
        "recipient_email": "teammate@lifeos.ai",
        "subject": "Demo Review Request",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/lifeos/draft", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["uid"] == "user-test"
        assert data["staged_action"]["action_type"] == "create_gmail_draft"
        assert data["staged_action"]["parameters"]["recipient_email"] == "teammate@lifeos.ai"
        assert data["staged_action"]["parameters"]["subject"] == "Demo Review Request"
        assert len(data["context_used"]) > 0

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_notifications_listing_endpoint(mock_gmail_telegram_dependencies):
    deps = mock_gmail_telegram_dependencies
    app.dependency_overrides[get_notification_service] = lambda: deps["notification"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/notifications?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    app.dependency_overrides.clear()
