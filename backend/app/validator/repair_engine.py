"""Surgical repair engine — fixes specific errors without full regeneration."""

from __future__ import annotations

import logging
import time

from app.llm.client import LLMClient, LLMResponse
from app.llm.prompts.repair_prompt import (
    REPAIR_SYSTEM_PROMPT,
    get_repair_inconsistency_prompt,
    get_repair_missing_field_prompt,
    get_repair_orphan_ref_prompt,
)
from app.llm.response_parser import extract_json_lenient, JSONParseError
from app.schemas.pipeline_schemas import ErrorType, RepairAction, ValidationError

logger = logging.getLogger("appcompiler.validator.repair")


class RepairEngine:
    """Repairs validation errors surgically without full schema regeneration."""

    def __init__(self, llm_client: LLMClient, max_attempts: int = 2) -> None:
        self._llm = llm_client
        self._max_attempts = max_attempts

    async def repair_errors(
        self,
        errors: list[ValidationError],
        schemas: dict[str, dict],
    ) -> tuple[dict[str, dict], list[RepairAction], list[ValidationError]]:
        """Attempt to repair a list of validation errors.

        Args:
            errors: List of validation errors to repair.
            schemas: Dict mapping layer names to their current schema dicts.

        Returns:
            Tuple of (updated_schemas, repairs_made, unresolved_errors).
        """
        repairs_made: list[RepairAction] = []
        unresolved: list[ValidationError] = []

        for error in errors:
            repaired = False

            for attempt in range(self._max_attempts):
                start = time.perf_counter()

                try:
                    if error.error_type == ErrorType.TYPE_MISMATCH:
                        success = self._repair_type_mismatch(error, schemas)
                        method = "programmatic"
                    elif error.error_type == ErrorType.MISSING_FIELD:
                        success = await self._repair_missing_field(error, schemas)
                        method = "llm_repair"
                    elif error.error_type == ErrorType.ORPHAN_REF:
                        success = await self._repair_orphan_ref(error, schemas)
                        method = "llm_repair"
                    elif error.error_type == ErrorType.INCONSISTENCY:
                        success = await self._repair_inconsistency(error, schemas)
                        method = "refinement"
                    else:
                        success = False
                        method = "none"

                    duration_ms = int((time.perf_counter() - start) * 1000)

                    if success:
                        repairs_made.append(
                            RepairAction(
                                error_type=error.error_type,
                                layer=error.layer,
                                description=f"Fixed: {error.message}",
                                method=method,
                                success=True,
                                duration_ms=duration_ms,
                            )
                        )
                        repaired = True
                        logger.info(f"Repaired error in {error.layer}: {error.message}")
                        break

                except Exception as e:
                    logger.warning(
                        f"Repair attempt {attempt + 1} failed for {error.layer}: {e}"
                    )

            if not repaired:
                unresolved.append(error)
                logger.warning(f"Could not repair error in {error.layer}: {error.message}")

        return schemas, repairs_made, unresolved

    def _repair_type_mismatch(self, error: ValidationError, schemas: dict[str, dict]) -> bool:
        """Fix type mismatches programmatically without LLM."""
        layer_data = schemas.get(error.layer)
        if layer_data is None:
            return False

        path_parts = self._parse_path(error.path)
        if not path_parts:
            return False

        try:
            obj = layer_data
            for part in path_parts[:-1]:
                if isinstance(part, int):
                    obj = obj[part]
                else:
                    obj = obj[part]

            last_key = path_parts[-1]
            current_val = obj[last_key] if isinstance(last_key, str) else obj[last_key]

            if isinstance(current_val, str):
                if current_val.isdigit():
                    if isinstance(last_key, int):
                        obj[last_key] = int(current_val)
                    else:
                        obj[last_key] = int(current_val)
                    return True
                elif current_val.lower() in ("true", "false"):
                    if isinstance(last_key, int):
                        obj[last_key] = current_val.lower() == "true"
                    else:
                        obj[last_key] = current_val.lower() == "true"
                    return True
                try:
                    if isinstance(last_key, int):
                        obj[last_key] = float(current_val)
                    else:
                        obj[last_key] = float(current_val)
                    return True
                except ValueError:
                    pass
            elif isinstance(current_val, (int, float)) and "string" in error.message.lower():
                if isinstance(last_key, int):
                    obj[last_key] = str(current_val)
                else:
                    obj[last_key] = str(current_val)
                return True

        except (KeyError, IndexError, TypeError):
            pass

        return False

    async def _repair_missing_field(self, error: ValidationError, schemas: dict[str, dict]) -> bool:
        """Fix missing fields via targeted LLM call."""
        layer_data = schemas.get(error.layer)
        if layer_data is None:
            return False

        field_info = self._extract_field_info(error.message)
        field_name = field_info.get("name", "unknown")
        field_type = field_info.get("type", "string")

        prompt = get_repair_missing_field_prompt(
            layer=error.layer,
            field_name=field_name,
            field_type=field_type,
            context_json=layer_data,
        )

        try:
            response = await self._llm.complete(
                system=REPAIR_SYSTEM_PROMPT,
                user=prompt,
                temperature=0.0,
                max_tokens=4096,
            )
            repaired = extract_json_lenient(response.content)
            schemas[error.layer] = repaired
            return True
        except (JSONParseError, Exception) as e:
            logger.warning(f"LLM repair failed for missing field: {e}")
            return False

    async def _repair_orphan_ref(self, error: ValidationError, schemas: dict[str, dict]) -> bool:
        """Fix orphaned references between layers via LLM."""
        source_layer = error.layer
        target_layer = self._infer_target_layer(error)

        source_data = schemas.get(source_layer, {})
        target_data = schemas.get(target_layer, {})

        prompt = get_repair_orphan_ref_prompt(
            source_layer=source_layer,
            reference=error.path,
            target_layer=target_layer,
            source_json=source_data,
            target_json=target_data,
        )

        try:
            response = await self._llm.complete(
                system=REPAIR_SYSTEM_PROMPT,
                user=prompt,
                temperature=0.0,
                max_tokens=4096,
            )
            repaired = extract_json_lenient(response.content)

            if "source" in repaired:
                schemas[source_layer] = repaired["source"]
            if "target" in repaired:
                schemas[target_layer] = repaired["target"]
            return True
        except (JSONParseError, Exception) as e:
            logger.warning(f"LLM repair failed for orphan ref: {e}")
            return False

    async def _repair_inconsistency(self, error: ValidationError, schemas: dict[str, dict]) -> bool:
        """Fix cross-layer inconsistencies via LLM."""
        relevant_layers = self._get_relevant_layers(error, schemas)

        prompt = get_repair_inconsistency_prompt(
            conflict_description=error.message,
            layers_json=relevant_layers,
        )

        try:
            response = await self._llm.complete(
                system=REPAIR_SYSTEM_PROMPT,
                user=prompt,
                temperature=0.0,
                max_tokens=4096,
            )
            repaired = extract_json_lenient(response.content)

            for layer_name, layer_data in repaired.items():
                if layer_name in schemas and isinstance(layer_data, dict):
                    schemas[layer_name] = layer_data
            return True
        except (JSONParseError, Exception) as e:
            logger.warning(f"LLM repair failed for inconsistency: {e}")
            return False

    @staticmethod
    def _parse_path(path: str) -> list:
        """Parse a JSON path string into a list of keys/indices."""
        if not path or path == "$":
            return []
        parts: list = []
        for segment in path.replace("]", "").split("["):
            for sub in segment.split("."):
                if not sub:
                    continue
                try:
                    parts.append(int(sub))
                except ValueError:
                    parts.append(sub)
        return parts

    @staticmethod
    def _extract_field_info(message: str) -> dict[str, str]:
        """Extract field name and type from an error message."""
        name = "unknown"
        field_type = "string"
        if "'" in message:
            parts = message.split("'")
            if len(parts) >= 2:
                name = parts[1]
        if "type" in message.lower():
            for t in ("string", "integer", "boolean", "array", "object", "number"):
                if t in message.lower():
                    field_type = t
                    break
        return {"name": name, "type": field_type}

    @staticmethod
    def _infer_target_layer(error: ValidationError) -> str:
        """Infer which layer a reference points to based on the error."""
        msg = error.message.lower()
        if "database" in msg or "table" in msg or "column" in msg:
            return "database"
        elif "api" in msg or "endpoint" in msg:
            return "api"
        elif "auth" in msg or "role" in msg or "permission" in msg:
            return "auth"
        elif "ui" in msg or "page" in msg or "component" in msg:
            return "ui"
        layer_order = ["database", "api", "auth", "ui"]
        for layer in layer_order:
            if layer != error.layer:
                return layer
        return "database"

    @staticmethod
    def _get_relevant_layers(error: ValidationError, schemas: dict[str, dict]) -> dict[str, dict]:
        """Get the layers relevant to an inconsistency error."""
        msg = error.message.lower()
        relevant: dict[str, dict] = {}
        if error.layer in schemas:
            relevant[error.layer] = schemas[error.layer]
        for layer_name in ("ui", "api", "database", "auth"):
            if layer_name in msg and layer_name in schemas:
                relevant[layer_name] = schemas[layer_name]
        if len(relevant) < 2:
            for layer_name, data in schemas.items():
                if layer_name not in relevant:
                    relevant[layer_name] = data
                if len(relevant) >= 2:
                    break
        return relevant
