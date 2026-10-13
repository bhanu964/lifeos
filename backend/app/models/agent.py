from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.models.memory import MemoryItem


class AskRequest(BaseModel):
    """
    Request payload for POST /api/ask.
    """
    uid: str = Field(..., min_length=1, description="User identifier owning the memories")
    question: str = Field(..., min_length=1, description="User question to be answered by the Lyzr agent")
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session identifier for conversational continuity in Lyzr"
    )


class ExecutionEvent(BaseModel):
    """
    Trace event recording each phase of agent orchestration.
    """
    step: str = Field(description="Name of the orchestration step (e.g. 'retrieval', 'reasoning')")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 event timestamp"
    )
    status: str = Field(description="Step status: 'started', 'completed', 'skipped', 'failed'")
    details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Structured contextual metadata about the execution step"
    )


class AskResponse(BaseModel):
    """
    Response returned by POST /api/ask.
    """
    answer: str = Field(description="Synthesized answer produced by the Lyzr agent")
    supporting_memories: List[MemoryItem] = Field(
        default_factory=list,
        description="Retrieved memories that informed the agent reasoning"
    )
    execution_events: List[ExecutionEvent] = Field(
        default_factory=list,
        description="Audit trace of execution events"
    )
    agent_id: str = Field(description="Lyzr agent ID that handled the request")
    session_id: str = Field(description="Active session ID used for the inference call")
    specialist_outputs: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Outputs from participating specialist agents in collaborative workflow"
    )
