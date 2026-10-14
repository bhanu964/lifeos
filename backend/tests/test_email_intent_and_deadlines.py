import asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.action import ActionStatus, ActionType
from app.models.workflow import NodeState, WorkflowRecord, WorkflowStage, WorkflowStatus
from app.services.action_service import ActionService
from app.services.email_intent_service import (
    extract_deadlines_from_emails,
    extract_email_fields,
    extract_task_details,
    format_telegram_execution_report,
    is_calendar_inspect_intent,
    is_calendar_schedule_intent,
    is_explicit_email_draft_intent,
    is_read_emails_intent,
    is_summarize_emails_intent,
    normalize_voice_transcript,
    summarize_recent_emails,
)
from app.services.lyzr_service import LyzrService
from app.services.workflow_service import WorkflowService

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit Tests for Intent Classification & Deadline Extraction
# ---------------------------------------------------------------------------

def test_intent_classification_reading_vs_drafting():
    """Verify that email checking requests never match draft intent."""
    voice_input = (
        "Uh check my last twenty-four hours emails. And let me know if there are important "
        "deadlines. And if there is any deadline, update that in my Google Calendar, like schedule it, "
        "and inform me. Eh through the telegram."
    )
    assert is_read_emails_intent(voice_input) is True
    assert is_calendar_schedule_intent(voice_input) is True
    assert is_calendar_inspect_intent(voice_input) is False
    assert is_explicit_email_draft_intent(voice_input) is False

    read_only_inputs = [
        "Check my emails for today",
        "Read my unread messages in inbox",
        "Search emails from Sarah",
        "Summarize emails from the last 24 hours",
        "Do I have any urgent emails?",
    ]
    for inp in read_only_inputs:
        assert is_read_emails_intent(inp) is True
        assert is_explicit_email_draft_intent(inp) is False, f"Failed for '{inp}'"

    explicit_draft_inputs = [
        "Draft an email to client@example.com about the project kickoff",
        "Compose an email to team@company.com",
        "Send an email to supervisor@test.org with the weekly report",
        "Write an email to alex@partner.com",
        "Email the team at team@lifeos.ai about our multi-agent architecture",
    ]
    for inp in explicit_draft_inputs:
        assert is_explicit_email_draft_intent(inp) is True, f"Failed for '{inp}'"


def test_deadline_extraction_identifies_deadlines_accurately():
    """Verify extraction of deadlines from email subjects and snippets."""
    mock_emails = [
        {
            "id": "msg-001",
            "subject": "Hackathon Project Submission Reminder",
            "snippet": "Hi participants, final submission deadline is tomorrow at 5:00 PM.",
            "body": "Ensure your video and repo are submitted before the deadline.",
        },
        {
            "id": "msg-002",
            "subject": "Weekly Newsletter",
            "snippet": "Here are this week's top AI papers.",
            "body": "No action required.",
        },
        {
            "id": "msg-003",
            "subject": "Invoice 1042 Due Date",
            "snippet": "Please pay your invoice due by 2026-10-25 18:00.",
            "body": "Payment link attached.",
        },
    ]

    deadlines = extract_deadlines_from_emails(mock_emails, tz_name="Asia/Kolkata")
    assert len(deadlines) == 2

    # Check first deadline
    d1 = deadlines[0]
    assert "Hackathon Project Submission Reminder" in d1["title"]
    assert "tomorrow" in d1["description"] or "17:00:00" in d1["start_datetime"]
    assert d1["source_email_id"] == "msg-001"

    # Check second deadline
    d2 = deadlines[1]
    assert "Invoice 1042 Due Date" in d2["title"]
    assert "2026-10-25T18:00:00" in d2["start_datetime"]
    assert d2["source_email_id"] == "msg-003"


def test_deadline_extraction_returns_empty_when_no_deadlines():
    """Verify empty list returned when emails contain no deadlines."""
    mock_emails = [
        {
            "id": "msg-101",
            "subject": "Welcome to the service",
            "snippet": "Thanks for signing up for our updates.",
        },
        {
            "id": "msg-102",
            "subject": "Coffee chat tomorrow?",
            "snippet": "Hey let's catch up tomorrow for lunch if you're free.",
        },
    ]
    deadlines = extract_deadlines_from_emails(mock_emails, tz_name="Asia/Kolkata")
    assert len(deadlines) == 0


