"""Generation router — POST /api/generate."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.deps import verify_token
from app.models.generation import GenerationJob
from app.pipeline.orchestrator import run_pipeline
from app.schemas.api_models import GenerateRequest, GenerateResponse
from app.schemas.pipeline_schemas import JobStatus
from app.services import job_service
from app.utils.structured_log import get_bound_logger

log = get_bound_logger("appcompiler.routers.generate")

router = APIRouter(prefix="/api", tags=["generation"])


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate(
    request: GenerateRequest,
    _token: str = Depends(verify_token),
) -> GenerateResponse:
    """Start a new app generation job."""
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        active = await session.scalar(
            select(func.count())
            .select_from(GenerationJob)
            .where(GenerationJob.status.in_(["queued", "running"]))
        )
        if active and active >= settings.max_concurrent_jobs:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Too many active jobs ({active}). "
                    f"Max concurrent: {settings.max_concurrent_jobs}. Try again shortly."
                ),
            )

    job_id = str(uuid.uuid4())

    await job_service.create_job(
        job_id=job_id,
        prompt=request.prompt,
        options=request.options,
    )

    asyncio.create_task(
        run_pipeline(
            job_id=job_id,
            prompt=request.prompt,
            options=request.options,
        )
    )

    log.info("generation_enqueued", job_id=job_id, prompt_length=len(request.prompt))

    return GenerateResponse(job_id=job_id, status=JobStatus.QUEUED)
