import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional
import uuid

import httpx

from app.config import settings
from app.models.action import ActionStatus, ActionType, StagedAction, TelegramNotificationRecord

from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TELEGRAM_STATE_FILE = DATA_DIR / "telegram_state.json"


class TelegramService:
    """
    Manages Telegram Bot communication for LifeOS:
    - Real-time interactive approval requests with inline keyboard buttons.
    - Clarification questions for missing parameters.
    - Verified success/failure notification delivery.
    - Chat ID auto-discovery from /start or incoming user messages.
    - Callback query processing and webhook/polling handling.
    """

    _discovered_chat_ids: List[str] = []
    _user_chat_map: Dict[str, str] = {}
    _pending_clarifications: Dict[str, Dict[str, Any]] = {}
    _on_approval_callback: Optional[Callable] = None
    _on_rejection_callback: Optional[Callable] = None
    _on_clarification_callback: Optional[Callable] = None
    _polling_task: Optional[asyncio.Task] = None
    _last_update_id: int = 0
    _state_loaded: bool = False

    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._ensure_state_loaded()

    @classmethod
    def _ensure_state_loaded(cls):
        if cls._state_loaded:
            return
        cls._state_loaded = True
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if TELEGRAM_STATE_FILE.exists():
                with open(TELEGRAM_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cls._discovered_chat_ids = data.get("discovered_chat_ids", [])
                    cls._user_chat_map = data.get("user_chat_map", {})
                logger.info("Loaded Telegram state: %d chat IDs", len(cls._discovered_chat_ids))
        except Exception as exc:
            logger.warning("Failed to load Telegram state file: %s", exc)

    @classmethod
    def _save_state(cls):
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(TELEGRAM_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "discovered_chat_ids": cls._discovered_chat_ids,
                    "user_chat_map": cls._user_chat_map,
                }, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to save Telegram state file: %s", exc)

    @classmethod
    def register_approval_handler(cls, handler: Callable):
        cls._on_approval_callback = handler

    @classmethod
    def register_rejection_handler(cls, handler: Callable):
        cls._on_rejection_callback = handler

    @classmethod
    def register_clarification_handler(cls, handler: Callable):
        cls._on_clarification_callback = handler

    @classmethod
    def register_chat_id(cls, chat_id: str, uid: Optional[str] = None):
        """Register or remember a chat ID discovered from user interaction."""
        cls._ensure_state_loaded()
        str_id = str(chat_id)
        if str_id not in cls._discovered_chat_ids:
            cls._discovered_chat_ids.append(str_id)
            logger.info("Discovered new Telegram chat_id: %s", str_id)
        if uid:
            cls._user_chat_map[uid] = str_id
        cls._save_state()

    def get_effective_chat_id(self, uid: Optional[str] = None) -> Optional[str]:
        """Resolves target Telegram chat ID: configured > user map > discovered list."""
        self._ensure_state_loaded()
        if settings.telegram_chat_id:
            return settings.telegram_chat_id
        if uid and uid in self._user_chat_map:
            return self._user_chat_map[uid]
        if self._discovered_chat_ids:
            return self._discovered_chat_ids[-1]
    async def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Explicitly sets Telegram Bot webhook URL."""
        if not self.bot_token:
            return {"ok": False, "error": "No bot token"}
        url = f"{self.base_url}/setWebhook"
        payload = {"url": webhook_url, "drop_pending_updates": False}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                data = res.json()
                logger.info("Telegram setWebhook to %s: %s", webhook_url, data)
                return data
        except Exception as exc:
            logger.error("Failed to set Telegram webhook to %s: %s", webhook_url, exc)
            return {"ok": False, "error": str(exc)}

    async def ensure_webhook(self, base_url: str) -> bool:
        """Verifies and automatically configures Telegram webhook to match the current deployment URL."""
        if not self.bot_token or not base_url:
            return False
        clean_base = base_url.rstrip("/")
        expected_url = f"{clean_base}/api/telegram/webhook"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(f"{self.base_url}/getWebhookInfo")
                data = res.json()
                current_url = data.get("result", {}).get("url", "")
                if current_url != expected_url:
                    logger.info("Updating Telegram webhook: %s -> %s", current_url, expected_url)
                    set_res = await self.set_webhook(expected_url)
                    return bool(set_res.get("ok"))
                logger.info("Telegram webhook already correctly pointed to %s", expected_url)
                return True
        except Exception as exc:
            logger.warning("Could not check/ensure Telegram webhook: %s", exc)
            return False

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Sends a message to Telegram using Bot API with Composio fallback."""
        if not chat_id:
            return {"ok": False, "status": "NEEDS_CONFIGURATION", "error": "No chat_id provided"}

        url = f"{self.base_url}/sendMessage"
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        # Try direct HTTP first (fast when connected)
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(url, json=payload)
                data = res.json()
                if data.get("ok"):
                    msg_id = data.get("result", {}).get("message_id")
                    return {"ok": True, "message_id": msg_id, "data": data}
                logger.warning("Telegram direct send rejected: %s. Trying Composio fallback...", data)
        except Exception as exc:
            logger.info("Direct Telegram call failed (%s). Falling back to Composio integration...", exc)

        # Fallback to Composio on Lyzr
        try:
            from app.services.lyzr_service import LyzrService
            lyzr = LyzrService()
            comp_res = await lyzr.send_telegram_message(text=text, chat_id=chat_id)
            if isinstance(comp_res, dict) and (
                comp_res.get("successful") is True
                or (isinstance(comp_res.get("data"), dict) and comp_res.get("data", {}).get("ok") is True)
            ):
                data_field = comp_res.get("data", {})
                msg_id = None
                if isinstance(data_field, dict):
                    msg_id = data_field.get("result", {}).get("message_id") or data_field.get("message_id")
                return {"ok": True, "message_id": msg_id, "data": comp_res}
            error_detail = str(comp_res.get("error") or "Composio delivery rejected")
            return {"ok": False, "error": error_detail, "data": comp_res}
        except Exception as comp_err:
            logger.error("Composio Telegram delivery failed: %s", comp_err)
            return {"ok": False, "error": str(comp_err)}

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
    ) -> Dict[str, Any]:
        """Acknowledges button press to remove Telegram spinner."""
        if not self.bot_token:
            return {"ok": False}
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = show_alert
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, json=payload)
                return res.json()
        except Exception as exc:
            logger.error("Failed to answer callback query: %s", exc)
            return {"ok": False, "error": str(exc)}

    async def send_approval_request(
        self,
        action: StagedAction,
        workflow_id: str,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends an approval request with inline buttons:
        [✅ Approve Draft] [❌ Reject Draft]
        """
        target_chat_id = chat_id or self.get_effective_chat_id(action.uid)
        if not target_chat_id:
            logger.info("No Telegram chat ID available to send approval request for %s", action.action_id)
            return {"ok": False, "reason": "no_chat_id"}

        recipient = action.parameters.get("recipient_email") or action.parameters.get("to") or "Unknown"
        subject = action.parameters.get("subject") or action.title
        body = action.parameters.get("body") or action.description

        message_text = (
            f"📬 *LifeOS Human Approval Required*\n\n"
            f"*Workflow:* `{workflow_id}`\n"
            f"*Action:* `{action.action_id}`\n"
            f"*Type:* Gmail Draft\n\n"
            f"*To:* {recipient}\n"
            f"*Subject:* {subject}\n\n"
            f"*Body Preview:*\n{body[:350]}\n\n"
            f"⚡ *Why prepared:* Staged automatically based on voice instructions.\n"
            f"Please review and approve or reject below:"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Approve Draft",
                        "callback_data": f"approve:{action.action_id}:{workflow_id}",
                    },
                    {
                        "text": "❌ Reject Draft",
                        "callback_data": f"reject:{action.action_id}:{workflow_id}",
                    },
                ]
            ]
        }

        res = await self.send_message(
            chat_id=target_chat_id,
            text=message_text,
            reply_markup=reply_markup,
        )
        return res

    async def send_clarification_request(
        self,
        workflow_id: str,
        action_id: str,
        question: str,
        chat_id: Optional[str] = None,
        uid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sends clarification question to user and records pending question."""
        target_chat_id = chat_id or self.get_effective_chat_id(uid)
        if not target_chat_id:
            return {"ok": False, "reason": "no_chat_id"}

        text = (
            f"❓ *LifeOS Clarification Needed*\n\n"
            f"For Workflow `{workflow_id}` (Action `{action_id}`):\n\n"
            f"{question}\n\n"
            f"👉 Reply to this message with the missing details to continue."
        )

        self._pending_clarifications[target_chat_id] = {
            "workflow_id": workflow_id,
            "action_id": action_id,
            "uid": uid,
            "question": question,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return await self.send_message(chat_id=target_chat_id, text=text)

    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a raw Telegram update from webhook or getUpdates polling.
        """
        # 1. Check for Callback Query (Inline Keyboard Buttons)
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb.get("id")
            from_user = cb.get("from", {})
            sender_chat_id = str(from_user.get("id"))
            self.register_chat_id(sender_chat_id)

            data = cb.get("data", "")
            logger.info("Received Telegram callback: %s from %s", data, sender_chat_id)

            if data.startswith("approve:") or data.startswith("reject:"):
                parts = data.split(":")
                action_verb = parts[0]
                action_id = parts[1] if len(parts) > 1 else ""
                workflow_id = parts[2] if len(parts) > 2 else ""

                if action_verb == "approve":
                    await self.answer_callback_query(cb_id, text="Approving and executing action...", show_alert=False)
                    if self._on_approval_callback:
                        asyncio.create_task(self._on_approval_callback(action_id, workflow_id, sender_chat_id))
                    return {"handled": True, "action": "approved", "action_id": action_id}

                elif action_verb == "reject":
                    await self.answer_callback_query(cb_id, text="Action rejected.", show_alert=False)
                    if self._on_rejection_callback:
                        asyncio.create_task(self._on_rejection_callback(action_id, workflow_id, sender_chat_id))
                    return {"handled": True, "action": "rejected", "action_id": action_id}

            await self.answer_callback_query(cb_id, text="Processed.")
            return {"handled": True}

        # 2. Check for Incoming Message
        if "message" in update:
            msg = update["message"]
            chat = msg.get("chat", {})
            chat_id = str(chat.get("id"))
            text = (msg.get("text") or "").strip()

            self.register_chat_id(chat_id)

            if text.startswith("/start"):
                pair_arg = text[len("/start"):].strip()
                paired_user_msg = ""
                if pair_arg:
                    clean_code = pair_arg.replace("pair_", "").strip().upper()
                    try:
                        from app.services.auth_service import AuthService
                        user = AuthService.pair_telegram_by_code(clean_code, chat_id)
                        if user:
                            paired_user_msg = f"\n\n🔗 *Account Linked:* Successfully linked to `{user.email}` ({user.full_name})!"
                            self.register_chat_id(chat_id, uid=user.id)
                    except Exception as err:
                        logger.warning("Error pairing telegram by code: %s", err)

                welcome = (
                    f"👋 *Welcome to LifeOS — Personal AI Operator!*\n\n"
                    f"Connected! Your Telegram Chat ID is `{chat_id}`.{paired_user_msg}\n\n"
                    f"Whenever you speak through Omi, LifeOS automatically:\n"
                    f"• Gathers your context from Qdrant Cloud\n"
                    f"• Coordinates Lyzr multi-agent planning\n"
                    f"• Executes verified low-risk tasks\n"
                    f"• Sends email draft approval requests here\n\n"
                    f"You can approve or reject drafts with a single tap on interactive buttons."
                )
                await self.send_message(chat_id=chat_id, text=welcome)
                return {"handled": True, "command": "/start", "chat_id": chat_id}

            # Check if this text is a reply to a pending clarification
            if chat_id in self._pending_clarifications:
                pending = self._pending_clarifications.pop(chat_id)
                logger.info("Received clarification reply from chat %s: %s", chat_id, text)
                if self._on_clarification_callback:
                    asyncio.create_task(
                        self._on_clarification_callback(
                            workflow_id=pending["workflow_id"],
                            action_id=pending["action_id"],
                            user_reply=text,
                            chat_id=chat_id,
                        )
                    )
                await self.send_message(
                    chat_id=chat_id,
                    text=f"✅ Received your clarification: *\"{text}\"*. Resuming workflow `{pending['workflow_id']}`...",
                )
                return {"handled": True, "type": "clarification_reply", "text": text}

        return {"handled": False}

    async def poll_updates_once(self) -> int:
        """Polls getUpdates once and processes incoming events."""
        if not self.bot_token:
            return 0
        url = f"{self.base_url}/getUpdates"
        params = {"offset": self._last_update_id + 1, "timeout": 2}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url, params=params)
                data = res.json()
                if not data.get("ok"):
                    return 0
                updates = data.get("result", [])
                for u in updates:
                    up_id = u.get("update_id", 0)
                    if up_id > self._last_update_id:
                        self._last_update_id = up_id
                    await self.handle_update(u)
                return len(updates)
        except Exception as exc:
            logger.debug("Telegram polling exception: %s", exc)
            return 0
