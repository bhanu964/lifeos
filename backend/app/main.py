from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    health_router,
    omi_router,
    agents_router,
    memories_router,
    lifeos_router,
    auth_router,
    integrations_router,
)
from app.services.db import init_db
from app.services.qdrant_service import QdrantService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agentmemory")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    Initializes vector collection on startup and performs clean teardown.
    """
    logger.info("Starting up AgentMemory AI backend...")
    try:
        init_db()
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)

    qdrant = QdrantService()
    try:
        if settings.qdrant_url:
            connected = await qdrant.verify_connection()
            if connected:
                logger.info("Connected to Qdrant Cloud. Ensuring collection '%s' is provisioned...", settings.qdrant_collection_name)
                await qdrant.init_collection()
            else:
                logger.warning("Could not verify Qdrant Cloud connection on startup. Will retry on demand.")
        else:
            logger.warning("QDRANT_URL is not set. Memory vector storage will be unavailable.")
    except Exception as exc:
        logger.error("Error during Qdrant startup verification: %s", exc)
    finally:
        await qdrant.close()

    yield

    logger.info("Shutting down AgentMemory AI backend...")


app = FastAPI(
    title="AgentMemory AI",
    description="Voice-driven collaborative multi-agent AI system with Omi, Qdrant, and Lyzr.",
    version=settings.app_version,
    lifespan=lifespan,
)

# Determine explicit allowed origins for CORS
_default_dev_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
    "https://lifeos-pi-gules.vercel.app",
]
_configured_origins = [
    origin.strip().rstrip("/")
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip()
]

# Always permit all Vercel production and preview domains (*.vercel.app)
_origin_regex = r"^https://.*\.vercel\.app$"
_allowed_origins = list(set(_default_dev_origins + _configured_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health_router)
app.include_router(omi_router)
app.include_router(agents_router)
app.include_router(memories_router)
app.include_router(lifeos_router)
app.include_router(auth_router)
app.include_router(integrations_router)


@app.get("/", summary="Root endpoint")
async def root():
    return {
        "message": "Welcome to AgentMemory AI API",
        "docs": "/docs",
        "health": "/health",
        "version": settings.app_version,
    }
