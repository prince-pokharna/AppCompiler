"""Stage 4: Validation + Repair — validates all schemas and repairs errors."""

from __future__ import annotations

import logging
import time

from app.llm.client import LLMClient
from app.schemas.app_schema import (
    APISchema, ArchitectureSchema, AuthSchema, DatabaseSchema, UISchema,
)
from app.schemas.pipeline_schemas import ValidationReport
from app.utils.cost_tracker import CostTracker
from app.validator.cross_layer_validator import run_all_checks
from app.validator.json_validator import validate_all_layers
from app.validator.repair_engine import RepairEngine

logger = logging.getLogger("appcompiler.pipeline.stage4")


async def validate_and_repair(
    ui: UISchema,
    api: APISchema,
    database: DatabaseSchema,
    auth: AuthSchema,
    architecture: ArchitectureSchema,
    llm_client: LLMClient,
    cost_tracker: CostTracker,
) -> tuple[UISchema, APISchema, DatabaseSchema, AuthSchema, ValidationReport]:
    """Validate all schema layers and repair any errors found.

    Args:
        ui: UI schema from Stage 3.
        api: API schema from Stage 3.
        database: Database schema from Stage 3.
        auth: Auth schema from Stage 3.
        architecture: Architecture from Stage 2 (for cross-ref checks).
        llm_client: LLM client for repair calls.
        cost_tracker: Cost tracker.

    Returns:
        Tuple of (repaired schemas..., ValidationReport).
    """
    validation_start = time.perf_counter()

    # Convert to dicts for validation
    schemas: dict[str, dict] = {
        "ui": ui.model_dump(),
        "api": api.model_dump(),
        "database": database.model_dump(),
        "auth": auth.model_dump(),
    }
    arch_dict = architecture.model_dump()

    # Phase 1: JSON Schema validation
    json_errors = validate_all_layers(
        ui=schemas["ui"],
        api=schemas["api"],
        database=schemas["database"],
        auth=schemas["auth"],
    )

    # Phase 2: Cross-layer consistency checks
    cross_errors = run_all_checks(
        ui=schemas["ui"],
        api=schemas["api"],
        database=schemas["database"],
        auth=schemas["auth"],
        architecture=arch_dict,
    )

    all_errors = json_errors + cross_errors
    validation_time_ms = int((time.perf_counter() - validation_start) * 1000)

    logger.info(
        f"Validation found {len(all_errors)} error(s) "
        f"({len(json_errors)} schema, {len(cross_errors)} cross-layer)",
        extra={
            "json_errors": len(json_errors),
            "cross_errors": len(cross_errors),
            "validation_time_ms": validation_time_ms,
        },
    )

    # Phase 3: Repair
    repair_start = time.perf_counter()
    repairs_made = []
    unresolved = []

    if all_errors:
        repairable_errors = [e for e in all_errors if e.auto_repairable]
        non_repairable = [e for e in all_errors if not e.auto_repairable]

        if repairable_errors:
            repair_engine = RepairEngine(llm_client=llm_client, max_attempts=2)
            schemas, repairs_made, repair_unresolved = await repair_engine.repair_errors(
                errors=repairable_errors,
                schemas=schemas,
            )
            unresolved = repair_unresolved + non_repairable
        else:
            unresolved = non_repairable
    
    repair_time_ms = int((time.perf_counter() - repair_start) * 1000)

    # Rebuild Pydantic models from (potentially repaired) dicts
    try:
        ui = UISchema(**schemas["ui"])
    except Exception as e:
        logger.warning(f"Failed to rebuild UI schema after repair: {e}")

    try:
        api = APISchema(**schemas["api"])
    except Exception as e:
        logger.warning(f"Failed to rebuild API schema after repair: {e}")

    try:
        database = DatabaseSchema(**schemas["database"])
    except Exception as e:
        logger.warning(f"Failed to rebuild DB schema after repair: {e}")

    try:
        auth = AuthSchema(**schemas["auth"])
    except Exception as e:
        logger.warning(f"Failed to rebuild Auth schema after repair: {e}")

    report = ValidationReport(
        errors_found=all_errors,
        repairs_made=repairs_made,
        unresolved_issues=unresolved,
        total_errors=len(all_errors),
        total_repaired=len(repairs_made),
        total_unresolved=len(unresolved),
        validation_time_ms=validation_time_ms,
        repair_time_ms=repair_time_ms,
    )

    logger.info(
        f"Validation complete: {report.total_errors} errors, "
        f"{report.total_repaired} repaired, {report.total_unresolved} unresolved",
    )

    return ui, api, database, auth, report
