"""Evaluation router — POST /api/evaluate, GET /api/evaluate/{eval_id}/results."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, status

from app.evaluation.runner import run_evaluation
from app.redis_client import get_job_state
from app.schemas.api_models import (
    EvaluateRequest,
    EvaluateResponse,
    EvaluationResultsResponse,
    EvaluationSummary,
    PromptResult,
)

logger = logging.getLogger("appcompiler.routers.evaluate")

router = APIRouter(prefix="/api", tags=["evaluation"])


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_evaluation(request: EvaluateRequest) -> EvaluateResponse:
    """Start a batch evaluation run."""
    eval_id = str(uuid.uuid4())

    from app.evaluation.dataset import get_prompts_by_ids
    prompts = get_prompts_by_ids(request.prompt_ids)
    total = len(prompts)

    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No matching prompts found for the given IDs",
        )

    # Launch evaluation as background task
    asyncio.create_task(
        run_evaluation(eval_id=eval_id, prompt_ids=request.prompt_ids)
    )

    logger.info(
        f"Evaluation started: {eval_id} ({total} prompts)",
        extra={"eval_id": eval_id, "total_prompts": total},
    )

    return EvaluateResponse(eval_id=eval_id, status="started", total_prompts=total)


@router.get(
    "/evaluate/{eval_id}/results",
    response_model=EvaluationResultsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_evaluation_results(eval_id: str) -> EvaluationResultsResponse:
    """Get results of an evaluation run."""
    state = await get_job_state(f"eval:{eval_id}")
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation {eval_id} not found",
        )

    results = [
        PromptResult(**r) for r in state.get("results", [])
    ]

    summary = None
    if state.get("summary"):
        summary = EvaluationSummary(**state["summary"])

    return EvaluationResultsResponse(
        eval_id=eval_id,
        status=state.get("status", "unknown"),
        results=results,
        summary=summary,
    )
