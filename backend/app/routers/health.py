from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint returning service status, metadata,
    and configured integration flags.
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "integrations": {
            "lyzr_configured": bool(settings.lyzr_api_key),
            "qdrant_configured": bool(settings.qdrant_url and settings.qdrant_api_key),
            "omi_configured": bool(settings.omi_api_key),
        },
    }
