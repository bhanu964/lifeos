import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.memory import (
    MemoryCreateRequest,
    MemoryDeleteResponse,
    MemoryItem,
    MemorySearchRequest,
    MemorySearchResponse,
)
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/memories", tags=["Memories"])


def get_memory_service() -> MemoryService:
    return MemoryService()


@router.get("", response_model=List[MemoryItem], summary="List user memories")
async def list_memories(
    uid: str = Query(..., description="Target user identifier"),
    limit: int = Query(default=50, ge=1, le=100, description="Max memories to return"),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """List stored memories scoped to the specified user."""
    try:
        return await memory_service.list_memories(uid=uid, limit=limit)
    except Exception as exc:
        logger.error("Error listing memories: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to list memories: {str(exc)}")


@router.post("", response_model=MemoryItem, status_code=201, summary="Store a memory manually")
async def create_memory(
    request: MemoryCreateRequest,
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Store an individual memory in Qdrant with user scoping and FastEmbed vectorization."""
    try:
        return await memory_service.store_memory(
            uid=request.uid,
            content=request.content,
            metadata=request.metadata,
        )
    except Exception as exc:
        logger.error("Error creating memory: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to create memory: {str(exc)}")


@router.post("/search", response_model=MemorySearchResponse, summary="Semantic memory search")
async def search_memories(
    request: MemorySearchRequest,
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Search for relevant memories semantically using FastEmbed 384-dimensional cosine matching."""
    try:
        results = await memory_service.search_memories(
            uid=request.uid,
            query=request.query,
            limit=request.limit,
            score_threshold=request.score_threshold,
        )
        return MemorySearchResponse(
            memories=results,
            total_found=len(results),
            query=request.query,
            uid=request.uid,
        )
    except Exception as exc:
        logger.error("Error searching memories: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(exc)}")


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse, summary="Delete a memory")
async def delete_memory(
    memory_id: str,
    uid: str = Query(..., description="Target user identifier"),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Delete a memory item from Qdrant, guaranteeing user boundary protection."""
    try:
        await memory_service.delete_memory(memory_id=memory_id, uid=uid)
        return MemoryDeleteResponse(
            status="deleted",
            memory_id=memory_id,
            uid=uid,
        )
    except Exception as exc:
        logger.error("Error deleting memory %s: %s", memory_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(exc)}")
