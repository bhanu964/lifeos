from pathlib import Path
from typing import Optional
import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Locate and load active .env file
_possible_dotenvs = [
    Path.cwd() / "agentmemory-ai" / ".env",
    Path.cwd() / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]
for _env_path in _possible_dotenvs:
    if _env_path.exists() and _env_path.is_file():
        load_dotenv(_env_path, override=False)
        break


class Settings(BaseSettings):
    """
    Configuration management for AgentMemory AI.
    Loads from environment variables and .env files securely.
    """
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    app_name: str = "AgentMemory AI"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    # Lyzr Agent Settings
    lyzr_api_key: str = Field(default="", alias="LYZR_API_KEY")
    lyzr_api_url: str = Field(
        default="https://agent-prod.studio.lyzr.ai/v3/inference/chat/",
        alias="LYZR_API_URL"
    )
    lyzr_research_agent_id: str = Field(
        default="6acd9f07cb0aafc9293bd126",
        alias="LYZR_RESEARCH_AGENT_ID"
    )
    lyzr_fact_finder_agent_id: str = Field(
        default="6acd9f07cb0aafc9293bd126",
        alias="LYZR_FACT_FINDER_AGENT_ID"
    )
    lyzr_data_analyst_agent_id: str = Field(
        default="6acd1ec70b4f09cf4da21e21",
        alias="LYZR_DATA_ANALYST_AGENT_ID"
    )
    lyzr_manager_agent_id: str = Field(
        default="6acdcd0f8a6a8741bd6df3df",
        alias="LYZR_MANAGER_AGENT_ID"
    )
    lyzr_user_id: str = Field(default="demo-user@agentmemory.ai", alias="LYZR_USER_ID")
    lyzr_tool_execute_url: str = Field(
        default="https://agent-prod.studio.lyzr.ai/v3/inference/tools/execute",
        alias="LYZR_TOOL_EXECUTE_URL",
    )

    # Google Calendar & Tasks Integration Settings (Composio on Lyzr)
    google_calendar_credential_id: str = Field(
        default="ad9dc0f9-2516-4224-bec8-26c8a9149cb4",
        alias="GOOGLE_CALENDAR_CREDENTIAL_ID",
    )
    google_calendar_provider_uuid: str = Field(
        default="6980d819100ddff45dec4e82",
        alias="GOOGLE_CALENDAR_PROVIDER_UUID",
    )
    google_tasks_credential_id: str = Field(
        default="3ee4c6f4-2d0f-44ac-afc4-a97ddd2a230f",
        alias="GOOGLE_TASKS_CREDENTIAL_ID",
    )
    google_tasks_provider_uuid: str = Field(
        default="6980d819100ddff45dec4e8a",
        alias="GOOGLE_TASKS_PROVIDER_UUID",
    )

    # Gmail Integration Settings (Composio on Lyzr)
    gmail_provider_uuid: str = Field(
        default="6980d819100ddff45dec4e80",
        alias="GMAIL_PROVIDER_UUID",
    )
    gmail_credential_id: str = Field(
        default="9dc55477-f8de-4f9c-a0a9-8846cb6c020c",
        alias="GMAIL_CREDENTIAL_ID",
    )

    # Telegram Integration Settings (Composio on Lyzr)
    telegram_provider_uuid: str = Field(
        default="699eea45c7cb89e0f6baa8ba",
        alias="TELEGRAM_PROVIDER_UUID",
    )
    telegram_credential_id: str = Field(
        default="a5a5dfe8-22ab-4c17-bdb1-8ff212a94846",
        alias="TELEGRAM_CREDENTIAL_ID",
    )
    telegram_chat_id: str = Field(
        default="",
        alias="TELEGRAM_CHAT_ID",
    )
    telegram_bot_username: str = Field(
        default="Ididhswkje_bot",
        alias="TELEGRAM_BOT_USERNAME",
    )
    telegram_bot_token: str = Field(
        default="",
        alias="TELEGRAM_BOT_TOKEN",
    )
    public_base_url: str = Field(
        default="",
        alias="PUBLIC_BASE_URL",
    )
    cors_allowed_origins: str = Field(
        default="",
        alias="CORS_ALLOWED_ORIGINS",
    )
    jwt_secret_key: str = Field(
        default="",
        alias="JWT_SECRET_KEY",
    )
    encryption_key: str = Field(
        default="",
        alias="ENCRYPTION_KEY",
    )
    database_url: str = Field(
        default="",
        alias="DATABASE_URL",
    )

    # Qdrant Cloud Vector Database Settings
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    qdrant_collection_name: str = Field(
        default="agentmemory_memories",
        alias="QDRANT_COLLECTION_NAME"
    )

    # Omi Voice & Webhook Settings
    omi_api_key: str = Field(default="", alias="OMI_API_KEY")

    # FastEmbed Settings (Fixed to BAAI/bge-small-en-v1.5, 384 dims)
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    def get_status_report(self) -> dict[str, str]:
        """
        Reports the presence or absence of required configuration variables
        using only their names and status. Never reveals values.
        """
        required_keys = {
            "LYZR_API_KEY": bool(self.lyzr_api_key),
            "LYZR_API_URL": bool(self.lyzr_api_url),
            "LYZR_RESEARCH_AGENT_ID": bool(self.lyzr_research_agent_id),
            "LYZR_USER_ID": bool(self.lyzr_user_id),
            "GOOGLE_CALENDAR_INTEGRATION": bool(self.google_calendar_credential_id),
            "GOOGLE_TASKS_INTEGRATION": bool(self.google_tasks_credential_id),
            "GMAIL_INTEGRATION": bool(self.gmail_credential_id),
            "TELEGRAM_INTEGRATION": bool(self.telegram_credential_id),
            "QDRANT_URL": bool(self.qdrant_url),
            "QDRANT_API_KEY": bool(self.qdrant_api_key),
            "QDRANT_COLLECTION_NAME": bool(self.qdrant_collection_name),
            "OMI_API_KEY": bool(self.omi_api_key),
        }
        return {key: ("PRESENT" if is_set else "MISSING") for key, is_set in required_keys.items()}

    @classmethod
    def load(cls) -> "Settings":
        settings = cls()

        # Fallback to alternate keys if standard ones are not present
        if not settings.qdrant_api_key:
            alt = os.getenv("QdrantAPIKEY")
            if alt:
                settings.qdrant_api_key = alt.strip()

        if not settings.qdrant_url:
            alt = os.getenv("Qdrant Cluster Endpoint") or os.getenv("QDRANT_CLUSTER_ENDPOINT")
            if alt:
                settings.qdrant_url = alt.strip()

        if not settings.lyzr_api_key:
            alt = os.getenv("Lyzr API") or os.getenv("LYZR_API")
            if alt:
                settings.lyzr_api_key = alt.strip()

        if not settings.omi_api_key:
            alt = os.getenv("Omi_api_key") or os.getenv("OMI_KEY")
            if alt:
                settings.omi_api_key = alt.strip()

        return settings


settings = Settings.load()

