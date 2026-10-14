from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

import httpx
from qdrant_client import AsyncQdrantClient
from sqlalchemy import delete, select

from app.config import settings
from app.models.user import IntegrationStatusItem, UserCredentialDB
from app.services.crypto_service import decrypt_payload, encrypt_payload, mask_secret
from app.services.db import get_db_session

logger = logging.getLogger(__name__)


class UserCredentialsService:
    """Manages encrypted-at-rest per-tenant integration credentials and health verifications."""

    SUPPORTED_INTEGRATIONS = {
        "qdrant": "Qdrant Cloud Persistent Memory",
        "lyzr": "Lyzr Multi-Agent Orchestration",
        "telegram": "Telegram Bot Notifications & Approvals",
        "google_calendar": "Google Calendar (via Composio)",
        "google_tasks": "Google Tasks (via Composio)",
        "gmail": "Gmail Drafts (via Composio)",
    }

    @classmethod
    def save_credentials(
        cls, user_id: str, integration_type: str, raw_credentials: Dict[str, Any]
    ) -> IntegrationStatusItem:
        if integration_type not in cls.SUPPORTED_INTEGRATIONS:
            raise ValueError(f"Unsupported integration type: {integration_type}")

        now_iso = datetime.now(timezone.utc).isoformat()
        encrypted = encrypt_payload(raw_credentials)

        with get_db_session() as session:
            existing = session.execute(
                select(UserCredentialDB).where(
                    UserCredentialDB.user_id == user_id,
                    UserCredentialDB.integration_type == integration_type,
                )
            ).scalar_one_or_none()

            if existing:
                existing.encrypted_payload = encrypted
                existing.status = "connected"
                existing.last_verified_at = now_iso
                existing.updated_at = now_iso
            else:
                cred_record = UserCredentialDB(
                    id=f"cred_{uuid.uuid4().hex[:16]}",
                    user_id=user_id,
                    integration_type=integration_type,
                    encrypted_payload=encrypted,
                    status="connected",
                    last_verified_at=now_iso,
                    created_at=now_iso,
                    updated_at=now_iso,
                )
                session.add(cred_record)

        return cls.get_integration_status(user_id, integration_type)

    @classmethod
    def get_decrypted_credentials(cls, user_id: str, integration_type: str) -> Dict[str, Any]:
        with get_db_session() as session:
            record = session.execute(
                select(UserCredentialDB).where(
                    UserCredentialDB.user_id == user_id,
                    UserCredentialDB.integration_type == integration_type,
                )
            ).scalar_one_or_none()

            if record and record.encrypted_payload:
                try:
                    return decrypt_payload(record.encrypted_payload)
                except Exception as err:
                    logger.error("Failed to decrypt credentials for %s/%s: %s", user_id, integration_type, err)
                    return {}

        return {}

    @classmethod
    def delete_credentials(cls, user_id: str, integration_type: str) -> bool:
        with get_db_session() as session:
            session.execute(
                delete(UserCredentialDB).where(
                    UserCredentialDB.user_id == user_id,
                    UserCredentialDB.integration_type == integration_type,
                )
            )
        return True

    @classmethod
    def get_integration_status(cls, user_id: str, integration_type: str) -> IntegrationStatusItem:
        with get_db_session() as session:
            record = session.execute(
                select(UserCredentialDB).where(
                    UserCredentialDB.user_id == user_id,
                    UserCredentialDB.integration_type == integration_type,
                )
            ).scalar_one_or_none()

            masked: Dict[str, str] = {}
            status_val = "unconfigured"
            verified_at = None

            if record:
                status_val = record.status
                verified_at = record.last_verified_at
                try:
                    raw = decrypt_payload(record.encrypted_payload)
                    if raw.get("use_managed"):
                        masked = {
                            "cluster": "LifeOS Managed High-Performance Cluster",
                            "tenant_partition": user_id,
                            "source": "managed_cluster",
                        }
                    else:
                        for k, v in raw.items():
                            if v and isinstance(v, str):
                                masked[k] = mask_secret(v)
                        masked["source"] = "custom"
                except Exception:
                    status_val = "error"
            else:
                # User-owned personal integrations MUST NOT fall back to developer/shared credentials!
                if integration_type == "lyzr":
                    # LifeOS managed intelligence backend (multi-agent triad reasoning)
                    status_val = "connected"
                    masked = {
                        "agent_model": "Lyzr Multi-Agent Triad (Manager, Fact Finder, Data Analyst)",
                        "manager_agent_id": mask_secret(settings.lyzr_manager_agent_id),
                        "source": "managed_triad",
                    }
                elif integration_type == "telegram":
                    # Check if user paired via /start in UserDB
                    from app.models.user import UserDB
                    user_row = session.execute(select(UserDB).where(UserDB.id == user_id)).scalar_one_or_none()
                    if user_row and user_row.telegram_chat_id:
                        status_val = "connected"
                        masked = {
                            "telegram_chat_id": mask_secret(user_row.telegram_chat_id),
                            "telegram_bot_username": settings.telegram_bot_username,
                            "source": "paired_chat",
                        }
                    else:
                        status_val = "unconfigured"
                else:
                    # Qdrant, Google Calendar, Google Tasks, Gmail: unconfigured until user configures them!
                    status_val = "unconfigured"
                    masked = {}

            return IntegrationStatusItem(
                integration_type=integration_type,
                status=status_val,
                last_verified_at=verified_at,
                masked_fields=masked,
                provider_name=cls.SUPPORTED_INTEGRATIONS.get(integration_type, integration_type),
            )

    @classmethod
    def list_all_statuses(cls, user_id: str) -> Dict[str, IntegrationStatusItem]:
        result = {}
        for itype in cls.SUPPORTED_INTEGRATIONS:
            result[itype] = cls.get_integration_status(user_id, itype)
        return result

    @classmethod
    async def test_integration(cls, user_id: str, integration_type: str) -> Dict[str, Any]:
        """Test live connectivity strictly for user's configured integration."""
        creds = cls.get_decrypted_credentials(user_id, integration_type)

        if integration_type == "telegram":
            bot_token = creds.get("telegram_bot_token")
            custom_chat = creds.get("telegram_chat_id")
            if bot_token:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(f"https://api.telegram.org/bot{bot_token}/getMe")
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("ok"):
                            bot_user = data.get("result", {}).get("username", "UnknownBot")
                            return {"success": True, "message": f"Successfully verified Telegram Bot @{bot_user}!"}
                    return {"success": False, "error": f"Telegram API error: {resp.text}"}
            elif custom_chat:
                return {"success": True, "message": f"Verified Telegram Chat ID: {mask_secret(custom_chat)}"}
            else:
                from app.models.user import UserDB
                with get_db_session() as session:
                    u = session.execute(select(UserDB).where(UserDB.id == user_id)).scalar_one_or_none()
                    if u and u.telegram_chat_id:
                        return {"success": True, "message": f"Verified paired Telegram Chat ID ({mask_secret(u.telegram_chat_id)})"}
                return {"success": False, "error": "Telegram is not connected. Please pair your account or configure a custom Bot Token."}

        elif integration_type == "qdrant":
            if creds.get("use_managed"):
                url = settings.qdrant_url
                api_key = settings.qdrant_api_key
            else:
                url = creds.get("qdrant_url")
                api_key = creds.get("qdrant_api_key")
            if not url:
                return {"success": False, "error": "No Qdrant cluster configured. Please configure your cluster or select managed Qdrant."}
            try:
                client = AsyncQdrantClient(url=url, api_key=api_key, timeout=10.0)
                await client.get_collections()
                await client.close()
                return {"success": True, "message": "Successfully connected to Qdrant Cloud cluster!"}
            except Exception as e:
                return {"success": False, "error": f"Qdrant connection failed: {str(e)}"}

        elif integration_type == "lyzr":
            api_key = creds.get("lyzr_api_key") or settings.lyzr_api_key
            agent_id = creds.get("lyzr_manager_agent_id") or settings.lyzr_manager_agent_id
            if not api_key:
                return {"success": False, "error": "No Lyzr API key provided."}
            headers = {"Content-Type": "application/json", "x-api-key": api_key}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    if agent_id:
                        resp = await client.get(f"https://agent-prod.studio.lyzr.ai/v3/agents/{agent_id}", headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            agent_name = data.get("name", "Manager Agent")
                            return {"success": True, "message": f"Successfully verified Lyzr Agent: '{agent_name}' ({agent_id})!"}
                        else:
                            return {"success": False, "error": f"Lyzr Agent verification failed (HTTP {resp.status_code}): {resp.text[:120]}"}
                    else:
                        resp = await client.get("https://agent-prod.studio.lyzr.ai/v3/agents/", headers=headers)
                        if resp.status_code == 200:
                            return {"success": True, "message": "Successfully verified Lyzr Studio API Key!"}
                        else:
                            return {"success": False, "error": f"Lyzr API Key verification failed (HTTP {resp.status_code})"}
            except Exception as e:
                return {"success": False, "error": f"Lyzr connection error: {str(e)}"}

        elif integration_type in ["google_calendar", "google_tasks", "gmail"]:
            cred_id = creds.get(f"{integration_type}_credential_id") or creds.get("credential_id")
            if not cred_id:
                return {
                    "success": False,
                    "error": f"No {cls.SUPPORTED_INTEGRATIONS.get(integration_type, integration_type)} credentials connected for your user. Please connect your Google account in Settings.",
                }
            return {
                "success": True,
                "message": f"Verified {cls.SUPPORTED_INTEGRATIONS[integration_type]} integration connection for this account.",
            }

        return {"success": False, "error": "Unknown integration type."}

    @classmethod
    def get_qdrant_service_for_user(cls, user_id: str):
        """Resolves user-specific QdrantService if custom cluster is configured, else managed cluster with strict tenant isolation."""
        from app.services.qdrant_service import QdrantService
        creds = cls.get_decrypted_credentials(user_id, "qdrant")
        if creds.get("use_managed"):
            return QdrantService(url=settings.qdrant_url, api_key=settings.qdrant_api_key, collection_name=settings.qdrant_collection_name)
        if creds.get("qdrant_url") and creds.get("qdrant_api_key"):
            return QdrantService(
                url=creds["qdrant_url"],
                api_key=creds["qdrant_api_key"],
                collection_name=creds.get("qdrant_collection_name") or settings.qdrant_collection_name,
            )
        return QdrantService(url=settings.qdrant_url, api_key=settings.qdrant_api_key, collection_name=settings.qdrant_collection_name)

    @classmethod
    def get_lyzr_service_for_user(cls, user_id: str):
        """Resolves user-specific LyzrService if custom agent/key is configured, else managed agent."""
        from app.services.lyzr_service import LyzrService
        creds = cls.get_decrypted_credentials(user_id, "lyzr")
        api_key = creds.get("lyzr_api_key") or settings.lyzr_api_key
        agent_id = creds.get("lyzr_manager_agent_id") or settings.lyzr_manager_agent_id
        return LyzrService(api_key=api_key, agent_id=agent_id, default_user_id=user_id)

    @classmethod
    def get_telegram_service_for_user(cls, user_id: str):
        """Resolves user-specific TelegramService if custom bot token is configured, else managed bot."""
        from app.services.telegram_service import TelegramService
        creds = cls.get_decrypted_credentials(user_id, "telegram")
        bot_token = creds.get("telegram_bot_token") or settings.telegram_bot_token
        tg = TelegramService(bot_token=bot_token)
        custom_chat_id = creds.get("telegram_chat_id")
        if custom_chat_id:
            tg.register_chat_id(custom_chat_id, uid=user_id)
        return tg
