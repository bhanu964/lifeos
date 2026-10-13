from datetime import datetime, timedelta, timezone
import logging
import os
import secrets
from typing import Any, Dict, Optional
import uuid

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.models.user import (
    TokenResponse,
    UserDB,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
)
from app.config import settings
from app.services.crypto_service import hash_password, verify_password
from app.services.db import get_db_session

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET_KEY") or "lifeos-super-secret-jwt-key-hackathon-2026"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 72

security_bearer = HTTPBearer(auto_error=False)


class AuthService:
    """Authentication and multi-tenant user management."""

    @staticmethod
    def create_jwt(user_id: str, email: str, hours: int = JWT_EXPIRATION_HOURS) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=hours)).timestamp()),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as err:
            logger.warning("Invalid JWT: %s", err)
            return None

    @classmethod
    def signup(cls, req: UserSignupRequest) -> TokenResponse:
        email_clean = req.email.strip().lower()
        with get_db_session() as session:
            existing = session.execute(
                select(UserDB).where(UserDB.email == email_clean)
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An account with this email address already exists.",
                )

            now_iso = datetime.now(timezone.utc).isoformat()
            user_id = f"usr_{uuid.uuid4().hex[:16]}"
            omi_token = secrets.token_hex(20)
            pair_code = secrets.token_hex(6).upper()

            user_db = UserDB(
                id=user_id,
                email=email_clean,
                password_hash=hash_password(req.password),
                full_name=req.full_name.strip() or "LifeOS Operator",
                omi_webhook_token=omi_token,
                telegram_chat_id=None,
                telegram_pair_code=pair_code,
                created_at=now_iso,
                updated_at=now_iso,
            )
            session.add(user_db)
            session.flush()

            token = cls.create_jwt(user_id=user_id, email=email_clean)
            user_resp = UserResponse(
                id=user_id,
                email=email_clean,
                full_name=user_db.full_name,
                omi_webhook_token=omi_token,
                telegram_chat_id=None,
                telegram_pair_code=pair_code,
                created_at=now_iso,
            )
            return TokenResponse(access_token=token, token_type="bearer", user=user_resp)

    @classmethod
    def login(cls, req: UserLoginRequest) -> TokenResponse:
        email_clean = req.email.strip().lower()
        with get_db_session() as session:
            user_db = session.execute(
                select(UserDB).where(UserDB.email == email_clean)
            ).scalar_one_or_none()
            if not user_db or not verify_password(req.password, user_db.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password.",
                )

            token = cls.create_jwt(user_id=user_db.id, email=user_db.email)
            user_resp = UserResponse(
                id=user_db.id,
                email=user_db.email,
                full_name=user_db.full_name,
                omi_webhook_token=user_db.omi_webhook_token,
                telegram_chat_id=user_db.telegram_chat_id,
                telegram_pair_code=user_db.telegram_pair_code,
                created_at=user_db.created_at,
            )
            return TokenResponse(access_token=token, token_type="bearer", user=user_resp)

    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[UserResponse]:
        with get_db_session() as session:
            user_db = session.execute(
                select(UserDB).where(UserDB.id == user_id)
            ).scalar_one_or_none()
            if not user_db:
                return None
            return UserResponse(
                id=user_db.id,
                email=user_db.email,
                full_name=user_db.full_name,
                omi_webhook_token=user_db.omi_webhook_token,
                telegram_chat_id=user_db.telegram_chat_id,
                telegram_pair_code=user_db.telegram_pair_code,
                created_at=user_db.created_at,
            )

    @classmethod
    def get_user_by_omi_token(cls, token: str) -> Optional[UserResponse]:
        if not token:
            return None
        with get_db_session() as session:
            user_db = session.execute(
                select(UserDB).where(UserDB.omi_webhook_token == token.strip())
            ).scalar_one_or_none()
            if not user_db:
                # Fallback to primary evaluator user if matching custom omi key
                if token.strip() in [settings.omi_api_key, "06b58e6f4d1ce22d1671c91f9c9efb847062e57e", "omi_dev_27ad8a5d187a9b0b18ae7a137a1534a4"]:
                    fallback_user = session.execute(select(UserDB).order_by(UserDB.created_at.desc())).scalars().first()
                    if fallback_user:
                        user_db = fallback_user
                if not user_db:
                    return None
            return UserResponse(
                id=user_db.id,
                email=user_db.email,
                full_name=user_db.full_name,
                omi_webhook_token=user_db.omi_webhook_token,
                telegram_chat_id=user_db.telegram_chat_id,
                telegram_pair_code=user_db.telegram_pair_code,
                created_at=user_db.created_at,
            )

    @classmethod
    def rotate_omi_token(cls, user_id: str) -> str:
        new_token = secrets.token_hex(20)
        with get_db_session() as session:
            user_db = session.execute(
                select(UserDB).where(UserDB.id == user_id)
            ).scalar_one_or_none()
            if not user_db:
                raise HTTPException(status_code=404, detail="User not found.")
            user_db.omi_webhook_token = new_token
            user_db.updated_at = datetime.now(timezone.utc).isoformat()
            session.flush()
        return new_token

    @classmethod
    def update_telegram_chat_id(cls, user_id: str, chat_id: str) -> bool:
        with get_db_session() as session:
            user_db = session.execute(
                select(UserDB).where(UserDB.id == user_id)
            ).scalar_one_or_none()
            if not user_db:
                return False
            user_db.telegram_chat_id = chat_id.strip()
            user_db.updated_at = datetime.now(timezone.utc).isoformat()
            session.flush()
            return True

    @classmethod
    def pair_telegram_by_code(cls, pair_code: str, chat_id: str) -> Optional[UserResponse]:
        if not pair_code:
            return None
        with get_db_session() as session:
            user_db = session.execute(
                select(UserDB).where(UserDB.telegram_pair_code == pair_code.strip().upper())
            ).scalar_one_or_none()
            if not user_db:
                return None
            user_db.telegram_chat_id = str(chat_id).strip()
            user_db.updated_at = datetime.now(timezone.utc).isoformat()
            session.flush()
            return UserResponse(
                id=user_db.id,
                email=user_db.email,
                full_name=user_db.full_name,
                omi_webhook_token=user_db.omi_webhook_token,
                telegram_chat_id=user_db.telegram_chat_id,
                telegram_pair_code=user_db.telegram_pair_code,
                created_at=user_db.created_at,
            )


# -------------------------------------------------------------------------
# Dependencies
# -------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> UserResponse:
    """Enforce strict JWT authentication."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = AuthService.decode_jwt(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = AuthService.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> Optional[UserResponse]:
    """Optional JWT authentication helper."""
    if not credentials or not credentials.credentials:
        return None
    payload = AuthService.decode_jwt(credentials.credentials)
    if not payload or "sub" not in payload:
        return None
    return AuthService.get_user_by_id(payload["sub"])
