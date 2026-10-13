from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.action import ActionExecutionResponse, ActionStatus, ActionType, StagedAction
from app.models.agent import ExecutionEvent


class WorkflowStage(str, Enum):
    VOICE_RECEIVED = "VOICE_RECEIVED"
    TRANSCRIPT_STORED = "TRANSCRIPT_STORED"
    MEMORY_RETRIEVAL = "MEMORY_RETRIEVAL"
    LYZR_MANAGER_PLANNING = "LYZR_MANAGER_PLANNING"
    SPECIALIST_AGENTS_WORKING = "SPECIALIST_AGENTS_WORKING"
    INTEGRATIONS_EXECUTING = "INTEGRATIONS_EXECUTING"
    AWAITING_TELEGRAM_APPROVAL = "AWAITING_TELEGRAM_APPROVAL"
    VERIFICATION = "VERIFICATION"
    QDRANT_MEMORY_UPDATED = "QDRANT_MEMORY_UPDATED"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    NEEDS_CONFIGURATION = "NEEDS_CONFIGURATION"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class WorkflowStatus(str, Enum):
    RECEIVED = "RECEIVED"
    RUNNING = "RUNNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    NEEDS_CONFIGURATION = "NEEDS_CONFIGURATION"
    REJECTED = "REJECTED"


class NodeState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    AWAITING_TELEGRAM_APPROVAL = "awaiting_telegram_approval"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineNode(BaseModel):
    id: str
    label: str
    state: NodeState = NodeState.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: Optional[int] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class SpecialistOutput(BaseModel):
    agent_id: str
    agent_name: str
    role: str
    output: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkflowRecord(BaseModel):
    workflow_id: str
    user_id: str
    conversation_id: str
    transcript: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: WorkflowStatus = WorkflowStatus.RECEIVED
    current_stage: WorkflowStage = WorkflowStage.VOICE_RECEIVED
    nodes: Dict[str, PipelineNode] = Field(default_factory=dict)
    plan_summary: Optional[str] = None
    specialist_outputs: List[SpecialistOutput] = Field(default_factory=list)
    action_ids: List[str] = Field(default_factory=list)
    actions: List[StagedAction] = Field(default_factory=list)
    action_results: List[ActionExecutionResponse] = Field(default_factory=list)
    calendar_result: Optional[Dict[str, Any]] = None
    telegram_delivery: Optional[Dict[str, Any]] = None
    retrieved_memories: List[Dict[str, Any]] = Field(default_factory=list)
    saved_memories: List[Dict[str, Any]] = Field(default_factory=list)
    execution_events: List[ExecutionEvent] = Field(default_factory=list)
    error_details: Optional[str] = None
    idempotency_hash: str


class WorkflowEventPayload(BaseModel):
    event_type: str  # workflow_created, stage_changed, node_updated, action_staged, etc.
    workflow_id: str
    user_id: str
    stage: WorkflowStage
    status: WorkflowStatus
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: Dict[str, Any] = Field(default_factory=dict)
