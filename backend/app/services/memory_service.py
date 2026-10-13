from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.models.memory import MemoryItem
from app.services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)


class MemoryService:
    """
    High-level memory orchestration service.
    Coordinates memory ingestion, indexing, retrieval, deduplication,
    and prompt contextualization for multi-agent reasoning.
    """

    def __init__(self, qdrant_service: Optional[QdrantService] = None):
        self.qdrant = qdrant_service or QdrantService()

    async def initialize(self) -> bool:
        """Ensure Qdrant collection is provisioned."""
        return await self.qdrant.init_collection()

    async def store_memory(
        self,
        uid: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
    ) -> MemoryItem:
        """Create and store a user memory."""
        cleaned_content = content.strip()
        if not cleaned_content:
            raise ValueError("Memory content cannot be empty.")

        item_id = memory_id or str(uuid.uuid4())
        item = MemoryItem(
            id=item_id,
            uid=uid,
            content=cleaned_content,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        await self.qdrant.store_memory(item)
        return item

    async def search_memories(
        self,
        uid: str,
        query: str,
        limit: int = 5,
        score_threshold: Optional[float] = 0.25,
    ) -> List[MemoryItem]:
        """Search relevant memories for a user."""
        return await self.qdrant.search_memories(
            uid=uid,
            query=query,
            limit=limit,
            score_threshold=score_threshold,
        )

    async def delete_memory(self, memory_id: str, uid: str) -> bool:
        """Delete a memory safely within the user's boundary."""
        return await self.qdrant.delete_memory(memory_id=memory_id, uid=uid)

    async def list_memories(self, uid: str, limit: int = 50) -> List[MemoryItem]:
        """List user memories."""
        return await self.qdrant.list_memories(uid=uid, limit=limit)

    def format_memories_for_prompt(self, memories: List[MemoryItem]) -> str:
        """
        Format retrieved memories into a structured, tamper-resistant context block.
        If no memories are available, clearly returns an explicit indicator.
        """
        if not memories:
            return "NO_RELEVANT_MEMORIES_AVAILABLE"

        formatted_lines = []
        for idx, mem in enumerate(memories, start=1):
            source = mem.metadata.get("source", "conversation")
            timestamp = mem.created_at or mem.metadata.get("timestamp", "unknown")
            speaker = mem.metadata.get("speaker", "user")
            score_info = f" | relevance: {mem.score:.2f}" if mem.score is not None else ""
            header = f"[Memory #{idx} | source: {source} | speaker: {speaker} | timestamp: {timestamp}{score_info}]"
            lines = [header, f"Original Spoken Transcript: {mem.content}"]
            if mem.display_text and mem.display_text != mem.content:
                lines.append(f"Normalized Product Reference: {mem.display_text}")
            formatted_lines.append("\n".join(lines))

        return "\n\n".join(formatted_lines)
