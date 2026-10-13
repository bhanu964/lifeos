import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.action import ActionStatus, ActionType
from app.models.memory import MemoryItem
from app.models.workflow import NodeState, WorkflowRecord, WorkflowStage, WorkflowStatus
from app.services.action_service import ActionService
from app.services.notification_service import NotificationService
from app.services.telegram_service import TelegramService
from app.services.workflow_service import WorkflowService
from app.utils.calendar_utils import (
    calculate_free_time_analysis,
    format_telegram_calendar_report,
    get_day_rfc3339_boundaries,
    resolve_date_from_text,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit Tests for Calendar Utilities
# ---------------------------------------------------------------------------

def test_resolve_date_from_text_tomorrow_and_today():
    today = date.today()
    tomorrow = today + timedelta(days=1)

    d1, s1 = resolve_date_from_text("Check my schedule tomorrow please")
    assert s1 == tomorrow.strftime("%Y-%m-%d")

    d2, s2 = resolve_date_from_text("Do I have anything today?")
    assert s2 == today.strftime("%Y-%m-%d")

    d3, s3 = resolve_date_from_text("Meetings on 2026-11-20")
    assert s3 == "2026-11-20"


def test_get_day_rfc3339_boundaries():
    target = date(2026, 10, 14)
    start_str, end_str = get_day_rfc3339_boundaries(target, tz_name="Asia/Kolkata")
    assert "2026-10-14T00:00:00+05:30" in start_str
    assert "2026-10-14T23:59:59+05:30" in end_str


def test_calculate_free_time_analysis_overlapping_events():
    target_d = date(2026, 10, 14)
    raw_events = [
        # Meeting 1: 10:00 - 11:30
        {
            "summary": "Sprint Planning",
            "start": {"dateTime": "2026-10-14T10:00:00+05:30"},
            "end": {"dateTime": "2026-10-14T11:30:00+05:30"},
        },
        # Meeting 2 (overlapping): 11:00 - 12:00
        {
            "summary": "Architecture Review",
            "start": {"dateTime": "2026-10-14T11:00:00+05:30"},
            "end": {"dateTime": "2026-10-14T12:00:00+05:30"},
        },
        # Meeting 3: 14:00 - 15:00
        {
            "summary": "1:1 Sync",
            "start": {"dateTime": "2026-10-14T14:00:00+05:30"},
            "end": {"dateTime": "2026-10-14T15:00:00+05:30"},
        },
    ]

    analysis = calculate_free_time_analysis(raw_events, target_date=target_d, tz_name="Asia/Kolkata")

    assert analysis["meetings_count"] == 3
    # Overlapping 10:00-12:00 is 2h, and 14:00-15:00 is 1h. Total busy = 3h.
    # Working hours 09:00 - 18:00 = 9h. Total free = 6h (360 min).
    assert analysis["total_free_minutes"] == 360
    assert analysis["total_free_formatted"] in ["6h", "6h 0m"]

    intervals = analysis["free_intervals"]
    assert len(intervals) == 3
    assert "09:00 - 10:00" in intervals[0]
    assert "12:00 - 14:00" in intervals[1]
    assert "15:00 - 18:00" in intervals[2]


def test_calculate_free_time_analysis_empty_calendar():
    target_d = date(2026, 10, 14)
    analysis = calculate_free_time_analysis([], target_date=target_d, tz_name="Asia/Kolkata")
    assert analysis["meetings_count"] == 0
    assert analysis["total_free_minutes"] == 540  # 9 hours
    assert analysis["total_free_formatted"] in ["9h", "9h 0m"]
    assert len(analysis["free_intervals"]) == 1
    assert "09:00 - 18:00" in analysis["free_intervals"][0]


def test_format_telegram_calendar_report_structure():
    sample = {
        "requested_date": "2026-10-14",
        "timezone": "Asia/Kolkata",
        "meetings_count": 1,
        "meetings": [
            {"title": "Demo Review", "start_time": "2026-10-14T11:00:00+05:30", "end_time": "2026-10-14T12:00:00+05:30"}
        ],
        "total_free_formatted": "8h 0m",
        "free_intervals": [
            "09:00 - 11:00 (2h free)",
            "12:00 - 18:00 (6h free)",
        ],
        "status": "success",
    }
    report = format_telegram_calendar_report(sample)
    assert "LifeOS Calendar Report" in report
    assert "2026-10-14" in report
    assert "Demo Review" in report
    assert "8h 0m" in report
    assert "09:00 - 11:00" in report
    assert "Success & Verified" in report


# ---------------------------------------------------------------------------
# Integration Tests for Action Execution & Workflow Pipeline
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pipeline_dependencies():
    with patch("app.services.memory_service.MemoryService.store_memory", new_callable=AsyncMock) as mock_store, \
         patch("app.services.memory_service.MemoryService.search_memories", new_callable=AsyncMock) as mock_search, \
         patch("app.services.lyzr_service.LyzrService.chat", new_callable=AsyncMock) as mock_chat, \
         patch("app.services.lyzr_service.LyzrService.list_calendar_events", new_callable=AsyncMock) as mock_list_cal, \
         patch("app.services.lyzr_service.LyzrService.send_telegram_message", new_callable=AsyncMock) as mock_tg_msg:

        mock_store.side_effect = lambda uid, content, metadata=None: MemoryItem(
            id=f"mock-mem-{datetime.now().microsecond}",
            uid=uid,
            content=content,
            metadata=metadata or {},
        )
        mock_search.return_value = []
        mock_chat.return_value = {"response": "Plan: Read Google Calendar tomorrow and compute free time."}
        mock_list_cal.return_value = [
            {
                "summary": "Team Standup",
                "start": {"dateTime": "2026-10-14T09:30:00+05:30"},
                "end": {"dateTime": "2026-10-14T10:00:00+05:30"},
            }
        ]
        mock_tg_msg.return_value = {
            "successful": True,
            "data": {"ok": True, "result": {"message_id": 9988}},
        }

        yield {
            "store": mock_store,
            "search": mock_search,
            "chat": mock_chat,
            "list_cal": mock_list_cal,
            "tg_msg": mock_tg_msg,
        }


@pytest.mark.asyncio
async def test_action_service_read_calendar_execution(mock_pipeline_dependencies):
    deps = mock_pipeline_dependencies
    action_service = ActionService()

    staged = await action_service.stage_action(
        uid="user-cal-test",
        action_type=ActionType.READ_CALENDAR,
        title="Inspect Google Calendar (2026-10-14)",
        description="Inspect events and compute free time",
        parameters={
            "target_date": "2026-10-14",
            "timezone": "Asia/Kolkata",
            "telegram_chat_id": "12345678",
        },
    )

    res = await action_service.confirm_and_execute(action_id=staged.action_id, uid="user-cal-test")

    assert res.status == ActionStatus.COMPLETED
    assert res.verified is True
    assert res.execution_result is not None
    assert res.execution_result["meetings_count"] == 1
    assert res.execution_result["total_free_formatted"] in ["8h 30m", "510m"]
    assert res.notification is not None
    assert res.notification["status"] == "delivered"
    assert res.notification["message_id"] == 9988

    # Check that memory was stored
    assert deps["store"].await_count >= 1


@pytest.mark.asyncio
async def test_voice_workflow_executes_calendar_request_and_completes(mock_pipeline_dependencies):
    """
    Test the critical bug scenario:
    Voice request asks to inspect Google Calendar for tomorrow.
    Verifies that READ_CALENDAR is staged and executed autonomously,
    calendar results are populated, Telegram message is dispatched,
    and workflow successfully completes.
    """
    deps = mock_pipeline_dependencies
    wf_service = WorkflowService()
    # Configure user telegram chat id in service state
    wf_service.telegram.register_chat_id("98765432", uid="user-voice-cal")

    transcript = "Check my Google calendar for tomorrow. Tell me what meetings I have and how much free time is available."
    workflow = await wf_service.create_and_enqueue_workflow(
        uid="user-voice-cal",
        conversation_id=f"conv-cal-001-{uuid.uuid4().hex[:6]}",
        transcript=transcript,
    )

    # Allow async pipeline execution to finish
    await asyncio.sleep(0.1)

    updated_wf = wf_service.get_workflow(workflow.workflow_id)
    assert updated_wf is not None
    assert updated_wf.status == WorkflowStatus.COMPLETED
    assert updated_wf.current_stage == WorkflowStage.COMPLETED

    # Verify calendar result populated
    assert updated_wf.calendar_result is not None
    assert updated_wf.calendar_result["meetings_count"] == 1
    assert updated_wf.calendar_result["total_free_formatted"] in ["8h 30m", "510m"]

    # Verify Telegram delivery record populated
    assert updated_wf.telegram_delivery is not None
    assert updated_wf.telegram_delivery["status"] == "delivered"
    assert updated_wf.telegram_delivery["message_id"] == 9988

    # Verify integrations executed node
    node_ie = updated_wf.nodes["integrations_executing"]
    assert node_ie.state == NodeState.COMPLETED
    assert len(updated_wf.action_results) >= 1
    cal_action = updated_wf.action_results[0]
    assert cal_action.verified is True

    # Verify Lyzr calendar list was called
    deps["list_cal"].assert_awaited_once()
    # Verify Telegram notification was sent
    deps["tg_msg"].assert_awaited_once()


@pytest.mark.asyncio
async def test_voice_workflow_calendar_needs_configuration_when_no_chat_id(mock_pipeline_dependencies):
    """
    When no Telegram chat ID is registered, calendar inspection should still run,
    but the workflow must report NEEDS_CONFIGURATION (never COMPLETED).
    """
    deps = mock_pipeline_dependencies
    wf_service = WorkflowService()
    # Clear any discovered chat IDs and ensure effective chat ID is None
    with patch.object(settings, "telegram_chat_id", None), \
         patch.object(wf_service.telegram, "get_effective_chat_id", return_value=None):

        transcript = "Check my Google calendar for tomorrow and tell me my free time."
        workflow = await wf_service.create_and_enqueue_workflow(
            uid="user-no-chat",
            conversation_id=f"conv-cal-no-chat-{uuid.uuid4().hex[:6]}",
            transcript=transcript,
        )

        await asyncio.sleep(0.1)

        updated_wf = wf_service.get_workflow(workflow.workflow_id)
        assert updated_wf is not None
        assert updated_wf.status == WorkflowStatus.NEEDS_CONFIGURATION
        assert updated_wf.current_stage == WorkflowStage.NEEDS_CONFIGURATION
        assert updated_wf.calendar_result is not None
        assert updated_wf.telegram_delivery is not None
        assert updated_wf.telegram_delivery["status"] == "NEEDS_CONFIGURATION"


@pytest.mark.asyncio
async def test_voice_workflow_calendar_fails_when_telegram_delivery_fails(mock_pipeline_dependencies):
    """
    When Telegram delivery fails with an error, the workflow must report DELIVERY_FAILED (never COMPLETED).
    """
    deps = mock_pipeline_dependencies
    deps["tg_msg"].return_value = {"successful": False, "error": "Bot was blocked by the user"}

    wf_service = WorkflowService()
    wf_service.telegram.register_chat_id("11223344", uid="user-fail-tg")

    transcript = "Check my calendar tomorrow and report on Telegram."
    workflow = await wf_service.create_and_enqueue_workflow(
        uid="user-fail-tg",
        conversation_id=f"conv-cal-fail-tg-{uuid.uuid4().hex[:6]}",
        transcript=transcript,
    )

    await asyncio.sleep(0.1)

    updated_wf = wf_service.get_workflow(workflow.workflow_id)
    assert updated_wf is not None
    assert updated_wf.status == WorkflowStatus.DELIVERY_FAILED
    assert updated_wf.current_stage == WorkflowStage.DELIVERY_FAILED


@pytest.mark.asyncio
async def test_voice_workflow_calendar_fails_when_calendar_api_errors(mock_pipeline_dependencies):
    """
    When the Google Calendar API call fails, the workflow must report FAILED (never COMPLETED).
    """
    deps = mock_pipeline_dependencies
    deps["list_cal"].side_effect = RuntimeError("Google Calendar API quota exceeded or connection timeout")

    wf_service = WorkflowService()
    wf_service.telegram.register_chat_id("11223344", uid="user-fail-cal")

    transcript = "Check my calendar tomorrow."
    workflow = await wf_service.create_and_enqueue_workflow(
        uid="user-fail-cal",
        conversation_id=f"conv-cal-api-err-{uuid.uuid4().hex[:6]}",
        transcript=transcript,
    )

    await asyncio.sleep(0.1)

    updated_wf = wf_service.get_workflow(workflow.workflow_id)
    assert updated_wf is not None
    assert updated_wf.status == WorkflowStatus.FAILED
    assert updated_wf.current_stage == WorkflowStage.FAILED