# ---------------------------------------------------------------------------
# End-to-End Workflow Regression Tests (Requirements A - F)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_all_services():
    with patch("app.services.qdrant_service.QdrantService.store_memories", new_callable=AsyncMock) as mock_qdrant_store, \
         patch("app.services.memory_service.MemoryService.search_memories", new_callable=AsyncMock) as mock_mem_search, \
         patch("app.services.memory_service.MemoryService.store_memory", new_callable=AsyncMock) as mock_mem_store, \
         patch("app.services.lyzr_service.LyzrService.chat", new_callable=AsyncMock) as mock_chat, \
         patch("app.services.lyzr_service.LyzrService.list_recent_emails", new_callable=AsyncMock) as mock_list_emails, \
         patch("app.services.lyzr_service.LyzrService.create_calendar_event", new_callable=AsyncMock) as mock_create_event, \
         patch("app.services.lyzr_service.LyzrService.create_task", new_callable=AsyncMock) as mock_create_task, \
         patch("app.services.lyzr_service.LyzrService.create_gmail_draft", new_callable=AsyncMock) as mock_create_draft, \
         patch("app.services.telegram_service.TelegramService.send_message", new_callable=AsyncMock) as mock_tg_msg, \
         patch("app.services.telegram_service.TelegramService.send_approval_request", new_callable=AsyncMock) as mock_tg_approval, \
         patch("app.services.lyzr_service.LyzrService.send_telegram_message", new_callable=AsyncMock) as mock_lyzr_tg_msg, \
         patch("app.services.user_credentials_service.UserCredentialsService.is_using_preconfigured_lyzr", return_value=False):

        mock_qdrant_store.return_value = ["mock-qdrant-id"]
        mock_mem_search.return_value = []
        mock_mem_store.return_value = AsyncMock(id="mem-12345", model_dump=lambda: {"id": "mem-12345"})
        mock_chat.return_value = {"response": "Plan formulated: Inspect emails, identify deadlines, schedule on calendar."}
        mock_create_event.return_value = {"successful": True, "data": {"id": "cal-evt-123"}}
        mock_create_task.return_value = {"successful": True, "data": {"id": "task-mock-123"}}
        mock_create_draft.return_value = {"successful": True, "data": {"id": "draft-789"}}
        mock_tg_msg.return_value = {"ok": True, "message_id": 9999}
        mock_tg_approval.return_value = {"ok": True, "message_id": 8888}
        mock_lyzr_tg_msg.return_value = {"ok": True, "message_id": 7777}

        yield {
            "list_emails": mock_list_emails,
            "create_event": mock_create_event,
            "create_task": mock_create_task,
            "create_draft": mock_create_draft,
            "tg_msg": mock_tg_msg,
            "tg_approval": mock_tg_approval,
            "chat": mock_chat,
            "mem_store": mock_mem_store,
        }


@pytest.mark.asyncio
async def test_regression_a_checking_emails_never_creates_draft(mock_all_services):
    """
    Test A: 'Check my last 24 hours of emails...' must NEVER create or stage an email draft.
    Mentioning 'email' as a source of information is read-only.
    Never invent recipients (such as team@stop-prompting.org or teammate@lifeos.ai).
    """
    deps = mock_all_services
    deps["list_emails"].return_value = [
        {
            "id": "email-01",
            "subject": "Hackathon Submission Deadline",
            "snippet": "Reminder: Submission deadline is tomorrow at 5:00 PM.",
        }
    ]

    wf_service = WorkflowService()
    transcript = (
        "Uh check my last twenty-four hours emails. And let me know if there are important "
        "deadlines. And if there is any deadline, update that in my Google Calendar, like schedule it, "
        "and inform me. Eh through the telegram."
    )

    wf = await wf_service.create_and_enqueue_workflow(
        uid="usr_evaluator_001",
        conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
        transcript=transcript,
    )

    await asyncio.sleep(0.15)
    updated_wf = wf_service.get_workflow(wf.workflow_id)

    assert updated_wf is not None
    # 1. Verify CREATE_GMAIL_DRAFT was never staged
    staged_types = [a.action_type for a in updated_wf.actions]
    assert ActionType.CREATE_GMAIL_DRAFT not in staged_types

    # 2. Verify neither mock address was assigned as a recipient
    for a in updated_wf.actions:
        assert "stop-prompting.org" not in str(a.parameters)
        assert "teammate@lifeos.ai" not in str(a.parameters)

    # 3. Verify node 7 (Telegram Approval) was skipped rather than awaiting approval
    node_ta = updated_wf.nodes["telegram_approval"]
    assert node_ta.state == NodeState.SKIPPED
    assert "No high-risk operations requiring approval" in (node_ta.summary or "")

    # 4. Verify create_gmail_draft tool was never called
    deps["create_draft"].assert_not_called()


