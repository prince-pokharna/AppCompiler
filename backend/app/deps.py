"""FastAPI dependencies — API authentication."""

from __future__ import annotations

import os

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

security = HTTPBearer(auto_error=True)


def _expected_api_key() -> str:
    """Resolve API key from env (API_SECRET_KEY preferred, SECRET_KEY fallback)."""
    return (
        os.getenv("API_SECRET_KEY")
        or os.getenv("SECRET_KEY")
        or get_settings().secret_key
    )


def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Validate Bearer token against configured API secret."""
    expected = _expected_api_key()
    if not expected or expected == "default-dev-secret-key-change-in-production":
        if get_settings().is_production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API_SECRET_KEY is not configured",
            )
    if credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
