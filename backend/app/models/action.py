from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.agent import ExecutionEvent


class ActionType(str, Enum):
    READ_CALENDAR = "read_calendar"
    CREATE_TASK = "create_task"
    CREATE_CALENDAR_EVENT = "create_calendar_event"
    CREATE_GMAIL_DRAFT = "create_gmail_draft"
    LIST_TASKS = "list_tasks"


class ActionStatus(str, Enum):
    STAGED = "staged"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class StagedAction(BaseModel):
    action_id: str = Field(description="Unique identifier for the staged action")
    uid: str = Field(description="User identifier owning the staged action")
    action_type: ActionType = Field(description="Type of action to execute")
    title: str = Field(description="Concise human-readable title of the proposed action")
    description: str = Field(description="Full explanation of proposed action details")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Validated parameters for integration execution")
    status: ActionStatus = Field(default=ActionStatus.STAGED, description="Current lifecycle state")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = Field(description="Expiration timestamp after which approval is rejected")
    idempotency_key: str = Field(description="Deterministic key preventing duplicate writes")
    execution_result: Optional[Dict[str, Any]] = Field(default=None, description="Raw outcome returned by integration")
    verification_status: Optional[str] = Field(default=None, description="Result of verification read-back")
    error_message: Optional[str] = Field(default=None, description="Detailed failure message if operation failed")


class CalendarEventItem(BaseModel):
    id: Optional[str] = None
    summary: str
    start_time: str
    end_time: str
    description: Optional[str] = None


class TaskItem(BaseModel):
    id: Optional[str] = None
    title: str
    status: Optional[str] = None
    due: Optional[str] = None
    notes: Optional[str] = None


class TimeSlot(BaseModel):
    start_time: str
    end_time: str
    duration_minutes: int
    label: Optional[str] = "Available Focus Slot"


class PlanRequest(BaseModel):
    uid: str = Field(..., min_length=1, description="Target user identifier")
    prompt: str = Field(..., min_length=1, description="Voice transcript or text instruction for planning")
    target_date: Optional[str] = Field(default=None, description="Target date in YYYY-MM-DD format (defaults to tomorrow)")
    timezone: Optional[str] = Field(default="UTC", description="Target timezone name or offset")


class PlanResponse(BaseModel):
    uid: str
    plan_summary: str
    target_date: str
    existing_events: List[CalendarEventItem] = Field(default_factory=list)
    pending_tasks: List[TaskItem] = Field(default_factory=list)
    suggested_slots: List[TimeSlot] = Field(default_factory=list)
    staged_actions: List[StagedAction] = Field(default_factory=list)
    execution_events: List[ExecutionEvent] = Field(default_factory=list)


class ActionExecutionResponse(BaseModel):
    action_id: str
    status: ActionStatus
    message: str
    execution_result: Optional[Dict[str, Any]] = None
    verified: bool = False
    memory_id: Optional[str] = None
    notification: Optional[Dict[str, Any]] = None


class GmailDraftItem(BaseModel):
    id: Optional[str] = None
    recipient_email: str
    subject: str
    body: str
    display_url: Optional[str] = None
    created_at: Optional[str] = None


class TelegramNotificationRecord(BaseModel):
    notification_id: str
    event_type: str
    action_id: Optional[str] = None
    chat_id: Optional[str] = None
    text: str
    status: str = Field(description="'delivered', 'failed', 'NEEDS_CONFIGURATION', or 'skipped_no_chat_id'")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_id: Optional[int] = None
    error_message: Optional[str] = None


class DraftRequest(BaseModel):
    uid: str = Field(..., min_length=1, description="Target user identifier")
    prompt: str = Field(..., min_length=1, description="Instruction for preparing the email draft")
    recipient_email: Optional[str] = Field(default=None, description="Explicit recipient email if known")
    subject: Optional[str] = Field(default=None, description="Explicit subject if known")


class DraftResponse(BaseModel):
    uid: str
    staged_action: StagedAction
    context_used: List[str] = Field(default_factory=list)
    execution_events: List[ExecutionEvent] = Field(default_factory=list)


class NotificationTestRequest(BaseModel):
    uid: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    chat_id: Optional[str] = None