@pytest.mark.asyncio
async def test_regression_b_workflow_reads_emails_and_extracts_deadlines(mock_all_services):
    """
    Test B: Workflow reads emails from previous 24h, extracts actual deadlines,
    and schedules Google Calendar events.
    """
    deps = mock_all_services
    deps["list_emails"].return_value = [
        {
            "id": "email-dl-1",
            "subject": "Project Proposal Submission Due",
            "snippet": "The submission deadline is tomorrow at 6:00 PM. Please be on time.",
        }
    ]

    wf_service = WorkflowService()
    wf_service.telegram.register_chat_id("12345678", uid="usr_evaluator_002")

    transcript = (
        "Check my last 24 hours of emails, find important deadlines, schedule them in Google Calendar, "
        "and notify me on Telegram."
    )

    wf = await wf_service.create_and_enqueue_workflow(
        uid="usr_evaluator_002",
        conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
        transcript=transcript,
    )

    await asyncio.sleep(0.15)
    updated_wf = wf_service.get_workflow(wf.workflow_id)

    assert updated_wf is not None
    # Verify emails were retrieved
    deps["list_emails"].assert_awaited_once_with(hours=24)

    # Verify calendar event was created for the deadline
    assert deps["create_event"].await_count >= 1

    # Verify calendar_result was populated with deadline details
    assert updated_wf.calendar_result is not None
    assert updated_wf.calendar_result["status"] == "DEADLINES_SCHEDULED"
    assert updated_wf.calendar_result["deadlines_count"] == 1

    # Verify workflow completed
    assert updated_wf.status == WorkflowStatus.COMPLETED
    assert updated_wf.current_stage == WorkflowStage.COMPLETED


@pytest.mark.asyncio
async def test_regression_c_explicit_email_draft_request_still_works(mock_all_services):
    """
    Test C: Explicit request to draft an email still works, staging CREATE_GMAIL_DRAFT
    and pausing at Stage 7 AWAITING_TELEGRAM_APPROVAL.
    """
    deps = mock_all_services
    wf_service = WorkflowService()

    transcript = "Draft an email to partner@venture.com asking for feedback on our pitch deck."
    wf = await wf_service.create_and_enqueue_workflow(
        uid="usr_evaluator_003",
        conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
        transcript=transcript,
    )

    await asyncio.sleep(0.15)
    updated_wf = wf_service.get_workflow(wf.workflow_id)

    assert updated_wf is not None
    assert updated_wf.status == WorkflowStatus.AWAITING_APPROVAL
    assert updated_wf.current_stage == WorkflowStage.AWAITING_TELEGRAM_APPROVAL

    # Verify draft action staged with recipient
    draft_actions = [a for a in updated_wf.actions if a.action_type == ActionType.CREATE_GMAIL_DRAFT]
    assert len(draft_actions) == 1
    assert draft_actions[0].parameters["recipient_email"] == "partner@venture.com"

    # Verify Telegram approval request was dispatched
    deps["tg_approval"].assert_awaited_once()


