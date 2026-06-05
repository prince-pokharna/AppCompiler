"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# Force test env before any app imports (ignore repo .env from shell)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-unit-tests"
os.environ["API_SECRET_KEY"] = "test-api-secret-key"
os.environ["SECRET_KEY"] = "test-api-secret-key"

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
async def init_test_database(monkeypatch):
    """Create tables in the in-memory SQLite database."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    from app.database import engine, init_db
    from app import database as db_module

    db_module.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    await init_db()


@pytest.fixture(autouse=True)
async def fake_redis(monkeypatch):
    """Use in-memory Redis so tests do not require a running Redis server."""
    import fakeredis.aioredis

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def _get_redis():
        return fake

    monkeypatch.setattr("app.redis_client.get_redis", _get_redis)
    monkeypatch.setattr("app.redis_client._redis_pool", None)


@pytest.fixture
def intent_fixture() -> dict:
    path = FIXTURES_DIR / "intent_response.json"
    return json.loads(path.read_text(encoding="utf-8"))
