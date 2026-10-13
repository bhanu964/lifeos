from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserDB(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False, default="")
    omi_webhook_token = Column(String(64), unique=True, index=True, nullable=False)
    telegram_chat_id = Column(String(64), nullable=True, index=True)
    telegram_pair_code = Column(String(32), unique=True, index=True, nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


class UserCredentialDB(Base):
    __tablename__ = "user_credentials"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    integration_type = Column(String(64), nullable=False, index=True)
    encrypted_payload = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="unconfigured")
    last_verified_at = Column(String(64), nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)

    __table_args__ = (
        Index("ix_user_integration", "user_id", "integration_type", unique=True),
    )


class WorkflowDB(Base):
    __tablename__ = "workflows"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    conversation_id = Column(String(128), nullable=False)
    transcript = Column(Text, nullable=False, default="")
    status = Column(String(32), nullable=False, default="RECEIVED")
    current_stage = Column(String(64), nullable=False, default="voice_received")
    plan_summary = Column(Text, nullable=True)
    idempotency_hash = Column(String(64), nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


class ActionDB(Base):
    __tablename__ = "actions"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    parameters_json = Column(Text, nullable=False, default="{}")
    status = Column(String(32), nullable=False, default="STAGED")
    expires_at = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), nullable=False, index=True)
    execution_result_json = Column(Text, nullable=True)
    verification_status = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


# -------------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------------

class UserSignupRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="User email address")
    password: str = Field(..., min_length=6, description="User password (min 6 chars)")
    full_name: str = Field(default="LifeOS Operator", max_length=120)


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    omi_webhook_token: str
    telegram_chat_id: Optional[str] = None
    telegram_pair_code: Optional[str] = None
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class IntegrationSaveRequest(BaseModel):
    credentials: Dict[str, Any] = Field(..., description="Key-value mapping of integration credentials")


class IntegrationStatusItem(BaseModel):
    integration_type: str
    status: str  # connected, unconfigured, error
    last_verified_at: Optional[str] = None
    masked_fields: Dict[str, str] = Field(default_factory=dict)
    provider_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class UserIntegrationsResponse(BaseModel):
    integrations: Dict[str, IntegrationStatusItem]