@pytest.mark.asyncio
async def test_regression_d_explicit_send_requires_approval_and_executes(mock_all_services):
    """
    Test D: Explicit draft/send request requires Telegram button approval before execution.
    """
    deps = mock_all_services
    wf_service = WorkflowService()
    action_service = ActionService()

    staged = await action_service.stage_action(
        uid="usr_evaluator_004",
        action_type=ActionType.CREATE_GMAIL_DRAFT,
        title="Draft follow-up email",
        description="Preview of email",
        parameters={
            "recipient_email": "founder@startup.io",
            "subject": "Follow up",
            "body": "Checking in on the integration.",
        },
    )

    wf = await wf_service.create_and_enqueue_workflow(
        uid="usr_evaluator_004",
        conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
        transcript="Send an email to founder@startup.io with the integration update.",
    )
    wf.action_ids.append(staged.action_id)
    wf.actions.append(staged)

    # Simulate Telegram callback approval
    callback_payload = {
        "callback_query": {
            "id": "cb-reg-001",
            "from": {"id": 12345, "username": "operator_user"},
            "data": f"approve:{staged.action_id}:{wf.workflow_id}",
        }
    }

    res = client.post("/api/telegram/webhook", json=callback_payload)
    assert res.status_code == 200
    assert res.json()["ok"] is True

    # Verify draft was created after explicit human approval
    deps["create_draft"].assert_awaited_once()


@pytest.mark.asyncio
async def test_regression_e_unpaired_telegram_produces_configuration_warning(mock_all_services):
    """
    Test E: Unpaired Telegram produces clear configuration warning without falsely reporting delivery
    or failing the whole workflow during safe autonomous operations.
    """
    deps = mock_all_services
    wf_service = WorkflowService()
    deps["list_emails"].return_value = []

    # Ensure no chat ID is registered
    with patch.object(wf_service.telegram, "get_effective_chat_id", return_value=None):
        transcript = (
            "Check my last 24 hours of emails. Identify important deadlines, add them to Google Calendar "
            "if necessary, and notify me through Telegram."
        )

        wf = await wf_service.create_and_enqueue_workflow(
            uid="usr_unpaired_tg",
            conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
            transcript=transcript,
        )

        await asyncio.sleep(0.15)
        updated_wf = wf_service.get_workflow(wf.workflow_id)

        assert updated_wf is not None
        # Must NOT falsely claim delivered
        assert updated_wf.telegram_delivery is not None
        assert updated_wf.telegram_delivery["status"] == "NEEDS_CONFIGURATION"
        assert "not linked" in updated_wf.telegram_delivery.get("message", "").lower()

        # The workflow should successfully complete autonomous execution without aborting
        assert updated_wf.status in [WorkflowStatus.COMPLETED, WorkflowStatus.NEEDS_CONFIGURATION]
        assert updated_wf.nodes["completed"].state == NodeState.COMPLETED


@pytest.mark.asyncio
async def test_regression_f_no_deadlines_does_not_create_calendar_events(mock_all_services):
    """
    Test F: When emails contain no deadlines, workflow does NOT create calendar events.
    Reports clean summary.
    """
    deps = mock_all_services
    deps["list_emails"].return_value = [
        {
            "id": "email-safe-1",
            "subject": "Team Lunch Photos",
            "snippet": "Here are the photos from yesterday's team lunch.",
        },
        {
            "id": "email-safe-2",
            "subject": "Platform Maintenance Notice",
            "snippet": "Scheduled routine maintenance completed successfully.",
        },
    ]

    wf_service = WorkflowService()
    transcript = (
        "Check my last 24 hours of emails. If there are any deadlines, schedule them in Google Calendar."
    )

    wf = await wf_service.create_and_enqueue_workflow(
        uid="usr_evaluator_006",
        conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
        transcript=transcript,
    )

    await asyncio.sleep(0.15)
    updated_wf = wf_service.get_workflow(wf.workflow_id)

    assert updated_wf is not None
    # 1. Verify emails were checked
    deps["list_emails"].assert_awaited_once_with(hours=24)

    # 2. Verify no calendar events were created
    deps["create_event"].assert_not_called()
    cal_actions = [a for a in updated_wf.actions if a.action_type == ActionType.CREATE_CALENDAR_EVENT]
    assert len(cal_actions) == 0

    # 3. Verify clean summary in calendar_result
    assert updated_wf.calendar_result is not None
    assert updated_wf.calendar_result["status"] == "NO_DEADLINES_FOUND"
    assert updated_wf.calendar_result["deadlines_count"] == 0
    assert "No actionable deadlines found" in updated_wf.calendar_result["summary"]


