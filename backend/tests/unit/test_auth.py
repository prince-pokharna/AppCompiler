"""Unit tests for API authentication."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.deps import verify_token


def test_verify_token_valid():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-api-secret-key")
    assert verify_token(creds) == "test-api-secret-key"


def test_verify_token_invalid():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-key")
    with pytest.raises(HTTPException) as exc:
        verify_token(creds)
    assert exc.value.status_code == 401
