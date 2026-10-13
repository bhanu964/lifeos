import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import (
    TokenResponse,
    UpdateProfileRequest,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
)
from app.services.auth_service import AuthService, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["SaaS Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Create a new SaaS account")
async def signup(request: UserSignupRequest):
    """
    Registers a new tenant user with a secure hashed password,
    provisions a unique cryptographically random Omi webhook token,
    and returns a signed JWT access token.
    """
    return AuthService.signup(request)


@router.post("/login", response_model=TokenResponse, summary="Log in with email and password")
async def login(request: UserLoginRequest):
    """
    Authenticates existing user and issues a signed JWT access token.
    """
    return AuthService.login(request)


@router.get("/me", response_model=UserResponse, summary="Get current authenticated user profile")
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """
    Returns the authenticated user's profile and unique webhook token.
    """
    return current_user


@router.post("/logout", summary="Log out current user")
async def logout(current_user: UserResponse = Depends(get_current_user)):
    """
    Stateless JWT logout endpoint. Signals client to discard token.
    """
    return {"success": True, "message": "Successfully logged out."}


@router.post("/rotate-omi-token", summary="Generate a new random Omi webhook token")
async def rotate_omi_token(current_user: UserResponse = Depends(get_current_user)):
    """
    Revokes previous Omi webhook token and generates a new cryptographically random token.
    """
    new_token = AuthService.rotate_omi_token(current_user.id)
    return {
        "success": True,
        "omi_webhook_token": new_token,
        "message": "Omi webhook token rotated successfully. Update your Omi mobile app URL.",
    }


@router.put("/profile", response_model=UserResponse, summary="Update user profile settings")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Updates profile details (e.g. display name, telegram chat ID).
    """
    if request.telegram_chat_id is not None:
        AuthService.update_telegram_chat_id(current_user.id, request.telegram_chat_id)
    
    updated = AuthService.get_user_by_id(current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found.")
    return updated