@pytest.mark.asyncio
async def test_preconfigured_lyzr_disables_gmail_read_and_draft(mock_all_services):
    """
    Verify that in Preconfigured Lyzr mode, reading Gmail and drafting emails
    are completely disabled to protect developer account privacy.
    """
    deps = mock_all_services
    wf_service = WorkflowService()

    with patch("app.services.user_credentials_service.UserCredentialsService.is_using_preconfigured_lyzr", return_value=True):
        # 1. Test Email Reading in Preconfigured mode
        wf1 = await wf_service.create_and_enqueue_workflow(
            uid="usr_preconfigured_user",
            conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
            transcript="Check my last 24 hours of emails for deadlines.",
        )
        await asyncio.sleep(0.15)
        updated_wf1 = wf_service.get_workflow(wf1.workflow_id)

        assert updated_wf1 is not None
        # Verify list_emails was NOT called
        deps["list_emails"].assert_not_called()
        assert updated_wf1.calendar_result is not None
        assert updated_wf1.calendar_result["status"] == "GMAIL_DISABLED_IN_PRECONFIGURED_MODE"
        assert "disabled in Preconfigured Lyzr mode" in updated_wf1.calendar_result["summary"]

        # 2. Test Email Drafting in Preconfigured mode
        wf2 = await wf_service.create_and_enqueue_workflow(
            uid="usr_preconfigured_user",
            conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
            transcript="Draft an email to partner@test.com about the project.",
        )
        await asyncio.sleep(0.15)
        updated_wf2 = wf_service.get_workflow(wf2.workflow_id)

        assert updated_wf2 is not None
        deps["create_draft"].assert_not_called()
        node_ta = updated_wf2.nodes["telegram_approval"]
        assert node_ta.state == NodeState.SKIPPED
        assert "disabled in Preconfigured Lyzr mode" in (node_ta.summary or "")


def test_summarize_emails_intent_and_formatting():
    """Verify intent recognition and zero-emoji structured summary generation."""
    t1 = "Check my last twenty-four hours emails. Is there any important deadlines? Uh let me know. and summarize all the emails and send it through the Telegram."
    assert is_summarize_emails_intent(t1) is True
    assert is_summarize_emails_intent("What is the weather today?") is False

    # Empty email list
    assert "No new emails" in summarize_recent_emails([])

    # Formatted email list
    emails = [
        {
            "id": "e1",
            "subject": "Hackathon Project Update",
            "from": "organizer@stop-prompting.org",
            "snippet": "Reminder that submissions close tomorrow at 5pm. Please finish your code.",
        },
        {
            "id": "e2",
            "subject": "Cloud Platform Billing",
            "from": "billing@cloud.io",
            "snippet": "Your monthly invoice is ready.",
        },
    ]
    summary = summarize_recent_emails(emails)
    assert "1. Hackathon Project Update (From: organizer@stop-prompting.org)" in summary
    assert "2. Cloud Platform Billing (From: billing@cloud.io)" in summary
    # Assert zero emojis
    assert not any(ord(c) > 127999 for c in summary)


def test_google_payload_headers_extraction():
    """Verify extraction of subject, sender, and deadlines from Google API nested payload.headers format."""
    google_api_msg = {
        "id": "google-msg-123",
        "snippet": "Hackathon submission deadline is tomorrow at 5:00 PM.",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Fwd: Hackathon Submission Deadline"},
                {"name": "From", "value": "lead@hackathon.org"},
                {"name": "Date", "value": "Wed, 14 Oct 2026 12:00:00 +0000"},
            ],
            "body": {"data": "Body content"},
        },
    }
    fields = extract_email_fields(google_api_msg)
    assert fields["subject"] == "Fwd: Hackathon Submission Deadline"
    assert fields["sender"] == "lead@hackathon.org"
    assert "Hackathon submission deadline" in fields["snippet"]

    deadlines = extract_deadlines_from_emails([google_api_msg], tz_name="Asia/Kolkata")
    assert len(deadlines) == 1
    assert "Hackathon Submission Deadline" in deadlines[0]["title"]
    assert deadlines[0]["source_email_id"] == "google-msg-123"


