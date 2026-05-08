"""Health router — GET /api/health."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, status

from app.config import get_settings
from app.schemas.api_models import HealthResponse

logger = logging.getLogger("appcompiler.routers.health")

router = APIRouter(prefix="/api", tags=["health"])

_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    settings = get_settings()
    uptime = time.time() - _start_time

    # Check database
    db_ok = False
    try:
        from app.database import get_engine
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            db_ok = True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")

    # Check Redis
    redis_ok = False
    try:
        from app.redis_client import get_redis
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")

    # Check LLM
    llm_ok = bool(settings.anthropic_api_key and settings.anthropic_api_key.startswith("sk-"))

    return HealthResponse(
        status="ok" if (db_ok and redis_ok) else "degraded",
        version=settings.app_version,
        uptime_seconds=round(uptime, 1),
        environment=settings.environment,
        llm_available=llm_ok,
        database_connected=db_ok,
        redis_connected=redis_ok,
    )
