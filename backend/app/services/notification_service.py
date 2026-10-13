from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.config import settings
from app.models.action import ActionStatus, ActionType, StagedAction, TelegramNotificationRecord
from app.services.lyzr_service import LyzrService
from app.services.memory_service import MemoryService
from app.utils.calendar_utils import format_telegram_calendar_report

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Notification service for LifeOS events.
    Delivers concise, verified updates to Telegram via Composio.
    Enforces idempotency, non-recursive delivery, and human auditability.
    """

    _notifications: List[TelegramNotificationRecord] = []
    _notified_event_keys: set[str] = set()

    def __init__(
        self,
        lyzr_service: Optional[LyzrService] = None,
        memory_service: Optional[MemoryService] = None,
    ):
        self.lyzr = lyzr_service or LyzrService()
        self.memory = memory_service or MemoryService()

    def list_notifications(self, limit: int = 50) -> List[TelegramNotificationRecord]:
        """Returns the most recent notifications."""
        return list(reversed(self._notifications[-limit:]))

    async def notify_action_success(
        self,
        action: StagedAction,
        chat_id: Optional[str] = None,
    ) -> TelegramNotificationRecord:
        """
        Sends a Telegram notification after a staged action has succeeded and verified.
        Guarantees idempotency using action_id to avoid duplicate sends.
        """
        event_key = f"action_success:{action.action_id}"
        if event_key in self._notified_event_keys:
            logger.info("Notification for %s already sent. Skipping duplicate.", event_key)
            for existing in reversed(self._notifications):
                if existing.action_id == action.action_id:
                    return existing

        target_chat_id = (
            chat_id
            or action.parameters.get("telegram_chat_id")
            or settings.telegram_chat_id
        )

        # Message formatting based on action type
        if action.action_type == ActionType.READ_CALENDAR:
            text = format_telegram_calendar_report(action.execution_result or {})
        else:
            type_label = {
                ActionType.CREATE_TASK: "Google Task",
                ActionType.CREATE_CALENDAR_EVENT: "Google Calendar Event",
                ActionType.CREATE_GMAIL_DRAFT: "Gmail Draft",
            }.get(action.action_type, "Action")

            text = (
                f"🚀 LifeOS: Your {type_label} was created and verified.\n\n"
                f"Title: {action.title}\n"
                f"Status: Completed & Verified\n"
                f"Action ID: {action.action_id}"
            )

        notification_id = f"notif-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # If no chat ID is available, record clean status
        if not target_chat_id:
            status_val = "NEEDS_CONFIGURATION" if action.action_type == ActionType.READ_CALENDAR else "skipped_no_chat_id"
            logger.info(
                "No Telegram chat_id configured. Notification %s marked as '%s'.",
                notification_id,
                status_val,
            )
            record = TelegramNotificationRecord(
                notification_id=notification_id,
                event_type="action_completed",
                action_id=action.action_id,
                chat_id=None,
                text=text,
                status=status_val,
                timestamp=now_iso,
                error_message="Telegram chat_id is not registered. Send /start to @Ididhswkje_bot on Telegram to connect your chat.",
            )
            self._notifications.append(record)
            self._notified_event_keys.add(event_key)
            return record

        try:
            logger.info("Sending Telegram notification for action %s to chat %s", action.action_id, target_chat_id)
            res = await self.lyzr.send_telegram_message(text=text, chat_id=target_chat_id)

            is_successful = bool(
                isinstance(res, dict)
                and (
                    res.get("successful") is True
                    or (isinstance(res.get("data"), dict) and res.get("data", {}).get("ok") is True)
                )
            )

            status = "delivered" if is_successful else "failed"
            error_msg = None
            if not is_successful:
                error_msg = str(res.get("error") or res.get("data", {}).get("message") or "Delivery rejected")

            msg_id = None
            if isinstance(res, dict):
                data_field = res.get("data", {})
                if isinstance(data_field, dict):
                    msg_id = data_field.get("result", {}).get("message_id") or data_field.get("message_id")

            record = TelegramNotificationRecord(
                notification_id=notification_id,
                event_type="action_completed",
                action_id=action.action_id,
                chat_id=str(target_chat_id),
                text=text,
                status=status,
                timestamp=now_iso,
                message_id=msg_id,
                error_message=error_msg,
            )
            self._notifications.append(record)
            self._notified_event_keys.add(event_key)

            # Record concise memory in Qdrant if delivered
            if is_successful:
                try:
                    await self.memory.store_memory(
                        uid=action.uid,
                        content=f"Telegram notification for action {action.action_id} was delivered. Content: {action.title}",
                        metadata={
                            "source": "telegram_notification",
                            "action_id": action.action_id,
                            "notification_id": notification_id,
                            "status": "delivered",
                            "timestamp": now_iso,
                        },
                    )
                except Exception as mem_err:
                    logger.warning("Failed to store notification memory in Qdrant: %s", mem_err)

            return record

        except Exception as exc:
            logger.error("Failed to deliver Telegram notification: %s", exc)
            record = TelegramNotificationRecord(
                notification_id=notification_id,
                event_type="action_completed",
                action_id=action.action_id,
                chat_id=str(target_chat_id),
                text=text,
                status="failed",
                timestamp=now_iso,
                error_message=str(exc),
            )
            self._notifications.append(record)
            self._notified_event_keys.add(event_key)
            return record

    async def notify_action_failure(
        self,
        action: StagedAction,
        error_message: str,
        chat_id: Optional[str] = None,
    ) -> TelegramNotificationRecord:
        """
        Sends a failure notification when an authorized action encounters an unrecoverable failure.
        """
        event_key = f"action_failure:{action.action_id}"
        if event_key in self._notified_event_keys:
            for existing in reversed(self._notifications):
                if existing.action_id == action.action_id:
                    return existing

        target_chat_id = (
            chat_id
            or action.parameters.get("telegram_chat_id")
            or settings.telegram_chat_id
        )

        text = (
            f"⚠️ LifeOS: Action execution failed.\n\n"
            f"Title: {action.title}\n"
            f"Status: Failed\n"
            f"Reason: {error_message[:200]}"
        )

        notification_id = f"notif-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        if not target_chat_id:
            record = TelegramNotificationRecord(
                notification_id=notification_id,
                event_type="action_failed",
                action_id=action.action_id,
                chat_id=None,
                text=text,
                status="skipped_no_chat_id",
                timestamp=now_iso,
                error_message="Telegram chat_id is not configured.",
            )
            self._notifications.append(record)
            self._notified_event_keys.add(event_key)
            return record

        try:
            res = await self.lyzr.send_telegram_message(text=text, chat_id=target_chat_id)
            is_successful = bool(
                isinstance(res, dict) and res.get("successful") is True
            )
            record = TelegramNotificationRecord(
                notification_id=notification_id,
                event_type="action_failed",
                action_id=action.action_id,
                chat_id=str(target_chat_id),
                text=text,
                status="delivered" if is_successful else "failed",
                timestamp=now_iso,
                error_message=None if is_successful else str(res.get("error")),
            )
            self._notifications.append(record)
            self._notified_event_keys.add(event_key)
            return record
        except Exception as exc:
            record = TelegramNotificationRecord(
                notification_id=notification_id,
                event_type="action_failed",
                action_id=action.action_id,
                chat_id=str(target_chat_id),
                text=text,
                status="failed",
                timestamp=now_iso,
                error_message=str(exc),
            )
            self._notifications.append(record)
            self._notified_event_keys.add(event_key)
            return record