def test_format_telegram_execution_report():
    """Verify structured human-readable Telegram report formatting without emojis."""
    transcript = "Check my last twenty-four hours emails. Is there any important deadlines? Uh let me know. and summarize all the emails and send it through the Telegram."
    cal_res = {
        "status": "DEADLINES_SCHEDULED",
        "checked_emails": 2,
        "deadlines_count": 1,
        "deadlines": [
            {
                "title": "Deadline: Hackathon Submission",
                "start_datetime": "2026-10-15T17:00:00+05:30",
            }
        ],
        "email_summary": "1. Hackathon Project Update (From: lead@hackathon.org)\n   Summary: Submissions close tomorrow.",
        "summary": "Identified 1 deadline(s) in emails. Successfully scheduled to Google Calendar.",
    }
    report = format_telegram_execution_report(transcript=transcript, calendar_result=cal_res)
    assert "LifeOS Execution Report" in report
    assert "Spoken Request:" in report
    assert "Email Summary (Last 24 Hours):" in report
    assert "Hackathon Project Update" in report
    assert "Important Deadlines & Google Calendar:" in report
    assert "Deadline: Hackathon Submission (Scheduled: 2026-10-15T17:00:00+05:30)" in report
    assert "Outcome:" in report
    assert "Identified 1 deadline(s)" in report
    # Strictly zero emojis
    assert not any(ord(c) > 127999 for c in report)


