"""Load environment variables from repo root and backend-local .env files."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# backend/app/env_loader.py -> repo root is parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def load_app_env() -> None:
    """Load .env from repository root, then backend (backend overrides root)."""
    load_dotenv(_REPO_ROOT / ".env", override=False)
    load_dotenv(_BACKEND_ROOT / ".env", override=True)
