import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from pathlib import Path
import sys

# Ensure backend root is on sys.path for direct pytest invocation
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.models.memory import MemoryItem
from app.services.lyzr_service import LyzrService
from app.services.memory_service import MemoryService
from app.services.omi_service import OmiService
from app.services.qdrant_service import QdrantService


@pytest.fixture
def sync_client():
    """Synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Asynchronous test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def mock_qdrant_service():
    """Mocked QdrantService fixture for isolated unit tests."""
    mock = MagicMock(spec=QdrantService)
    mock.verify_connection = AsyncMock(return_value=True)
    mock.init_collection = AsyncMock(return_value=True)
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    mock.generate_embeddings = AsyncMock(side_effect=lambda texts: [[0.1] * 384 for _ in texts])
    mock.store_memory = AsyncMock(side_effect=lambda m: m.id)
    mock.store_memories = AsyncMock(side_effect=lambda ms: [m.id for m in ms])
    mock.search_memories = AsyncMock(return_value=[])
    mock.delete_memory = AsyncMock(return_value=True)
    mock.list_memories = AsyncMock(return_value=[])
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_lyzr_service():
    """Mocked LyzrService fixture."""
    mock = MagicMock(spec=LyzrService)
    mock.chat = AsyncMock(
        return_value={
            "response": "Based on your discussion, the target release date is Friday.",
            "module_outputs": {},
            "agent_id": "6acd9f07cb0aafc9293bd126",
            "session_id": "test-session",
        }
    )
    return mock