@pytest.mark.asyncio
async def test_lyzr_service_list_recent_emails_parsing_and_fallback():
    """Verify that list_recent_emails parses nested Composio structures and handles dual parameters."""
    lyzr = LyzrService(api_key="mock-key", agent_id="mock-agent", is_preconfigured=False)

    nested_composio_response = {
        "tool_name": "GMAIL_LIST_MESSAGES",
        "result": {
            "successful": True,
            "data": {
                "response_data": {
                    "messages": [
                        {
                            "id": "msg-nested-1",
                            "subject": "Important Project Review",
                            "from": "manager@company.com",
                            "snippet": "Please review the document by tomorrow at 4pm.",
                        }
                    ]
                }
            },
        },
    }

    with patch.object(lyzr, "execute_tool", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = nested_composio_response
        emails = await lyzr.list_recent_emails(hours=24)
        assert len(emails) == 1
        assert emails[0]["id"] == "msg-nested-1"

        # Verify dual-parameter arguments were supplied
        call_args = mock_exec.call_args[1]["arguments"]
        assert "q" in call_args
        assert "query" in call_args
        assert "maxResults" in call_args
        assert "max_results" in call_args
        assert "newer_than:1d" in call_args["q"]


@pytest.mark.asyncio
async def test_workflow_telegram_report_contains_email_summary(mock_all_services):
    """
    Verify end-to-end that when the user asks to check and summarize emails,
    the Telegram message dispatched contains the email summary, deadlines, and outcome.
    """
    deps = mock_all_services
    deps["list_emails"].return_value = [
        {
            "id": "email-dl-1",
            "subject": "Hackathon Submission Deadline",
            "from": "organizer@hackathon.org",
            "snippet": "Reminder: Submission deadline is tomorrow at 5:00 PM.",
        }
    ]

    wf_service = WorkflowService()
    transcript = (
        "Check my last twenty-four hours emails. Is there any important deadlines? Uh let me know. "
        "and summarize all the emails and send it through the Telegram. "
        "And if there are any important deadlines, update that in the Google Calendar."
    )

    with patch("app.services.telegram_service.TelegramService.get_effective_chat_id", return_value="12345678"):
        wf = await wf_service.create_and_enqueue_workflow(
            uid="usr_evaluator_007",
            conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
            transcript=transcript,
        )

        await asyncio.sleep(0.15)
        updated_wf = wf_service.get_workflow(wf.workflow_id)

        assert updated_wf is not None
        assert updated_wf.status == WorkflowStatus.COMPLETED

        # Verify Telegram message was sent
        assert deps["tg_msg"].await_count >= 1
        tg_call_args = deps["tg_msg"].call_args[1]
        sent_text = tg_call_args["text"]

        assert "LifeOS Execution Report" in sent_text
        assert "Email Summary (Last 24 Hours):" in sent_text
        assert "Hackathon Submission Deadline" in sent_text
        assert "organizer@hackathon.org" in sent_text
        assert "Important Deadlines & Google Calendar:" in sent_text
        assert "Outcome:" in sent_text
        # Assert strictly zero emojis
        assert not any(ord(c) > 127999 for c in sent_text)


def test_normalize_voice_transcript_speech_artifacts():
    """Verify normalization of mobile Whisper phonetic mishearings."""
    raw = (
        "Check my last twenty four hour females and let me know is there any important deadlines. "
        "If there are any important deadlines, update in the Google calendar, like say Julie, "
        "then inform me in the telegram. Line give the summarization in the telegram."
    )
    normalized = normalize_voice_transcript(raw)
    assert "last 24 hour emails" in normalized
    assert "schedule it" in normalized
    assert "summarization" in normalized

    # Additional common voice artifacts
    assert "emails" in normalize_voice_transcript("check females")
    assert "email inbox" in normalize_voice_transcript("female inbox")
    assert "emails" in normalize_voice_transcript("read my e-mails")


def test_production_reported_voice_transcript_intent_and_deadlines():
    """
    Verify intent classification on exact evaluator transcript:
    'Check my last twenty four hour females and let me know is there any important deadlines...'
    """
    transcript = (
        "Check my last twenty four hour females and let me know is there any important deadlines. "
        "If there are any important deadlines, update in the Google calendar, like say Julie, "
        "then inform me in the telegram. Line give the summarization in the telegram."
    )
    plan = (
        "The user’s spoken request is about checking the last 24 hours of emails for important deadlines "
        "and updating the Google Calendar accordingly, then providing a summary and notification via Telegram."
    )

    # 1. Intent without plan summary (via phonetic STT correction)
    assert is_read_emails_intent(transcript) is True
    assert is_calendar_schedule_intent(transcript) is True
    assert is_summarize_emails_intent(transcript) is True
    assert is_explicit_email_draft_intent(transcript) is False

    # 2. Intent with plan summary fallback
    assert is_read_emails_intent(transcript, plan_summary=plan) is True
    assert is_calendar_schedule_intent(transcript, plan_summary=plan) is True
    assert is_summarize_emails_intent(transcript, plan_summary=plan) is True


def test_format_telegram_execution_report_with_plan_summary_and_empty_emails():
    """Verify that even when 0 emails or deadlines are found, the report clearly articulates sections and outcome."""
    transcript = "Check my last 24 hour emails for deadlines and schedule it in Google Calendar."
    plan = "Check last 24 hours of emails for important deadlines and schedule any found events."
    cal_res = {
        "status": "NO_DEADLINES_FOUND",
        "checked_emails": 0,
        "deadlines_count": 0,
        "deadlines": [],
        "email_summary": "No new or unread emails found in the last 24 hours.",
        "summary": "Checked recent emails. No actionable deadlines found.",
    }

    report = format_telegram_execution_report(
        transcript=transcript,
        calendar_result=cal_res,
        plan_summary=plan,
    )

    assert "LifeOS Execution Report" in report
    assert "Email Summary (Last 24 Hours):" in report
    assert "No new or unread emails found" in report
    assert "Important Deadlines & Google Calendar:" in report
    assert "No actionable deadlines detected" in report
    assert "Outcome:" in report
    assert "No actionable deadlines found" in report
    assert not any(ord(c) > 127999 for c in report)


@pytest.mark.asyncio
async def test_stage_9_qdrant_timeout_resilience(mock_all_services):
    """
    Verify that if Qdrant Cloud or ONNX memory commit times out in Stage 9,
    the workflow gracefully degrades, logs a warning, completes Stage 9 and finishes Stage 10
    without getting permanently stuck in RUNNING or failing the user experience.
    """
    deps = mock_all_services
    deps["mem_store"].side_effect = asyncio.TimeoutError("Qdrant cloud timed out after 5.0s")

    wf_service = WorkflowService()
    transcript = "Check my last 24 hours emails for deadlines."

    wf = await wf_service.create_and_enqueue_workflow(
        uid="usr_evaluator_resilience",
        conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
        transcript=transcript,
    )

    await asyncio.sleep(0.15)
    updated_wf = wf_service.get_workflow(wf.workflow_id)

    assert updated_wf is not None
    # Workflow must successfully complete Stage 9 & Stage 10 despite Qdrant timeout
    assert updated_wf.status == WorkflowStatus.COMPLETED
    assert updated_wf.current_stage == WorkflowStage.COMPLETED

    node_mu = updated_wf.nodes["memory_updated"]
    assert node_mu.state == NodeState.COMPLETED
    assert "Memory commit bypassed" in node_mu.summary

    node_cp = updated_wf.nodes["completed"]
    assert node_cp.state == NodeState.COMPLETED


def test_extract_task_details_marathon_and_speech_artifacts():
    """Verify accurate task title and due date extraction from spoken input and plan summary."""
    # 1. Marathon voice request with plan summary
    transcript1 = "Tomorrow six pм. Going to marathon, add this in the Google Tasks."
    plan1 = (
        "UNDERSTAND\n- User requested: Tomorrow six p.m. Going to marathon.\n"
        "EXECUTE\n- Intended task to add: “Going to marathon”\n- Intended due time: tomorrow at 6 p.m."
    )
    details1 = extract_task_details(transcript1, plan_summary=plan1)
    assert details1["title"] == "Going to marathon"
    assert "Z" in details1["due"]
    assert "Tomorrow six pм" in details1["notes"]

    # 2. Marathon voice request without plan summary (pure transcript parsing with Cyrillic m)
    details2 = extract_task_details(transcript1)
    assert details2["title"] == "Going to marathon"
    assert "Z" in details2["due"]

    # 3. Explicit title directive: 'make it as a hackathon submission title'
    transcript3 = "Add a task for the Google tasks. Uh today 9 p.m. Hakathon submission. Make it as a hackathon submission title and add the task in the Google Tasks."
    details3 = extract_task_details(transcript3)
    assert details3["title"] == "Hackathon submission"

    # 4. Directive: 'assign a task in the Google tasks like uh nine a.m. running marathon'
    transcript4 = "Tomorrow morning, nine AM I has the running marathon. So uh assign a task in the Google tasks like uh nine a.m. running marathon."
    details4 = extract_task_details(transcript4)
    assert "running marathon" in details4["title"].lower()


@pytest.mark.asyncio
async def test_workflow_executes_dynamic_marathon_task(mock_all_services):
    """
    Verify end-to-end that when the user speaks:
    'Tomorrow six pм. Going to marathon, add this in the Google Tasks.'
    the staged and executed action creates a task titled 'Going to marathon' (never hardcoded hackathon),
    executes Google Tasks, and successfully completes without failing.
    """
    deps = mock_all_services
    deps["chat"].return_value = {
        "response": (
            "UNDERSTAND\n- User requested: Tomorrow six p.m. Going to marathon.\n"
            "PLAN\n- Create a Google Tasks entry for marathon reminder tomorrow at 6 p.m.\n"
            "EXECUTE\n- Intended task to add: “Going to marathon”\n- Intended due time: tomorrow at 6 p.m."
        )
    }

    wf_service = WorkflowService()
    transcript = "Tomorrow six pм. Going to marathon, add this in the Google Tasks."

    with patch("app.services.telegram_service.TelegramService.get_effective_chat_id", return_value="12345678"):
        wf = await wf_service.create_and_enqueue_workflow(
            uid="usr_evaluator_marathon",
            conversation_id=f"conv-{uuid.uuid4().hex[:8]}",
            transcript=transcript,
        )

        await asyncio.sleep(0.2)
        updated_wf = wf_service.get_workflow(wf.workflow_id)

        assert updated_wf is not None
        assert updated_wf.status == WorkflowStatus.COMPLETED

        # Verify an action was staged and executed
        assert len(updated_wf.actions) >= 1
        staged_task = updated_wf.actions[0]
        assert staged_task.action_type == ActionType.CREATE_TASK
        assert staged_task.title == "Going to marathon"
        assert staged_task.title != "Prepare Stop Prompting Hackathon project submission"

        # Verify Lyzr Google Tasks tool was called with dynamic title
        assert deps["create_task"].await_count >= 1
        call_kwargs = deps["create_task"].call_args[1]
        assert call_kwargs["title"] == "Going to marathon"
        assert "due" in call_kwargs
        assert "Z" in call_kwargs["due"]

        # Verify action result was recorded
        assert len(updated_wf.action_results) >= 1
        assert updated_wf.action_results[0].status == ActionStatus.COMPLETED




