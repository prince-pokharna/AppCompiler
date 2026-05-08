"""Batch evaluation runner — runs the pipeline against test prompts."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.evaluation.dataset import TestPrompt, get_prompts_by_ids
from app.evaluation.evaluator import RunMetrics
from app.pipeline.orchestrator import run_pipeline
from app.redis_client import get_job_state, set_job_state
from app.schemas.pipeline_schemas import PipelineOptions

logger = logging.getLogger("appcompiler.evaluation.runner")


async def run_evaluation(
    eval_id: str,
    prompt_ids: list[str] | None = None,
) -> None:
    """Run the evaluation suite against selected or all test prompts.

    Args:
        eval_id: Unique evaluation run ID.
        prompt_ids: Optional list of prompt IDs. Empty/None = run all 20.
    """
    prompts = get_prompts_by_ids(prompt_ids or [])
    total = len(prompts)

    logger.info(f"Starting evaluation {eval_id} with {total} prompt(s)")

    await set_job_state(f"eval:{eval_id}", {
        "status": "running",
        "total_prompts": total,
        "completed_prompts": 0,
        "results": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    results: list[dict] = []
    success_count = 0
    total_cost = 0.0

    for i, prompt in enumerate(prompts):
        logger.info(f"Evaluating prompt {i + 1}/{total}: {prompt.id} — {prompt.description}")

        metrics = RunMetrics(prompt_id=prompt.id, prompt_text=prompt.text)
        metrics.start()

        job_id = f"eval-{eval_id}-{prompt.id}-{uuid.uuid4().hex[:8]}"

        try:
            await run_pipeline(
                job_id=job_id,
                prompt=prompt.text,
                options=PipelineOptions(skip_codegen=False, fast_mode=False),
            )

            # Get job result
            job_state = await get_job_state(job_id)
            if job_state and job_state.get("status") == "completed":
                metrics.finish(success=True)
                success_count += 1

                result_data = job_state.get("result", {})
                gen_meta = result_data.get("generation_meta", {})
                metrics.estimated_cost_usd = gen_meta.get("total_cost_usd", 0.0)
                total_cost += metrics.estimated_cost_usd

                # Extract stage timings
                for stage in gen_meta.get("stages", []):
                    metrics.stage_times[stage.get("stage_name", "")] = stage.get("duration_ms", 0)

                # Extract validation info
                val_report = job_state.get("validation_report", {})
                if val_report:
                    metrics.record_validation(
                        errors_found=val_report.get("total_errors", 0),
                        errors_resolved=val_report.get("total_repaired", 0),
                        repair_counts=val_report.get("total_repaired", 0),
                    )

                # Extract assumptions
                intent = result_data.get("intent", {})
                metrics.assumptions_made = intent.get("assumptions", [])
            else:
                error_msg = (job_state or {}).get("error", "Unknown error")
                metrics.finish(success=False, failure_type="pipeline_error")
                metrics.error_message = error_msg

        except Exception as e:
            logger.error(f"Evaluation failed for {prompt.id}: {e}")
            metrics.finish(success=False, failure_type="exception")
            metrics.error_message = str(e)

        results.append(metrics.to_dict())

        # Update eval state
        await set_job_state(f"eval:{eval_id}", {
            "status": "running",
            "total_prompts": total,
            "completed_prompts": i + 1,
            "results": results,
        })

    # Compute summary
    completed = len(results)
    failure_count = completed - success_count
    avg_latency = sum(r.get("total_latency_ms", 0) for r in results) / max(completed, 1)
    total_retries = sum(
        sum(r.get("retry_counts", {}).values()) for r in results
    )
    avg_retries = total_retries / max(completed, 1)
    avg_repairs = sum(r.get("repair_counts", 0) for r in results) / max(completed, 1)

    failure_types: dict[str, int] = {}
    for r in results:
        ft = r.get("failure_type")
        if ft:
            failure_types[ft] = failure_types.get(ft, 0) + 1

    summary = {
        "total_prompts": total,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate_pct": round((success_count / max(total, 1)) * 100, 1),
        "avg_latency_ms": round(avg_latency),
        "avg_retries": round(avg_retries, 2),
        "avg_repairs": round(avg_repairs, 2),
        "total_cost_usd": round(total_cost, 4),
        "failure_types": failure_types,
    }

    await set_job_state(f"eval:{eval_id}", {
        "status": "completed",
        "total_prompts": total,
        "completed_prompts": completed,
        "results": results,
        "summary": summary,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(
        f"Evaluation {eval_id} complete: {success_count}/{total} passed, "
        f"cost=${total_cost:.4f}",
    )
