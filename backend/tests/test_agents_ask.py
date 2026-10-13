import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.main import app
from app.models.memory import MemoryItem
from app.routers.agents import get_lyzr_service, get_memory_service
from app.services.lyzr_service import LyzrAPIError, LyzrService
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_ask_agent_with_relevant_memories(mock_lyzr_service):
    memory_service = MemoryService(qdrant_service=AsyncMock())
    memories = [
        MemoryItem(
            id="mem-1",
            uid="demo-user",
            content="Alex agreed to write the Qdrant connector documentation.",
            score=0.88,
            metadata={"speaker": "Alex", "source": "omi_voice"},
            created_at="2026-10-13T08:00:00Z",
        )
    ]
    memory_service.search_memories = AsyncMock(return_value=memories)

    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_lyzr_service] = lambda: mock_lyzr_service

    payload = {
        "uid": "demo-user",
        "question": "Who is writing the documentation?",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/ask", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert len(data["supporting_memories"]) == 1
        assert data["supporting_memories"][0]["id"] == "mem-1"
        assert len(data["execution_events"]) >= 3

        # Verify execution trace contains collaborative multi-agent steps
        step_names = [e["step"] for e in data["execution_events"]]
        assert "request_validation" in step_names
        assert "memory_retrieval" in step_names
        assert "prompt_synthesis" in step_names
        assert "fact_finder_agent" in step_names
        assert "data_analyst_agent" in step_names
        assert "agent_reasoning" in step_names
        assert "final_response" in step_names

        # Verify all specialist agents were coordinated (Fact Finder, Data Analyst, Manager)
        assert mock_lyzr_service.chat.await_count == 3
        first_call_kwargs = mock_lyzr_service.chat.call_args_list[0].kwargs
        assert "Alex agreed to write the Qdrant connector documentation" in first_call_kwargs["message"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ask_agent_when_no_memories_found(mock_lyzr_service):
    memory_service = MemoryService(qdrant_service=AsyncMock())
    # No memories found in Qdrant
    memory_service.search_memories = AsyncMock(return_value=[])

    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_lyzr_service] = lambda: mock_lyzr_service

    payload = {
        "uid": "demo-user",
        "question": "What did I discuss regarding quantum computing?",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/ask", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["supporting_memories"] == []

        # Check prompt sent to Fact Finder clearly indicates absence of memories
        first_call_kwargs = mock_lyzr_service.chat.call_args_list[0].kwargs
        assert "NO RELEVANT MEMORIES FOUND" in first_call_kwargs["message"]

        # Check execution event records the absence
        prompt_event = next(e for e in data["execution_events"] if e["step"] == "prompt_synthesis")
        assert prompt_event["details"]["status"] == "NO_RELEVANT_MEMORIES"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ask_agent_validation_errors():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing question
        res1 = await client.post("/api/ask", json={"uid": "user-1", "question": "   "})
        assert res1.status_code == 400

        # Missing uid
        res2 = await client.post("/api/ask", json={"uid": "", "question": "Hello"})
        assert res2.status_code in (400, 422)


@pytest.mark.asyncio
async def test_ask_agent_lyzr_api_failure_handling():
    memory_service = MemoryService(qdrant_service=AsyncMock())
    memory_service.search_memories = AsyncMock(return_value=[])

    failing_lyzr = LyzrService(api_key="fake-key")
    failing_lyzr.chat = AsyncMock(
        side_effect=LyzrAPIError("Lyzr upstream service unavailable", status_code=503)
    )

    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_lyzr_service] = lambda: failing_lyzr

    payload = {
        "uid": "demo-user",
        "question": "Will this fail gracefully?",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/ask", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert "Lyzr Agent Error" in data["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_multi_agent_collaboration_specialist_outputs(mock_lyzr_service):
    """
    Verifies that both specialist agents (Fact Finder, Data Analyst) and Manager
    contribute distinct real outputs to the final result and telemetry.
    """
    memory_service = MemoryService(qdrant_service=AsyncMock())
    memories = [
        MemoryItem(
            id="mem-42",
            uid="demo-user",
            content="We decided to use Qdrant for 384-d memory and Lyzr for agent reasoning.",
            score=0.92,
            metadata={"source": "omi_voice"},
            created_at="2026-10-13T09:00:00Z",
        )
    ]
    memory_service.search_memories = AsyncMock(return_value=memories)

    # Return distinct outputs per call
    mock_lyzr_service.chat = AsyncMock(
        side_effect=[
            {"response": "FACTS: Qdrant used for 384-d memory, Lyzr used for reasoning.", "agent_id": "6acd9f07cb0aafc9293bd126"},
            {"response": "ANALYSIS: 2 core technical decisions confirmed. No missing items.", "agent_id": "6acd1ec70b4f09cf4da21e21"},
            {"response": "Your project uses Qdrant for vector memory and Lyzr for multi-agent reasoning.", "agent_id": "6acdcd0f8a6a8741bd6df3df"},
        ]
    )

    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_lyzr_service] = lambda: mock_lyzr_service

    payload = {"uid": "demo-user", "question": "What architecture decisions did we make?"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/ask", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "specialist_outputs" in data
        assert "FACTS: Qdrant used" in data["specialist_outputs"]["fact_finder"]
        assert "ANALYSIS: 2 core" in data["specialist_outputs"]["data_analyst"]
        assert data["agent_id"] == "6acdcd0f8a6a8741bd6df3df"
        assert "Qdrant for vector memory" in data["answer"]

        # Check telemetry event count
        steps = [e["step"] for e in data["execution_events"]]
        assert "fact_finder_agent" in steps
        assert "data_analyst_agent" in steps
        assert "agent_reasoning" in steps
        assert "final_response" in steps

    app.dependency_overrides.clear()

