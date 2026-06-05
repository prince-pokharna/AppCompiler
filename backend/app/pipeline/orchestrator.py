"""Pipeline Orchestrator — runs all 6 stages and emits SSE events."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from app.config import get_settings
from app.llm.client import LLMClient
from app.pipeline.stage1_intent import extract_intent
from app.pipeline.stage2_design import design_architecture
from app.pipeline.stage3_schemas import generate_schemas
from app.pipeline.stage4_validation import validate_and_repair
from app.pipeline.stage5_refinement import refine_schemas
from app.pipeline.stage6_codegen import generate_code
from app.redis_client import append_event
from app.schemas.app_schema import CompletedAppSchema, GenerationMeta, MetaSchema, StageTimingInfo
from app.schemas.pipeline_schemas import (
    CodeGenerationResult,
    JobStatus,
    PipelineOptions,
    PipelineStage,
    StageStatus,
    ValidationReport,
)
from app.services import job_service
from app.utils.cost_tracker import CostTracker
from app.utils.structured_log import bind_context, get_bound_logger

log = get_bound_logger("appcompiler.pipeline.orchestrator")


async def _run_stage(coro, stage_name: str, timeout: int):
    """Run a pipeline stage with a per-stage timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise RuntimeError(
            f"Stage '{stage_name}' exceeded {timeout}s timeout"
        ) from exc


