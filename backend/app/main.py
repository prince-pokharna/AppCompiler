"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import close_db, init_db
from app.redis_client import close_redis
from app.routers import evaluate, generate, health, status
from app.utils.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    settings = get_settings()

    # Startup
    setup_logging(level="DEBUG" if settings.debug else "INFO")
    logger = logging.getLogger("appcompiler")
    logger.info(
        f"Starting AppCompiler v{settings.app_version} ({settings.environment})"
    )

    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down AppCompiler")
    await close_db()
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
