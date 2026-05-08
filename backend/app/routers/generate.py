"""Generation router — POST /api/generate."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, status

from app.pipeline.orchestrator import run_pipeline
from app.redis_client import set_job_state
from app.schemas.api_models import GenerateRequest, GenerateResponse
from app.schemas.pipeline_schemas import JobStatus

logger = logging.getLogger("appcompiler.routers.generate")

router = APIRouter(prefix="/api", tags=["generation"])


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate(request: GenerateRequest) -> GenerateResponse:
    """Start a new app generation job.

    Creates an async background task that runs the full 6-stage pipeline.
    Returns immediately with a job_id for status polling or SSE streaming.
    """
    job_id = str(uuid.uuid4())

    # Initialize job state in Redis
    await set_job_state(job_id, {
        "status": JobStatus.QUEUED.value,
        "prompt": request.prompt,
        "options": request.options.model_dump(),
        "current_stage": None,
        "progress_pct": 0.0,
    })

    # Launch pipeline as background task
    asyncio.create_task(
        run_pipeline(
            job_id=job_id,
            prompt=request.prompt,
            options=request.options,
        )
    )

    logger.info(
        f"Generation job created: {job_id}",
        extra={"job_id": job_id, "prompt_length": len(request.prompt)},
    )

    return GenerateResponse(job_id=job_id, status=JobStatus.QUEUED)
