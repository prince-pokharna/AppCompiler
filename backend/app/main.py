from __future__ import annotations

from app.env_loader import load_app_env

load_app_env()  # must run before any other app imports

"""FastAPI application entry point."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, init_db
from app.redis_client import close_redis
from app.routers import evaluate, generate, health, status
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.utils.logger import setup_logging
from app.utils.structured_log import configure_structlog


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    settings = get_settings()

    # Startup
    setup_logging(level="DEBUG" if settings.debug else "INFO")
    configure_structlog(level="DEBUG" if settings.debug else "INFO")
    logger = logging.getLogger("appcompiler")
    logger.info(
        f"Starting AppCompiler v{settings.app_version} ({settings.environment})"
    )

    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:
        logger.critical(
            "\n\n"
            "╔══════════════════════════════════════════════════════════╗\n"
            "║           DATABASE CONNECTION FAILED — EXITING           ║\n"
            "╠══════════════════════════════════════════════════════════╣\n"
            f"║  {str(exc)[:56]:<56} ║\n"
            "╠══════════════════════════════════════════════════════════╣\n"
            "║  Quick fixes:                                            ║\n"
            "║  1. Start PostgreSQL:  pg_ctl start                      ║\n"
            "║     Or on Windows:    net start postgresql-x64-16        ║\n"
            "║  2. Check .env has:   DATABASE_URL=postgresql+asyncpg:// ║\n"
            "║                       user:pass@localhost:5432/dbname    ║\n"
            "║  3. No PostgreSQL?    Leave DATABASE_URL empty for       ║\n"
            "║     SQLite dev mode (auto-fallback)                      ║\n"
            "╚══════════════════════════════════════════════════════════╝\n"
        )
        sys.exit(1)

    yield

    # Shutdown
    logger.info("Shutting down AppCompiler")
    await engine.dispose()
    await close_redis()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="AppCompiler API",
        description="Natural Language to App Generator — compiles NL descriptions into validated schemas and working Next.js scaffolds.",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(generate.router)
    app.include_router(status.router)
    app.include_router(evaluate.router)
    app.include_router(health.router)

    return app


app = create_app()
