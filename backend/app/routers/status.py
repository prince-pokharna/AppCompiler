"""Status router — GET /api/status/{job_id}, SSE stream, result, download."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import zipfile

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.redis_client import get_event_log, get_job_state
from app.schemas.api_models import ResultResponse, StatusResponse
from app.schemas.app_schema import CompletedAppSchema
from app.schemas.pipeline_schemas import CodeGenerationResult, JobStatus, ValidationReport

logger = logging.getLogger("appcompiler.routers.status")

router = APIRouter(prefix="/api", tags=["status"])


@router.get(
    "/status/{job_id}",
    response_model=StatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_status(job_id: str) -> StatusResponse:
    """Get the current status of a generation job."""
    state = await get_job_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return StatusResponse(
        job_id=job_id,
        status=JobStatus(state.get("status", "queued")),
        current_stage=state.get("current_stage"),
        progress_pct=state.get("progress_pct", 0.0),
        error=state.get("error"),
    )


@router.get("/status/{job_id}/stream")
async def stream_status(job_id: str) -> EventSourceResponse:
    """SSE stream of pipeline progress events."""
    state = await get_job_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    async def event_generator():
        last_index = 0
        max_wait = 300  # 5 minutes max

        for _ in range(max_wait * 2):  # Check every 0.5s
            events = await get_event_log(job_id)

            for i in range(last_index, len(events)):
                event = events[i]
                yield {
                    "event": event.get("event", "message"),
                    "data": json.dumps(event.get("data", {})),
                }
                last_index = i + 1

                # If we got a terminal event, stop
                if event.get("event") in ("done", "error"):
                    return

            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@router.get(
    "/result/{job_id}",
    response_model=ResultResponse,
    status_code=status.HTTP_200_OK,
)
async def get_result(job_id: str) -> ResultResponse:
    """Get the full result of a completed generation job."""
    state = await get_job_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if state.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not completed (status: {state.get('status')})",
        )

    result_data = state.get("result")
    if result_data is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job completed but no result data found",
        )

    schema = CompletedAppSchema(**result_data)
    code_result = None
    if state.get("code_result"):
        code_result = CodeGenerationResult(**state["code_result"])

    validation_report = None
    if state.get("validation_report"):
        validation_report = ValidationReport(**state["validation_report"])

    return ResultResponse(
        job_id=job_id,
        schema=schema,
        code_result=code_result,
        validation_report=validation_report,
    )


@router.get("/result/{job_id}/download")
async def download_result(job_id: str) -> StreamingResponse:
    """Download the generated Next.js project as a ZIP file."""
    state = await get_job_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if state.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not completed",
        )

    code_result = state.get("code_result")
    if not code_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No generated code available (codegen may have been skipped)",
        )

    generated_files = code_result.get("generated_files", [])
    if not generated_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were generated",
        )

    # Get app name for the ZIP
    result_data = state.get("result", {})
    app_name = result_data.get("meta", {}).get("app_name", "generated-app")

    # Create in-memory ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_entry in generated_files:
            file_path = file_entry.get("path", "")
            file_content = file_entry.get("content", "")
            if file_path:
                zf.writestr(f"{app_name}/{file_path}", file_content)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{app_name}.zip"',
        },
    )
