"""Per-IP rate limiting for generation endpoints using Redis counters."""

from __future__ import annotations

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.redis_client import get_redis

logger = logging.getLogger("appcompiler.middleware.rate_limit")

GENERATE_LIMIT = 5
GENERATE_WINDOW_SECONDS = 3600
RATE_LIMITED_PATHS = {"/api/generate", "/api/evaluate"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit expensive endpoints to N requests per IP per hour."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path in RATE_LIMITED_PATHS:
            client_ip = request.client.host if request.client else "unknown"
            key = f"ratelimit:{request.url.path}:{client_ip}"

            try:
                r = await get_redis()
                count = await r.incr(key)
                if count == 1:
                    await r.expire(key, GENERATE_WINDOW_SECONDS)

                if count > GENERATE_LIMIT:
                    logger.warning(
                        "rate_limit_exceeded",
                        extra={"ip": client_ip, "path": request.url.path, "count": count},
                    )
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": (
                                f"Rate limit exceeded: max {GENERATE_LIMIT} "
                                f"requests per hour for this endpoint"
                            ),
                        },
                    )
            except Exception as exc:
                logger.warning(f"Rate limit check skipped: {exc}")

        return await call_next(request)
