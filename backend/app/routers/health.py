"""Health router — GET /api/health (unauthenticated)."""

from __future__ import annotations

import time

from fastapi import APIRouter, status
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.schemas.api_models import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])

_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health_check() -> HealthResponse:
    """Health check endpoint — no authentication required."""
    settings = get_settings()
    uptime = time.time() - _start_time

    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        from app.redis_client import get_redis
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        pass

    llm_ok = bool(settings.openai_api_key and settings.openai_api_key.startswith("sk-"))

    return HealthResponse(
        status="ok" if (db_ok and redis_ok) else "degraded",
        version=settings.app_version,
        uptime_seconds=round(uptime, 1),
        environment=settings.environment,
        llm_available=llm_ok,
        database_connected=db_ok,
        redis_connected=redis_ok,
    )
