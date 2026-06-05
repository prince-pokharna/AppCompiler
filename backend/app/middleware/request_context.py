"""Request correlation ID middleware for structured tracing."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.utils.structured_log import bind_context, clear_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to each request for log tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        bind_context(request_id=request_id, path=request.url.path, method=request.method)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            clear_context()
