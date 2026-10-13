import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.models.user import (
    IntegrationSaveRequest,
    IntegrationStatusItem,
    UserIntegrationsResponse,
    UserResponse,
)
from app.services.auth_service import get_current_user
from app.services.user_credentials_service import UserCredentialsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations", tags=["SaaS Integrations Wizard"])


@router.get("", response_model=UserIntegrationsResponse, summary="List all integrations status for user")
async def list_integrations(current_user: UserResponse = Depends(get_current_user)):
    """
    Returns the real connection status and masked keys for all supported integrations.
    Never exposes raw secrets or unmasked tokens.
    """
    statuses = UserCredentialsService.list_all_statuses(current_user.id)
    return UserIntegrationsResponse(integrations=statuses)


@router.post("/{integration_type}", response_model=IntegrationStatusItem, summary="Save or update integration credentials")
async def save_integration(
    integration_type: str,
    request: IntegrationSaveRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Encrypts and persists credentials at rest for the specified integration.
    """
    try:
        return UserCredentialsService.save_credentials(
            user_id=current_user.id,
            integration_type=integration_type,
            raw_credentials=request.credentials,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.error("Error saving credentials for %s: %s", integration_type, exc)
        raise HTTPException(status_code=500, detail=f"Failed to save integration: {str(exc)}")


@router.post("/{integration_type}/test", summary="Test live connectivity for an integration")
async def test_integration(
    integration_type: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Validates live connection to external service (Qdrant, Lyzr, Telegram, Google).
    """
    result = await UserCredentialsService.test_integration(
        user_id=current_user.id,
        integration_type=integration_type,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Integration test failed."),
        )
    return result


@router.delete("/{integration_type}", summary="Disconnect and delete integration credentials")
async def disconnect_integration(
    integration_type: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Safely removes stored credentials for an integration.
    """
    UserCredentialsService.delete_credentials(current_user.id, integration_type)
    return {"success": True, "message": f"{integration_type} disconnected successfully."}


@router.get("/omi/webhook-info", summary="Get personalized Omi webhook endpoints")
async def get_omi_webhook_info(current_user: UserResponse = Depends(get_current_user)):
    """
    Returns the personalized Omi webhook endpoint URLs and setup instructions for this user.
    """
    base_url = settings.public_base_url.rstrip("/")
    token = current_user.omi_webhook_token
    conversation_url = f"{base_url}/omi/v2/{token}/conversation"
    realtime_url = f"{base_url}/omi/v2/{token}/realtime"

    return {
        "webhook_token": token,
        "conversation_webhook_url": conversation_url,
        "realtime_webhook_url": realtime_url,
        "setup_steps": [
            "Open the Omi app on your phone (iOS/Android).",
            "Go to Settings -> Developer -> Webhooks.",
            f"Paste your Conversation Webhook URL: {conversation_url}",
            "Check 'Send on session complete'.",
            "Speak naturally with Omi. LifeOS will automatically trigger your personal AI operator!",
        ],
    }
