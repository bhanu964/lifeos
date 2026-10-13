import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from qdrant_client import models
from app.models.memory import MemoryItem
from app.services.qdrant_service import QdrantService


@pytest.mark.asyncio
async def test_qdrant_verify_connection_success():
    service = QdrantService(url="https://fake-qdrant.io", api_key="fake-key")
    service._client = AsyncMock()
    service._client.get_collections = AsyncMock(return_value=MagicMock())

    is_connected = await service.verify_connection()
    assert is_connected is True


@pytest.mark.asyncio
async def test_qdrant_verify_connection_failure():
    service = QdrantService(url="https://fake-qdrant.io", api_key="fake-key")
    service._client = AsyncMock()
    service._client.get_collections = AsyncMock(side_effect=Exception("Connection refused"))

    is_connected = await service.verify_connection()
    assert is_connected is False


@pytest.mark.asyncio
async def test_qdrant_init_collection_creates_when_missing():
    service = QdrantService(url="https://fake-qdrant.io", api_key="fake-key")
    service._client = AsyncMock()
    collections_res = MagicMock()
    collections_res.collections = []  # No collections yet
    service._client.get_collections = AsyncMock(return_value=collections_res)
    service._client.create_collection = AsyncMock()
    service._client.create_payload_index = AsyncMock()

    res = await service.init_collection()
    assert res is True
    service._client.create_collection.assert_awaited_once()
    # Verify vector dimension is 384
    call_kwargs = service._client.create_collection.call_args.kwargs
    vector_params = call_kwargs["vectors_config"]
    assert vector_params.size == 384
    assert vector_params.distance == models.Distance.COSINE


@pytest.mark.asyncio
async def test_qdrant_search_memories_scoped_by_uid():
    service = QdrantService(url="https://fake-qdrant.io", api_key="fake-key")
    service._client = AsyncMock()
    service.generate_embedding = AsyncMock(return_value=[0.1] * 384)

    mock_point = MagicMock()
    mock_point.id = "point-1"
    mock_point.score = 0.88
    mock_point.payload = {
        "id": "point-1",
        "uid": "user-abc",
        "content": "Discussed Lyzr agent integration",
        "metadata": {"speaker": "User"},
        "created_at": "2026-10-13T10:00:00Z",
    }
    service._client.search = AsyncMock(return_value=[mock_point])

    results = await service.search_memories(uid="user-abc", query="Lyzr agent", limit=5)
    assert len(results) == 1
    assert results[0].uid == "user-abc"
    assert results[0].score == 0.88
    assert results[0].content == "Discussed Lyzr agent integration"

    # Verify query filter strictly enforced uid match
    call_args = service._client.search.call_args.kwargs
    query_filter = call_args["query_filter"]
    assert query_filter is not None
    assert query_filter.must[0].key == "uid"
    assert query_filter.must[0].match.value == "user-abc"
