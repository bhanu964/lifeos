import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.routers.omi import get_omi_service
from app.services.omi_service import OmiService


@pytest.mark.asyncio
async def test_omi_conversation_webhook(mock_qdrant_service):
    omi_service = OmiService(qdrant_service=mock_qdrant_service)
    app.dependency_overrides[get_omi_service] = lambda: omi_service

    payload = {
        "id": "conv-1234",
        "created_at": "2026-10-13T10:00:00Z",
        "transcript_segments": [
            {
                "text": "We need to finish the AgentMemory presentation.",
                "speaker": "SPEAKER_00",
                "speaker_name": "Bhanu",
                "is_user": True,
                "start": 0.0,
                "end": 4.5,
            },
            {
                "text": "I will handle the slide deck design.",
                "speaker": "SPEAKER_01",
                "speaker_name": "Alex",
                "is_user": False,
                "start": 5.0,
                "end": 8.0,
            },
            # Duplicate segment to test deduplication
            {
                "text": "We need to finish the AgentMemory presentation.",
                "speaker": "SPEAKER_00",
                "speaker_name": "Bhanu",
                "is_user": True,
                "start": 0.0,
                "end": 4.5,
            },
        ],
        "structured": {
            "title": "Presentation Planning",
            "overview": "Discussed responsibilities for the presentation.",
            "category": "work",
            "action_items": [
                {"description": "Design slide deck", "completed": False}
            ],
        },
        "discarded": False,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/omi/conversation?uid=demo-user", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        # 1 structured summary + 2 unique segments = 3 memories (duplicate dropped)
        assert data["processed_count"] == 3
        assert data["memory_id"] == "conv-1234"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_omi_conversation_discarded():
    omi_service = OmiService(qdrant_service=AsyncMock())
    app.dependency_overrides[get_omi_service] = lambda: omi_service

    payload = {
        "id": "discarded-conv",
        "transcript_segments": [{"text": "Testing 123"}],
        "discarded": True,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/omi/conversation?uid=demo-user", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"
        assert data["processed_count"] == 0

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_omi_realtime_webhook_dict_format(mock_qdrant_service):
    omi_service = OmiService(qdrant_service=mock_qdrant_service)
    app.dependency_overrides[get_omi_service] = lambda: omi_service

    payload = {
        "session_id": "session-live-1",
        "segments": [
            {
                "text": "Remember to submit before the hackathon cutoff.",
                "speaker": "SPEAKER_00",
                "is_user": True,
                "start": 12.0,
                "end": 15.0,
            }
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/omi/realtime?uid=demo-user", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["processed_count"] == 1
        assert data["session_id"] == "session-live-1"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_omi_realtime_webhook_array_format(mock_qdrant_service):
    omi_service = OmiService(qdrant_service=mock_qdrant_service)
    app.dependency_overrides[get_omi_service] = lambda: omi_service

    payload = [
        {
            "text": "Deploying the backend to production.",
            "speaker": "SPEAKER_00",
            "is_user": True,
            "start": 1.0,
            "end": 3.0,
        }
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/omi/realtime?uid=demo-user&session_id=stream-99", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["processed_count"] == 1
        assert data["session_id"] == "stream-99"

    app.dependency_overrides.clear()
