from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """
    Representation of an individual memory item stored or retrieved from Qdrant.
    Preserves original verbatim transcript in 'content', and presents normalized
    product names in 'display_text'.
    """
    id: str = Field(description="Unique identifier of the memory item (UUID)")
    uid: str = Field(description="User ID owning this memory (user-scoped retrieval)")
    content: str = Field(description="Original, unmodified textual content of the memory as received from Omi")
    display_text: Optional[str] = Field(
        default=None,
        description="Normalized transcript text for presentation with recognized product names clarified"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata such as speaker, session_id, source, category, timestamps"
    )
    score: Optional[float] = Field(
        default=None,
        description="Similarity score (cosine) when returned from a semantic search"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp"
    )

    def model_post_init(self, __context: Any) -> None:
        """Ensure display_text is populated with normalized product names if not provided."""
        if self.display_text is None and self.content:
            from app.utils.text_normalizer import normalize_transcript_text
            self.display_text = normalize_transcript_text(self.content)


class MemoryCreateRequest(BaseModel):
    """Request payload to manually insert a memory."""
    uid: str = Field(..., description="Target user identifier")
    content: str = Field(..., min_length=1, description="Memory text to store")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata associated with the memory"
    )


class MemorySearchRequest(BaseModel):
    """Request payload to query memories semantically."""
    uid: str = Field(..., description="Target user identifier")
    query: str = Field(..., min_length=1, description="Query text to search")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of items to return")
    score_threshold: Optional[float] = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score threshold"
    )


class MemorySearchResponse(BaseModel):
    """Semantic search response."""
    memories: List[MemoryItem]
    total_found: int
    query: str
    uid: str


class MemoryDeleteResponse(BaseModel):
    """Response returned upon deleting a memory."""
    status: str
    memory_id: str
    uid: str