async def run_pipeline(
    job_id: str,
    prompt: str,
    options: PipelineOptions,
) -> None:
    """Run the full 6-stage pipeline for a generation job."""
    settings = get_settings()
    bind_context(job_id=job_id, prompt_preview=prompt[:50])
    log.info("pipeline_started", mode="fast" if options.fast_mode else "quality")

    llm_client = LLMClient()
    cost_tracker = CostTracker()
    pipeline_start = time.perf_counter()
    stage_timings: list[StageTimingInfo] = []
    current_result: CompletedAppSchema | None = None
    code_result: CodeGenerationResult | None = None
    validation_report: ValidationReport | None = None
    total_retries = 0
    stage_timeout = settings.pipeline_stage_timeout_seconds

    async def _execute() -> None:
        nonlocal current_result, code_result, validation_report, total_retries

        await job_service.update_job_progress(
            job_id, JobStatus.RUNNING, PipelineStage.INTENT.value, 0,
        )

        # ── Stage 1: Intent Extraction ──
        stage_start = time.perf_counter()
        await _emit(job_id, "stage_start", {"stage": "intent", "message": "Extracting intent..."})

        intent, intent_retries = await _run_stage(
            extract_intent(
                user_input=prompt,
                llm_client=llm_client,
                cost_tracker=cost_tracker,
                fast_mode=options.fast_mode,
            ),
            "intent",
            stage_timeout,
        )
        total_retries += intent_retries

        intent_ms = int((time.perf_counter() - stage_start) * 1000)
        stage_timings.append(_timing("intent", intent_ms, cost_tracker, intent_retries))
        log.info("stage_completed", stage="intent", duration_ms=intent_ms)
        await _emit(job_id, "stage_complete", {
            "stage": "intent", "duration_ms": intent_ms,
            "app_name": intent.app_name, "app_type": intent.app_type,
        })
        await job_service.update_job_progress(
            job_id, JobStatus.RUNNING, PipelineStage.DESIGN.value, 16,
        )

        # ── Stage 2: System Design ──
        stage_start = time.perf_counter()
        await _emit(job_id, "stage_start", {"stage": "design", "message": "Designing architecture..."})

        architecture, design_retries = await _run_stage(
            design_architecture(
                intent=intent,
                llm_client=llm_client,
                cost_tracker=cost_tracker,
                fast_mode=options.fast_mode,
            ),
            "design",
            stage_timeout,
        )
        total_retries += design_retries

        design_ms = int((time.perf_counter() - stage_start) * 1000)
        stage_timings.append(_timing("design", design_ms, cost_tracker, design_retries))
        log.info("stage_completed", stage="design", duration_ms=design_ms)
        await _emit(job_id, "stage_complete", {
            "stage": "design", "duration_ms": design_ms,
            "entities": len(architecture.entities), "pages": len(architecture.pages),
        })
        await job_service.update_job_progress(
            job_id, JobStatus.RUNNING, PipelineStage.SCHEMAS.value, 33,
        )

        # ── Stage 3: Parallel Schema Generation ──
        stage_start = time.perf_counter()
        await _emit(job_id, "stage_start", {"stage": "schemas", "message": "Generating schemas in parallel..."})

        ui, api, database, auth, schema_retries = await _run_stage(
            generate_schemas(
                intent=intent,
                architecture=architecture,
                llm_client=llm_client,
                cost_tracker=cost_tracker,
                fast_mode=options.fast_mode,
            ),
            "schemas",
            stage_timeout * 2,
        )
        total_schema_retries = sum(schema_retries.values())
        total_retries += total_schema_retries

        schemas_ms = int((time.perf_counter() - stage_start) * 1000)
        stage_timings.append(_timing("schemas", schemas_ms, cost_tracker, total_schema_retries))
        log.info("stage_completed", stage="schemas", duration_ms=schemas_ms)
        await _emit(job_id, "stage_complete", {
            "stage": "schemas", "duration_ms": schemas_ms,
            "ui_pages": len(ui.pages), "api_endpoints": len(api.endpoints),
            "db_tables": len(database.tables), "auth_roles": len(auth.roles),
        })
        await job_service.update_job_progress(
            job_id, JobStatus.RUNNING, PipelineStage.VALIDATION.value, 50,
        )

        # ── Stage 4: Validation + Repair ──
        stage_start = time.perf_counter()
        await _emit(job_id, "stage_start", {"stage": "validation", "message": "Validating and repairing..."})

        ui, api, database, auth, validation_report = await _run_stage(
            validate_and_repair(
                ui=ui, api=api, database=database, auth=auth,
                architecture=architecture,
                llm_client=llm_client,
                cost_tracker=cost_tracker,
            ),
            "validation",
            stage_timeout * 2,
        )

        validation_ms = int((time.perf_counter() - stage_start) * 1000)
        stage_timings.append(_timing("validation", validation_ms, cost_tracker, 0))

        for repair in validation_report.repairs_made:
            await _emit(job_id, "repair", {
                "layer": repair.layer, "description": repair.description,
                "method": repair.method,
            })

        await _emit(job_id, "stage_complete", {
            "stage": "validation", "duration_ms": validation_ms,
            "errors_found": validation_report.total_errors,
            "errors_repaired": validation_report.total_repaired,
            "errors_unresolved": validation_report.total_unresolved,
        })
        await job_service.update_job_progress(
            job_id, JobStatus.RUNNING, PipelineStage.REFINEMENT.value, 66,
        )

        # ── Stage 5: Refinement ──
        stage_start = time.perf_counter()
        skip_refinement = options.fast_mode and not validation_report.unresolved_issues

        if skip_refinement:
            await _emit(job_id, "stage_complete", {
                "stage": "refinement", "duration_ms": 0, "skipped": True,
            })
            stage_timings.append(StageTimingInfo(stage_name="refinement", duration_ms=0))
        else:
            await _emit(job_id, "stage_start", {"stage": "refinement", "message": "Refining schemas..."})

            ui, api, database, auth, was_skipped = await _run_stage(
                refine_schemas(
                    ui=ui, api=api, database=database, auth=auth,
                    validation_report=validation_report,
                    llm_client=llm_client,
                    cost_tracker=cost_tracker,
                ),
                "refinement",
                stage_timeout,
            )

            refinement_ms = int((time.perf_counter() - stage_start) * 1000)
            stage_timings.append(_timing("refinement", refinement_ms, cost_tracker, 0))
            await _emit(job_id, "stage_complete", {
                "stage": "refinement", "duration_ms": refinement_ms, "skipped": was_skipped,
            })

        await job_service.update_job_progress(
            job_id, JobStatus.RUNNING, PipelineStage.CODEGEN.value, 83,
        )

        # ── Stage 6: Code Generation ──
        if not options.skip_codegen:
            stage_start = time.perf_counter()
            await _emit(job_id, "stage_start", {"stage": "codegen", "message": "Generating code..."})

            total_ms = int((time.perf_counter() - pipeline_start) * 1000)
            gen_meta = GenerationMeta(
                total_duration_ms=total_ms,
                total_cost_usd=cost_tracker.total_cost(),
                stages=stage_timings,
                fast_mode=options.fast_mode,
                errors_found=validation_report.total_errors,
                errors_repaired=validation_report.total_repaired,
                errors_unresolved=validation_report.total_unresolved,
            )

            current_result = CompletedAppSchema(
                meta=MetaSchema(
                    app_name=intent.app_name,
                    description=intent.description,
                    generated_at=datetime.now(timezone.utc).isoformat(),
                ),
                intent=intent,
                architecture=architecture,
                ui=ui, api=api, database=database, auth=auth,
                generation_meta=gen_meta,
            )

            code_result = await _run_stage(
                generate_code(
                    schema=current_result,
                    cost_tracker=cost_tracker,
                    skip_validation=options.fast_mode,
                ),
                "codegen",
                stage_timeout,
            )

            codegen_ms = int((time.perf_counter() - stage_start) * 1000)
            stage_timings.append(_timing("codegen", codegen_ms, cost_tracker, 0))
            await _emit(job_id, "stage_complete", {
                "stage": "codegen", "duration_ms": codegen_ms,
                "files_generated": code_result.total_files,
                "compilation_success": code_result.execution_report.compilation_success,
            })
        else:
            stage_timings.append(StageTimingInfo(stage_name="codegen", duration_ms=0))
            await _emit(job_id, "stage_complete", {"stage": "codegen", "skipped": True})

        total_duration_ms = int((time.perf_counter() - pipeline_start) * 1000)

        gen_meta = GenerationMeta(
            total_duration_ms=total_duration_ms,
            total_cost_usd=cost_tracker.total_cost(),
            stages=stage_timings,
            fast_mode=options.fast_mode,
            errors_found=validation_report.total_errors,
            errors_repaired=validation_report.total_repaired,
            errors_unresolved=validation_report.total_unresolved,
        )

        current_result = CompletedAppSchema(
            meta=MetaSchema(
                app_name=intent.app_name,
                description=intent.description,
                generated_at=datetime.now(timezone.utc).isoformat(),
            ),
            intent=intent,
            architecture=architecture,
            ui=ui, api=api, database=database, auth=auth,
            generation_meta=gen_meta,
        )

        await job_service.complete_job(
            job_id,
            result=current_result.model_dump(),
            code_result=code_result.model_dump() if code_result else None,
            validation_report=validation_report.model_dump() if validation_report else None,
            total_duration_ms=total_duration_ms,
            total_input_tokens=cost_tracker.total_input_tokens(),
            total_output_tokens=cost_tracker.total_output_tokens(),
            total_cost_usd=cost_tracker.total_cost(),
            retry_count=total_retries,
            errors_found=validation_report.total_errors,
            errors_repaired=validation_report.total_repaired,
        )

        await _emit(job_id, "done", {
            "total_duration_ms": total_duration_ms,
            "total_cost_usd": cost_tracker.total_cost(),
            "total_input_tokens": cost_tracker.total_input_tokens(),
            "total_output_tokens": cost_tracker.total_output_tokens(),
            "app_name": intent.app_name,
        })

        log.info(
            "pipeline_completed",
            app_name=intent.app_name,
            duration_ms=total_duration_ms,
            cost_usd=cost_tracker.total_cost(),
        )

    try:
        await asyncio.wait_for(
            _execute(),
            timeout=settings.pipeline_timeout_seconds,
        )
    except asyncio.TimeoutError:
        msg = f"Pipeline exceeded global timeout ({settings.pipeline_timeout_seconds}s)"
        log.error("pipeline_timeout", message=msg)
        await job_service.fail_job(job_id, msg)
        await _emit(job_id, "error", {"message": msg})
    except Exception as e:
        log.exception("pipeline_failed", error=str(e))
        await job_service.fail_job(job_id, str(e))
        await _emit(job_id, "error", {"message": str(e)})
    finally:
        await llm_client.close()


def _timing(stage: str, duration_ms: int, tracker: CostTracker, retries: int) -> StageTimingInfo:
    """Build a StageTimingInfo from tracker data."""
    usage = tracker.get_stage_usage(stage)
    return StageTimingInfo(
        stage_name=stage,
        duration_ms=duration_ms,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        model_used=usage.get("model", ""),
        retries=retries,
        cost_usd=usage.get("cost_usd", 0.0),
    )


async def _emit(job_id: str, event: str, data: dict) -> None:
    """Emit an SSE event via Redis event log."""
    await append_event(job_id, {"event": event, "data": data})
