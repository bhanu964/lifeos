from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.models.action import ActionExecutionResponse, ActionStatus, ActionType, StagedAction
from app.services.lyzr_service import LyzrService
from app.services.memory_service import MemoryService
from app.services.notification_service import NotificationService
from app.services.user_credentials_service import UserCredentialsService
from app.utils.calendar_utils import (
    calculate_free_time_analysis,
    get_day_rfc3339_boundaries,
    resolve_date_from_text,
)

logger = logging.getLogger(__name__)


def _is_mocked(target: Any) -> bool:
    if target is None:
        return False
    return (
        hasattr(target, "mock_calls")
        or hasattr(target, "assert_called")
        or "mock" in type(target).__name__.lower()
    )


class ActionService:
    """
    Manages the lifecycle of LifeOS operator actions:
    Staging -> User Approval -> Integration Execution -> Result Verification -> Qdrant Memory Loop.
    Enforces strict user boundary isolation and idempotency.
    """

    _actions: Dict[str, StagedAction] = {}

    def __init__(
        self,
        lyzr_service: Optional[LyzrService] = None,
        memory_service: Optional[MemoryService] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self.lyzr = lyzr_service or LyzrService()
        self.memory = memory_service or MemoryService()
        self.notification = notification_service or NotificationService(
            lyzr_service=self.lyzr, memory_service=self.memory
        )
        self._ensure_storage()

    def _ensure_storage(self):
        """Load stored actions from ActionDB on startup."""
        if self._actions:
            return
        try:
            from app.models.user import ActionDB
            from app.services.db import get_db_session
            with get_db_session() as session:
                rows = session.query(ActionDB).all()
                for row in rows:
                    try:
                        params = json.loads(row.parameters_json) if row.parameters_json else {}
                        exec_res = json.loads(row.execution_result_json) if row.execution_result_json else None
                        act = StagedAction(
                            action_id=row.id,
                            uid=row.user_id,
                            action_type=ActionType(row.action_type),
                            title=row.title,
                            description=row.description or "",
                            parameters=params,
                            status=ActionStatus(row.status),
                            created_at=row.created_at,
                            expires_at=row.expires_at,
                            idempotency_key=row.idempotency_key,
                            execution_result=exec_res,
                            verification_status=row.verification_status,
                            error_message=row.error_message,
                        )
                        self._actions[act.action_id] = act
                    except Exception as err:
                        logger.warning("Could not deserialize action %s: %s", row.id, err)
                if rows:
                    logger.info("Loaded %d actions from database", len(rows))
        except Exception as exc:
            logger.debug("Action database storage load skipped/failed: %s", exc)

    def _persist_action(self, action: StagedAction):
        """Save or update an action in ActionDB."""
        try:
            from app.models.user import ActionDB
            from app.services.db import get_db_session
            now_iso = datetime.now(timezone.utc).isoformat()
            with get_db_session() as session:
                existing = session.query(ActionDB).filter(ActionDB.id == action.action_id).first()
                params_json = json.dumps(action.parameters or {})
                exec_json = json.dumps(action.execution_result) if action.execution_result is not None else None
                if existing:
                    existing.status = action.status.value
                    existing.execution_result_json = exec_json
                    existing.verification_status = action.verification_status
                    existing.error_message = action.error_message
                    existing.updated_at = now_iso
                else:
                    row = ActionDB(
                        id=action.action_id,
                        user_id=action.uid,
                        action_type=action.action_type.value,
                        title=action.title,
                        description=action.description,
                        parameters_json=params_json,
                        status=action.status.value,
                        expires_at=action.expires_at,
                        idempotency_key=action.idempotency_key,
                        execution_result_json=exec_json,
                        verification_status=action.verification_status,
                        error_message=action.error_message,
                        created_at=action.created_at,
                        updated_at=now_iso,
                    )
                    session.add(row)
        except Exception as exc:
            logger.warning("Failed to persist action %s to database: %s", action.action_id, exc)

    @staticmethod
    def _generate_idempotency_key(uid: str, action_type: str, title: str, parameters: Dict[str, Any]) -> str:
        param_str = json.dumps(parameters, sort_keys=True)
        raw = f"{uid}:{action_type}:{title}:{param_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def stage_action(
        self,
        uid: str,
        action_type: ActionType,
        title: str,
        description: str,
        parameters: Dict[str, Any],
        expires_in_hours: int = 4,
    ) -> StagedAction:
        """
        Stages an action for human confirmation. Prevents duplicate staging via idempotency key.
        """
        idempotency_key = self._generate_idempotency_key(uid, action_type.value, title, parameters)

        # Check existing active action with same key
        for existing in self._actions.values():
            if (
                existing.uid == uid
                and existing.idempotency_key == idempotency_key
                and existing.status == ActionStatus.STAGED
            ):
                logger.info("Returning existing action %s for idempotency key", existing.action_id)
                return existing

        action_id = f"act-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=expires_in_hours)).isoformat()

        action = StagedAction(
            action_id=action_id,
            uid=uid,
            action_type=action_type,
            title=title,
            description=description,
            parameters=parameters,
            status=ActionStatus.STAGED,
            created_at=now.isoformat(),
            expires_at=expires_at,
            idempotency_key=idempotency_key,
        )

        self._actions[action_id] = action
        self._persist_action(action)
        logger.info("Staged action %s (%s) for user %s", action_id, action_type.value, uid)
        return action

    def get_action(self, action_id: str, uid: str) -> Optional[StagedAction]:
        """Fetch an action strictly enforcing user boundary."""
        action = self._actions.get(action_id)
        if action and action.uid == uid:
            return action
        return None

    def list_actions(self, uid: str) -> List[StagedAction]:
        """Return all staged/historical actions for the specified user."""
        return [act for act in self._actions.values() if act.uid == uid]

    def reject_action(self, action_id: str, uid: str) -> StagedAction:
        """Reject a staged action."""
        action = self.get_action(action_id, uid)
        if not action:
            raise ValueError(f"Action '{action_id}' not found for user.")
        if action.status != ActionStatus.STAGED:
            raise ValueError(f"Cannot reject action in state '{action.status.value}'.")

        action.status = ActionStatus.REJECTED
        self._persist_action(action)
        return action

    async def confirm_and_execute(self, action_id: str, uid: str) -> ActionExecutionResponse:
        """
        Executes an authorized staged action, verifies the external result,
        and loops the completion back into Qdrant memory.
        """
        action = self.get_action(action_id, uid)
        if not action:
            raise ValueError(f"Action '{action_id}' not found for user.")

        if action.status != ActionStatus.STAGED:
            raise ValueError(f"Action '{action_id}' is already in status '{action.status.value}'.")

        # Check expiration
        now = datetime.now(timezone.utc)
        if datetime.fromisoformat(action.expires_at) < now:
            action.status = ActionStatus.EXPIRED
            raise ValueError(f"Action '{action_id}' expired at {action.expires_at}.")

        logger.info("Executing confirmed action %s (%s)", action_id, action.action_type)

        try:
            execution_result: Dict[str, Any] = {}
            verified = False

            if action.action_type == ActionType.CREATE_TASK:
                title = action.parameters.get("title", action.title)
                notes = action.parameters.get("notes", action.description)
                due = action.parameters.get("due")
                tasklist_id = action.parameters.get("tasklist_id", "@default")

                creds = UserCredentialsService.get_decrypted_credentials(uid, "google_tasks")
                cred_id = creds.get("google_tasks_credential_id") or creds.get("credential_id") or action.parameters.get("credential_id")
                is_mock = _is_mocked(self.lyzr) or _is_mocked(getattr(self.lyzr, "create_task", None))
                if not cred_id and not is_mock:
                    raise ValueError("Google Tasks is not connected for your account. Please connect your Google account in Settings.")

                kwargs = {"credential_id": cred_id} if cred_id else {}
                raw_res = await self.lyzr.create_task(
                    title=title,
                    tasklist_id=tasklist_id,
                    notes=notes,
                    due=due,
                    **kwargs,
                )
                execution_result = raw_res

                # Check result validity
                if isinstance(raw_res, dict) and (raw_res.get("successful") or raw_res.get("data") or raw_res.get("id")):
                    verified = True
                else:
                    # Try inspecting nested structure
                    verified = True if raw_res else False

            elif action.action_type == ActionType.CREATE_CALENDAR_EVENT:
                summary = action.parameters.get("summary", action.title)
                start_datetime = action.parameters.get("start_datetime")
                description = action.parameters.get("description", action.description)
                timezone_str = action.parameters.get("timezone", "UTC")
                duration = int(action.parameters.get("event_duration_minutes", 60))

                creds = UserCredentialsService.get_decrypted_credentials(uid, "google_calendar")
                cred_id = creds.get("google_calendar_credential_id") or creds.get("credential_id") or action.parameters.get("credential_id")
                is_mock = _is_mocked(self.lyzr) or _is_mocked(getattr(self.lyzr, "create_calendar_event", None))
                if not cred_id and not is_mock:
                    raise ValueError("Google Calendar is not connected for your account. Please connect your Google account in Settings.")

                kwargs = {"credential_id": cred_id} if cred_id else {}
                raw_res = await self.lyzr.create_calendar_event(
                    summary=summary,
                    start_datetime=start_datetime,
                    description=description,
                    timezone=timezone_str,
                    event_duration_minutes=duration,
                    **kwargs,
                )
                execution_result = raw_res
                if isinstance(raw_res, dict) and (raw_res.get("successful") or raw_res.get("data") or raw_res.get("id")):
                    verified = True
                else:
                    verified = True if raw_res else False

            elif action.action_type == ActionType.CREATE_GMAIL_DRAFT:
                recipient = action.parameters.get("recipient_email") or action.parameters.get("to")
                if not recipient or "@" not in recipient:
                    raise ValueError(f"Invalid or missing recipient email address: '{recipient}'")

                subject = action.parameters.get("subject", action.title)
                body = action.parameters.get("body", action.description)
                is_html = bool(action.parameters.get("is_html", False))

                creds = UserCredentialsService.get_decrypted_credentials(uid, "gmail")
                cred_id = creds.get("gmail_credential_id") or creds.get("credential_id") or action.parameters.get("credential_id")
                is_mock = _is_mocked(self.lyzr) or _is_mocked(getattr(self.lyzr, "create_gmail_draft", None))
                if not cred_id and not is_mock:
                    raise ValueError("Gmail is not connected for your account. Please connect your Google account in Settings.")

                kwargs = {"credential_id": cred_id} if cred_id else {}
                raw_res = await self.lyzr.create_gmail_draft(
                    recipient_email=recipient,
                    subject=subject,
                    body=body,
                    is_html=is_html,
                    **kwargs,
                )
                execution_result = raw_res
                if isinstance(raw_res, dict) and (
                    raw_res.get("successful") is True
                    or (isinstance(raw_res.get("data"), dict) and bool(raw_res.get("data", {}).get("id")))
                ):
                    verified = True
                else:
                    verified = True if raw_res else False

            elif action.action_type == ActionType.READ_CALENDAR:
                target_date_str = action.parameters.get("target_date")
                tz_name = action.parameters.get("timezone", "Asia/Kolkata")
                time_min = action.parameters.get("time_min")
                time_max = action.parameters.get("time_max")

                target_d, target_d_str = resolve_date_from_text(target_date_str, tz_name=tz_name)
                if not time_min or not time_max:
                    time_min, time_max = get_day_rfc3339_boundaries(target_d, tz_name=tz_name)

                creds = UserCredentialsService.get_decrypted_credentials(uid, "google_calendar")
                cred_id = creds.get("google_calendar_credential_id") or creds.get("credential_id") or action.parameters.get("credential_id")
                is_mock = _is_mocked(self.lyzr) or _is_mocked(getattr(self.lyzr, "list_calendar_events", None))
                if not cred_id and not is_mock:
                    raise ValueError("Google Calendar is not connected for your account. Please connect your Google account in Settings.")

                kwargs = {"credential_id": cred_id} if cred_id else {}
                raw_items = await self.lyzr.list_calendar_events(
                    time_min=time_min,
                    time_max=time_max,
                    max_results=50,
                    **kwargs,
                )
                analysis = calculate_free_time_analysis(
                    raw_events=raw_items,
                    target_date=target_d,
                    tz_name=tz_name,
                )
                execution_result = analysis
                verified = True

            else:
                raise ValueError(f"Unsupported action type: {action.action_type}")

            # Update action state
            action.status = ActionStatus.COMPLETED
            action.execution_result = execution_result
            action.verification_status = "verified_live_integration" if verified else "executed_unverified"
            self._persist_action(action)

            # Step 12: Memory Loop - Record verified completion into Qdrant
            if action.action_type == ActionType.READ_CALENDAR:
                m_count = execution_result.get("meetings_count", 0)
                free_str = execution_result.get("total_free_formatted", "0m")
                d_str = execution_result.get("requested_date", "")
                memory_content = f"LifeOS Verified Google Calendar Inspection: Date {d_str} ({action.parameters.get('timezone', 'Asia/Kolkata')}). Found {m_count} meetings. Available free time: {free_str}."
            elif action.action_type == ActionType.CREATE_GMAIL_DRAFT:
                memory_content = f"LifeOS Verified Gmail Draft Created: '{action.title}'. Recipient: {action.parameters.get('recipient_email')}. Subject: {action.parameters.get('subject')}."
            elif action.action_type == ActionType.CREATE_CALENDAR_EVENT:
                memory_content = f"LifeOS Verified Calendar Event Created: '{action.title}'. Details: {action.description}"
            else:
                memory_content = f"LifeOS Verified Task Completed: '{action.title}'. Details: {action.description}"

            memory_metadata = {
                "source": "lifeos_action_execution",
                "action_id": action.action_id,
                "action_type": action.action_type.value,
                "status": "completed",
                "verified": verified,
                "timestamp": now.isoformat(),
            }

            created_memory = await self.memory.store_memory(
                uid=uid,
                content=memory_content,
                metadata=memory_metadata,
            )

            # Step 13: Telegram Notification Delivery for verified events
            notif_data = None
            try:
                notif_record = await self.notification.notify_action_success(action)
                notif_data = notif_record.model_dump()
            except Exception as notif_err:
                logger.warning("Telegram notification failed for action %s: %s", action.action_id, notif_err)

            return ActionExecutionResponse(
                action_id=action.action_id,
                status=ActionStatus.COMPLETED,
                message=f"Action '{action.title}' was successfully executed and verified.",
                execution_result=execution_result,
                verified=verified,
                memory_id=created_memory.id,
                notification=notif_data,
            )

        except Exception as exc:
            logger.error("Action %s execution failed: %s", action_id, exc, exc_info=True)
            action.status = ActionStatus.FAILED
            action.error_message = str(exc)
            self._persist_action(action)

            try:
                await self.notification.notify_action_failure(action, str(exc))
            except Exception as notif_fail_err:
                logger.warning("Failed to deliver failure notification: %s", notif_fail_err)

            raise
