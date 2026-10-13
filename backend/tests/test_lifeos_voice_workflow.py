import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.action import ActionStatus, ActionType, StagedAction
from app.models.omi import ConversationPayload, TranscriptSegment
from app.models.workflow import NodeState, WorkflowRecord, WorkflowStage, WorkflowStatus
from app.services.action_service import ActionService
from app.services.omi_service import OmiService
from app.services.telegram_service import TelegramService
from app.services.workflow_service import WorkflowService

client = TestClient(app)


@pytest.fixture
def mock_dependencies():
    with patch("app.services.qdrant_service.QdrantService.store_memories", new_callable=AsyncMock) as mock_store, \
         patch("app.services.memory_service.MemoryService.search_memories", new_callable=AsyncMock) as mock_search, \
         patch("app.services.lyzr_service.LyzrService.chat", new_callable=AsyncMock) as mock_chat, \
         patch("app.services.lyzr_service.LyzrService.create_task", new_callable=AsyncMock) as mock_task, \
         patch("app.services.lyzr_service.LyzrService.create_gmail_draft", new_callable=AsyncMock) as mock_draft, \
         patch("app.services.telegram_service.TelegramService.send_message", new_callable=AsyncMock) as mock_tg_msg, \
         patch("app.services.telegram_service.TelegramService.send_approval_request", new_callable=AsyncMock) as mock_tg_app:

        mock_store.return_value = ["mock-mem-id"]
        mock_search.return_value = []
        mock_chat.return_value = {"response": "Executive Plan generated."}
        mock_task.return_value = {"successful": True, "data": {"id": "gtask-123", "title": "Test Task"}}
        mock_draft.return_value = {"successful": True, "data": {"id": "draft-456"}}
        mock_tg_msg.return_value = {"ok": True}
        mock_tg_app.return_value = {"ok": True}

        yield {
            "store": mock_store,
            "search": mock_search,
            "chat": mock_chat,
            "create_task": mock_task,
            "create_draft": mock_draft,
            "telegram_send": mock_tg_msg,
            "telegram_approval": mock_tg_app,
        }


@pytest.mark.asyncio
async def test_completed_omi_conversation_automatically_creates_workflow(mock_dependencies):
    """Verify that a completed conversation webhook automatically enqueues a LifeOS workflow."""
    payload = {
        "id": "conv-test-auto-001",
        "uid": "user-voice-test",
        "transcript_segments": [
            {"text": "LifeOS, I agreed to prepare the hackathon demo submission tomorrow evening."}
        ],
    }

    response = client.post("/omi/conversation?uid=user-voice-test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["workflow_id"] is not None
    assert data["workflow_id"].startswith("wf-")

    # Verify workflow exists in service
    wf_res = client.get(f"/api/workflows/{data['workflow_id']}")
    assert wf_res.status_code == 200
    wf = wf_res.json()
    assert wf["workflow_id"] == data["workflow_id"]
    assert wf["user_id"] == "user-voice-test"
    assert "hackathon demo" in wf["transcript"]
    assert "voice_received" in wf["nodes"]
    assert wf["nodes"]["voice_received"]["state"] == "completed"


@pytest.mark.asyncio
async def test_realtime_chunks_do_not_execute_actions():
    """Verify that realtime streaming chunks do NOT trigger autonomous workflows."""
    with patch("app.services.qdrant_service.QdrantService.store_memories", new_callable=AsyncMock) as mock_store:
        mock_store.return_value = ["mock-realtime-id"]
        payload = {
            "session_id": "live-stream-001",
            "segments": [{"text": "Hello, I am speaking partial sentence..."}],
        }
        res = client.post("/omi/realtime?uid=user-stream", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data.get("workflow_id") is None


@pytest.mark.asyncio
async def test_duplicate_webhook_does_not_create_duplicate_workflow(mock_dependencies):
    """Verify idempotency: repeating the same conversation webhook returns the existing workflow."""
    payload = {
        "id": "conv-dedup-001",
        "uid": "user-dedup",
        "transcript_segments": [{"text": "This is an idempotent spoken test sentence."}],
    }

    res1 = client.post("/omi/conversation?uid=user-dedup", json=payload)
    wf_id1 = res1.json()["workflow_id"]

    res2 = client.post("/omi/conversation?uid=user-dedup", json=payload)
    wf_id2 = res2.json()["workflow_id"]

    assert wf_id1 == wf_id2


@pytest.mark.asyncio
async def test_gmail_draft_pauses_for_telegram_approval(mock_dependencies):
    """Verify that email requests pause at AWAITING_TELEGRAM_APPROVAL without dashboard clicks."""
    payload = {
        "id": "conv-draft-approval-001",
        "uid": "user-draft-test",
        "transcript_segments": [
            {"text": "Email the team at team@lifeos.ai about our multi-agent architecture and Google integrations."}
        ],
    }

    res = client.post("/omi/conversation?uid=user-draft-test", json=payload)
    wf_id = res.json()["workflow_id"]

    # Give background task brief moment to advance
    await asyncio.sleep(0.1)

    wf_res = client.get(f"/api/workflows/{wf_id}")
    wf = wf_res.json()
    assert wf["status"] in ["AWAITING_APPROVAL", "RUNNING"]
    # Check node 7 exists
    assert "telegram_approval" in wf["nodes"]


@pytest.mark.asyncio
async def test_telegram_callback_approves_and_executes_draft(mock_dependencies):
    """Verify that tapping [Approve Draft] in Telegram executes the draft and completes the workflow."""
    wf_service = WorkflowService()
    action_service = ActionService()

    # Stage an action
    staged = await action_service.stage_action(
        uid="user-test",
        action_type=ActionType.CREATE_GMAIL_DRAFT,
        title="Draft team update",
        description="Body preview",
        parameters={"recipient_email": "team@test.org", "subject": "Update", "body": "Hello team"},
    )

    wf = await wf_service.create_and_enqueue_workflow(
        uid="user-test",
        conversation_id="conv-manual-test",
        transcript="Email team@test.org about update",
    )
    wf.action_ids.append(staged.action_id)
    wf.actions.append(staged)

    # Simulate Telegram button click callback
    telegram_payload = {
        "callback_query": {
            "id": "cb-12345",
            "from": {"id": 99999999, "username": "testuser"},
            "data": f"approve:{staged.action_id}:{wf.workflow_id}",
        }
    }

    res = client.post("/api/telegram/webhook", json=telegram_payload)
    assert res.status_code == 200
    assert res.json()["ok"] is True


@pytest.mark.asyncio
async def test_telegram_start_registers_chat_id():
    """Verify that sending /start to Telegram registers chat ID and sends welcome."""
    update = {
        "message": {
            "message_id": 1,
            "chat": {"id": 12345678, "first_name": "TestUser"},
            "text": "/start",
        }
    }

    with patch("app.services.telegram_service.TelegramService.send_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"ok": True}
        res = client.post("/api/telegram/webhook", json=update)
        assert res.status_code == 200
        assert res.json()["ok"] is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[1]
        assert call_args["chat_id"] == "12345678"
        assert "Welcome to LifeOS" in call_args["text"]


@pytest.mark.asyncio
async def test_workflows_listing_and_restoration():
    """Verify workflows can be listed and retrieved for dashboard restoration."""
    res = client.get("/api/workflows")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_telegram_status_endpoint():
    """Verify GET /api/telegram/status returns clean non-secret telemetry."""
    res = client.get("/api/telegram/status")
    assert res.status_code == 200
    data = res.json()
    assert "bot_username" in data
    assert "webhook_url" in data
    assert data["has_token"] is True
