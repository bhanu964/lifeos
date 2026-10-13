import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.memory import MemoryItem
from app.services.memory_service import MemoryService
from app.services.qdrant_service import QdrantService


@pytest.mark.asyncio
async def test_memory_service_store(mock_qdrant_service):
    service = MemoryService(qdrant_service=mock_qdrant_service)
    item = await service.store_memory(
        uid="user-123",
        content="Meeting with John about hackathon deliverables",
        metadata={"category": "work"},
    )
    assert item.uid == "user-123"
    assert item.content == "Meeting with John about hackathon deliverables"
    assert item.id is not None
    mock_qdrant_service.store_memory.assert_awaited_once()


@pytest.mark.asyncio
async def test_memory_service_store_empty_raises(mock_qdrant_service):
    service = MemoryService(qdrant_service=mock_qdrant_service)
    with pytest.raises(ValueError, match="cannot be empty"):
        await service.store_memory(uid="user-123", content="   ")


@pytest.mark.asyncio
async def test_format_memories_for_prompt_empty():
    service = MemoryService()
    formatted = service.format_memories_for_prompt([])
    assert formatted == "NO_RELEVANT_MEMORIES_AVAILABLE"


@pytest.mark.asyncio
async def test_format_memories_for_prompt_populated():
    service = MemoryService()
    memories = [
        MemoryItem(
            id="mem-1",
            uid="user-1",
            content="Project deadline is this Friday",
            score=0.89,
            metadata={"source": "omi_voice", "speaker": "Alice"},
            created_at="2026-10-13T10:00:00Z",
        )
    ]
    formatted = service.format_memories_for_prompt(memories)
    assert "Alice" in formatted
    assert "Project deadline is this Friday" in formatted
    assert "0.89" in formatted


@pytest.mark.asyncio
async def test_memory_service_delete(mock_qdrant_service):
    service = MemoryService(qdrant_service=mock_qdrant_service)
    result = await service.delete_memory(memory_id="mem-1", uid="user-1")
    assert result is True
    mock_qdrant_service.delete_memory.assert_awaited_once_with(memory_id="mem-1", uid="user-1")
