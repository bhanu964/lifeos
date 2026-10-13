from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.action import ActionStatus, ActionType, StagedAction
from app.models.memory import MemoryItem
from app.routers.lifeos import get_action_service, get_lyzr_service, get_memory_service, get_operator_service
from app.services.action_service import ActionService
from app.services.lyzr_service import LyzrService
from app.services.memory_service import MemoryService
from app.services.operator_service import OperatorService


@pytest.fixture
def mock_operator_dependencies():
    mock_lyzr = MagicMock(spec=LyzrService)
    mock_lyzr.chat = AsyncMock(
        return_value={
            "response": "Here is your optimized daily plan for tomorrow. Focus on hackathon demo and presentation.",
            "agent_id": "6acdcd0f8a6a8741bd6df3df",
        }
    )
    mock_lyzr.list_calendar_events = AsyncMock(
        return_value=[
            {
                "id": "cal-1",
                "summary": "Team Sync",
                "start": {"dateTime": "2026-10-14T10:00:00Z"},
                "end": {"dateTime": "2026-10-14T10:30:00Z"},
                "description": "Daily standup",
            }
        ]
    )
    mock_lyzr.list_tasks = AsyncMock(
        return_value=[
            {
                "id": "task-1",
                "title": "Review codebase",
                "status": "needsAction",
            }
        ]
    )
    mock_lyzr.create_task = AsyncMock(
        return_value={"id": "new-task-123", "title": "Finish hackathon demo", "successful": True}
    )
    mock_lyzr.create_calendar_event = AsyncMock(
        return_value={"id": "new-event-456", "summary": "Hackathon Demo Prep", "successful": True}
    )

    mock_memory = MagicMock(spec=MemoryService)
    mock_memory.search_memories = AsyncMock(
        return_value=[
            MemoryItem(
                id="mem-1",
                uid="test-user",
                content="Need to finish the hackathon demo by tomorrow.",
                score=0.85,
            )
        ]
    )
    mock_memory.format_memories_for_prompt = MagicMock(
        return_value="[Memory #1] Need to finish the hackathon demo by tomorrow."
    )
    mock_memory.store_memory = AsyncMock(
        return_value=MemoryItem(
            id="mem-action-done",
            uid="test-user",
            content="LifeOS Verified Task Completed",
        )
    )
    mock_memory.initialize = AsyncMock(return_value=True)

    action_service = ActionService(lyzr_service=mock_lyzr, memory_service=mock_memory)
    operator_service = OperatorService(
        lyzr_service=mock_lyzr,
        memory_service=mock_memory,
        action_service=action_service,
    )

    return {
        "lyzr": mock_lyzr,
        "memory": mock_memory,
        "actions": action_service,
        "operator": operator_service,
    }


@pytest.mark.asyncio
async def test_lifeos_status_endpoint(mock_operator_dependencies):
    deps = mock_operator_dependencies
    app.dependency_overrides[get_memory_service] = lambda: deps["memory"]
    app.dependency_overrides[get_lyzr_service] = lambda: deps["lyzr"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/lifeos/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "integrations" in data
        assert data["integrations"]["google_calendar"]["status"] == "connected"
        assert data["integrations"]["google_tasks"]["status"] == "connected"
        assert data["integrations"]["qdrant"]["status"] == "connected"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_lifeos_plan_endpoint(mock_operator_dependencies):
    deps = mock_operator_dependencies
    app.dependency_overrides[get_operator_service] = lambda: deps["operator"]

    payload = {
        "uid": "test-user",
        "prompt": "Plan my day for tomorrow. Check my calendar, find free time, and create tasks for hackathon demo.",
        "target_date": "2026-10-14",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/lifeos/plan", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["uid"] == "test-user"
        assert data["target_date"] == "2026-10-14"
        assert len(data["existing_events"]) == 1
        assert data["existing_events"][0]["summary"] == "Team Sync"
        assert len(data["pending_tasks"]) == 1
        assert len(data["suggested_slots"]) == 3
        assert len(data["staged_actions"]) == 2

        # Check telemetry events
        steps = [e["step"] for e in data["execution_events"]]
        assert "request_validation" in steps
        assert "personal_context_retrieval" in steps
        assert "calendar_reading" in steps
        assert "task_reading" in steps
        assert "manager_orchestration" in steps
        assert "action_staging" in steps

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_action_staging_and_idempotency(mock_operator_dependencies):
    action_service = mock_operator_dependencies["actions"]

    act1 = await action_service.stage_action(
        uid="user-a",
        action_type=ActionType.CREATE_TASK,
        title="Deploy frontend",
        description="Run npm build and deploy",
        parameters={"title": "Deploy frontend"},
    )
    assert act1.status == ActionStatus.STAGED

    # Duplicate call with same parameters should return the same staged action (idempotent)
    act2 = await action_service.stage_action(
        uid="user-a",
        action_type=ActionType.CREATE_TASK,
        title="Deploy frontend",
        description="Run npm build and deploy",
        parameters={"title": "Deploy frontend"},
    )
    assert act1.action_id == act2.action_id


@pytest.mark.asyncio
async def test_action_confirm_execution_and_memory_loop(mock_operator_dependencies):
    deps = mock_operator_dependencies
    action_service = deps["actions"]

    staged = await action_service.stage_action(
        uid="user-a",
        action_type=ActionType.CREATE_TASK,
        title="Record 5-minute video",
        description="Walk through full LifeOS voice workflow",
        parameters={"title": "Record 5-minute video"},
    )

    app.dependency_overrides[get_action_service] = lambda: action_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # User confirms action
        res = await client.post(f"/api/actions/{staged.action_id}/confirm?uid=user-a")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert data["verified"] is True
        assert data["memory_id"] is not None

        # Verify Qdrant memory service was called to store completion record
        deps["memory"].store_memory.assert_awaited_once()
        stored_kwargs = deps["memory"].store_memory.call_args.kwargs
        assert stored_kwargs["uid"] == "user-a"
        assert "LifeOS Verified Task Completed" in stored_kwargs["content"]
        assert stored_kwargs["metadata"]["verified"] is True

        # Verify executing again fails (already completed)
        res_repeat = await client.post(f"/api/actions/{staged.action_id}/confirm?uid=user-a")
        assert res_repeat.status_code == 400

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_action_rejection(mock_operator_dependencies):
    deps = mock_operator_dependencies
    action_service = deps["actions"]

    staged = await action_service.stage_action(
        uid="user-a",
        action_type=ActionType.CREATE_TASK,
        title="Optional errand",
        description="Buy notebook",
        parameters={"title": "Optional errand"},
    )

    app.dependency_overrides[get_action_service] = lambda: action_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(f"/api/actions/{staged.action_id}/reject?uid=user-a")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "rejected"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_user_isolation_prevent_cross_tenant_action_access(mock_operator_dependencies):
    deps = mock_operator_dependencies
    action_service = deps["actions"]

    staged = await action_service.stage_action(
        uid="user-a",
        action_type=ActionType.CREATE_TASK,
        title="Confidential meeting prep",
        description="Review NDA",
        parameters={"title": "Confidential meeting prep"},
    )

    app.dependency_overrides[get_action_service] = lambda: action_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Other user cannot access or approve user-a's action
        res_get = await client.get(f"/api/actions/{staged.action_id}?uid=attacker-user")
        assert res_get.status_code == 404

        res_confirm = await client.post(f"/api/actions/{staged.action_id}/confirm?uid=attacker-user")
        assert res_confirm.status_code == 400

    app.dependency_overrides.clear()
