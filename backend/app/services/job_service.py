"""Job persistence — PostgreSQL as source of truth, Redis for cache and SSE."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.generation import GenerationJob
from app.redis_client import get_job_state, set_job_state
from app.schemas.pipeline_schemas import JobStatus, PipelineOptions

logger = logging.getLogger("appcompiler.services.job")


def _status_value(status: JobStatus | str) -> str:
    return status.value if isinstance(status, JobStatus) else status


async def create_job(
    job_id: str,
    prompt: str,
    options: PipelineOptions,
) -> None:
    """Create job in Postgres and initialize Redis cache."""
    async with AsyncSessionLocal() as session:
        job = GenerationJob(
            id=job_id,
            prompt=prompt,
            status=JobStatus.QUEUED.value,
            fast_mode=options.fast_mode,
            skip_codegen=options.skip_codegen,
        )
        session.add(job)
        await session.commit()

    await set_job_state(job_id, {
        "status": JobStatus.QUEUED.value,
        "prompt": prompt,
        "options": options.model_dump(),
        "current_stage": None,
        "progress_pct": 0.0,
    })
    logger.info("job_created", extra={"job_id": job_id})


async def update_job_progress(
    job_id: str,
    status: JobStatus | str,
    current_stage: str | None = None,
    progress_pct: float | None = None,
    *,
    merge_redis: bool = True,
) -> None:
    """Update job status in Postgres and merge into Redis (preserves prompt/result)."""
    status_str = _status_value(status)

    async with AsyncSessionLocal() as session:
        job = await session.get(GenerationJob, job_id)
        if job:
            job.status = status_str
            if current_stage is not None:
                job.current_stage = current_stage
            if progress_pct is not None:
                job.progress_pct = progress_pct
            if status_str == JobStatus.RUNNING.value and job.started_at is None:
                job.started_at = datetime.now(timezone.utc)
            await session.commit()

    if merge_redis:
        existing = await get_job_state(job_id) or {}
        existing.update({
            "status": status_str,
            "current_stage": current_stage if current_stage is not None else existing.get("current_stage"),
            "progress_pct": progress_pct if progress_pct is not None else existing.get("progress_pct", 0.0),
        })
        await set_job_state(job_id, existing)
    else:
        patch: dict[str, Any] = {"status": status_str}
        if current_stage is not None:
            patch["current_stage"] = current_stage
        if progress_pct is not None:
            patch["progress_pct"] = progress_pct
        existing = await get_job_state(job_id) or {}
        existing.update(patch)
        await set_job_state(job_id, existing)


async def complete_job(
    job_id: str,
    *,
    result: dict | None = None,
    code_result: dict | None = None,
    validation_report: dict | None = None,
    total_duration_ms: int = 0,
    total_input_tokens: int = 0,
    total_output_tokens: int = 0,
    total_cost_usd: float = 0.0,
    retry_count: int = 0,
    errors_found: int = 0,
    errors_repaired: int = 0,
) -> None:
    """Mark job completed and persist results to Postgres."""
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        job = await session.get(GenerationJob, job_id)
        if job:
            job.status = JobStatus.COMPLETED.value
            job.current_stage = None
            job.progress_pct = 100.0
            job.result_schema = result
            job.code_result = code_result
            job.validation_report = validation_report
            job.total_duration_ms = total_duration_ms
            job.total_input_tokens = total_input_tokens
            job.total_output_tokens = total_output_tokens
            job.total_cost_usd = total_cost_usd
            job.retry_count = retry_count
            job.errors_found = errors_found
            job.errors_repaired = errors_repaired
            job.completed_at = now
            await session.commit()

    redis_state: dict[str, Any] = {
        "status": JobStatus.COMPLETED.value,
        "current_stage": None,
        "progress_pct": 100.0,
        "result": result,
        "code_result": code_result,
        "validation_report": validation_report,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost_usd": total_cost_usd,
        "total_duration_ms": total_duration_ms,
    }
    existing = await get_job_state(job_id) or {}
    existing.update(redis_state)
    await set_job_state(job_id, existing, ttl=86400)


async def fail_job(job_id: str, error: str) -> None:
    """Mark job failed in Postgres and Redis."""
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        job = await session.get(GenerationJob, job_id)
        if job:
            job.status = JobStatus.FAILED.value
            job.error_message = error
            job.completed_at = now
            await session.commit()

    existing = await get_job_state(job_id) or {}
    existing.update({
        "status": JobStatus.FAILED.value,
        "error": error,
        "progress_pct": existing.get("progress_pct", 0.0),
    })
    await set_job_state(job_id, existing, ttl=86400)


async def get_job_from_db(job_id: str) -> GenerationJob | None:
    """Load job row from PostgreSQL."""
    async with AsyncSessionLocal() as session:
        return await session.get(GenerationJob, job_id)


async def get_job_state_merged(job_id: str) -> dict[str, Any] | None:
    """Get job state — Redis first, fall back to Postgres for completed/failed jobs."""
    state = await get_job_state(job_id)
    if state is not None:
        return state

    job = await get_job_from_db(job_id)
    if job is None:
        return None

    return {
        "status": job.status,
        "prompt": job.prompt,
        "current_stage": job.current_stage,
        "progress_pct": job.progress_pct,
        "error": job.error_message,
        "result": job.result_schema,
        "code_result": job.code_result,
        "validation_report": job.validation_report,
        "total_input_tokens": job.total_input_tokens,
        "total_output_tokens": job.total_output_tokens,
        "estimated_cost_usd": job.total_cost_usd,
        "total_duration_ms": job.total_duration_ms,
        "options": {
            "fast_mode": job.fast_mode,
            "skip_codegen": job.skip_codegen,
        },
    }


async def job_exists(job_id: str) -> bool:
    """Check if job exists in Redis or Postgres."""
    if await get_job_state(job_id) is not None:
        return True
    job = await get_job_from_db(job_id)
    return job is not None
