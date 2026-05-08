"""Stage 5: Cross-layer Refinement — resolves remaining conflicts after validation."""

from __future__ import annotations

import logging

from app.llm.client import LLMClient
from app.llm.prompts.refinement_prompt import REFINEMENT_SYSTEM_PROMPT, get_refinement_user_prompt
from app.llm.response_parser import JSONParseError, extract_json_lenient
from app.schemas.app_schema import APISchema, AuthSchema, DatabaseSchema, UISchema
from app.schemas.pipeline_schemas import ValidationReport
from app.utils.cost_tracker import CostTracker

logger = logging.getLogger("appcompiler.pipeline.stage5")


async def refine_schemas(
    ui: UISchema,
    api: APISchema,
    database: DatabaseSchema,
    auth: AuthSchema,
    validation_report: ValidationReport,
    llm_client: LLMClient,
    cost_tracker: CostTracker,
) -> tuple[UISchema, APISchema, DatabaseSchema, AuthSchema, bool]:
    """Refine schemas to resolve remaining cross-layer inconsistencies.

    Fast path: if no unresolved issues, skip entirely.

    Returns:
        Tuple of (refined schemas..., was_skipped).
    """
    if not validation_report.unresolved_issues:
        logger.info("Refinement skipped — no unresolved issues")
        return ui, api, database, auth, True

    logger.info(
        f"Refinement starting — {len(validation_report.unresolved_issues)} unresolved issues"
    )

    full_schema = {
        "ui": ui.model_dump(),
        "api": api.model_dump(),
        "database": database.model_dump(),
        "auth": auth.model_dump(),
    }

    unresolved_dicts = [
        {"layer": issue.layer, "path": issue.path, "message": issue.message}
        for issue in validation_report.unresolved_issues
    ]

    user_prompt = get_refinement_user_prompt(full_schema, unresolved_dicts)

    try:
        response = await llm_client.complete(
            system=REFINEMENT_SYSTEM_PROMPT,
            user=user_prompt,
            temperature=0.1,
            max_tokens=4096,
        )

        cost_tracker.record(
            stage="refinement",
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
        )

        parsed = extract_json_lenient(response.content)
        fixes = parsed.get("fixes", [])

        if not fixes:
            logger.info("Refinement returned no fixes")
            return ui, api, database, auth, False

        # Apply fixes
        for fix in fixes:
            layer = fix.get("layer", "")
            data = fix.get("data")
            if not data or layer not in full_schema:
                continue

            action = fix.get("action", "modify")
            path = fix.get("path", "")

            if action == "modify" and isinstance(data, dict):
                _deep_merge(full_schema[layer], data)
            elif action == "add" and isinstance(data, (dict, list)):
                _apply_add(full_schema[layer], path, data)

            logger.debug(f"Applied fix to {layer}: {fix.get('description', '')}")

        # Rebuild Pydantic models
        try:
            ui = UISchema(**full_schema["ui"])
        except Exception as e:
            logger.warning(f"Failed to rebuild UI after refinement: {e}")

        try:
            api = APISchema(**full_schema["api"])
        except Exception as e:
            logger.warning(f"Failed to rebuild API after refinement: {e}")

        try:
            database = DatabaseSchema(**full_schema["database"])
        except Exception as e:
            logger.warning(f"Failed to rebuild DB after refinement: {e}")

        try:
            auth = AuthSchema(**full_schema["auth"])
        except Exception as e:
            logger.warning(f"Failed to rebuild Auth after refinement: {e}")

        logger.info(f"Refinement applied {len(fixes)} fix(es)")
        return ui, api, database, auth, False

    except (JSONParseError, Exception) as e:
        logger.error(f"Refinement failed: {e}")
        return ui, api, database, auth, False


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _apply_add(schema: dict, path: str, data: dict | list) -> None:
    """Apply an 'add' fix at a specific path in the schema."""
    if not path:
        if isinstance(data, dict):
            _deep_merge(schema, data)
        return

    parts = path.replace("]", "").split("[")
    obj = schema
    for part in parts[:-1]:
        for sub in part.split("."):
            if not sub:
                continue
            try:
                idx = int(sub)
                obj = obj[idx]
            except (ValueError, TypeError):
                if sub not in obj:
                    obj[sub] = {}
                obj = obj[sub]

    last = parts[-1].split(".")[-1] if parts[-1] else ""
    if last and isinstance(obj, dict):
        if isinstance(data, list) and last in obj and isinstance(obj[last], list):
            obj[last].extend(data)
        else:
            obj[last] = data
