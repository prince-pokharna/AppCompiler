"""JSON linting and JSON Schema validation for each pipeline layer."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import jsonschema
from jsonschema import Draft7Validator, ValidationError as JsonSchemaValidationError

from app.schemas.pipeline_schemas import ErrorType, ValidationError

logger = logging.getLogger("appcompiler.validator.json")

# Directory containing the JSON Schema files
SCHEMAS_DIR = Path(__file__).parent / "schemas"

# Cache for loaded schemas
_schema_cache: dict[str, dict] = {}


def _load_schema(schema_name: str) -> dict:
    """Load and cache a JSON Schema file."""
    if schema_name not in _schema_cache:
        schema_path = SCHEMAS_DIR / f"{schema_name}_schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        with open(schema_path, "r", encoding="utf-8") as f:
            _schema_cache[schema_name] = json.load(f)
    return _schema_cache[schema_name]


def validate_json_structure(data: dict, layer: str) -> list[ValidationError]:
    """Validate a data dict against its JSON Schema.

    Args:
        data: The parsed JSON data to validate.
        layer: The schema layer name (intent, ui, api, db, auth).

    Returns:
        List of ValidationError objects for any issues found.
    """
    # Map layer names to schema file names
    schema_map = {
        "intent": "intent",
        "ui": "ui",
        "api": "api",
        "database": "db",
        "db": "db",
        "auth": "auth",
    }

    schema_key = schema_map.get(layer)
    if schema_key is None:
        logger.warning(f"No JSON Schema defined for layer: {layer}")
        return []

    try:
        schema = _load_schema(schema_key)
    except FileNotFoundError:
        logger.warning(f"Schema file not found for layer: {layer}")
        return []

    errors: list[ValidationError] = []
    validator = Draft7Validator(schema)

    for error in validator.iter_errors(data):
        error_type = _classify_schema_error(error)
        json_path = _format_path(error.absolute_path)

        errors.append(
            ValidationError(
                error_type=error_type,
                layer=layer,
                path=json_path,
                message=error.message,
                severity="error",
                auto_repairable=error_type in (ErrorType.MISSING_FIELD, ErrorType.TYPE_MISMATCH),
            )
        )

    if errors:
        logger.info(
            f"JSON validation found {len(errors)} error(s) in {layer}",
            extra={"layer": layer, "error_count": len(errors)},
        )
    else:
        logger.debug(f"JSON validation passed for {layer}")

    return errors


def validate_all_layers(
    intent: dict | None = None,
    ui: dict | None = None,
    api: dict | None = None,
    database: dict | None = None,
    auth: dict | None = None,
) -> list[ValidationError]:
    """Validate multiple layers at once."""
    all_errors: list[ValidationError] = []

    layers = {
        "intent": intent,
        "ui": ui,
        "api": api,
        "database": database,
        "auth": auth,
    }

    for layer_name, data in layers.items():
        if data is not None:
            layer_errors = validate_json_structure(data, layer_name)
            all_errors.extend(layer_errors)

    return all_errors


def _classify_schema_error(error: JsonSchemaValidationError) -> ErrorType:
    """Classify a jsonschema validation error into our error type taxonomy."""
    validator_type = error.validator

    if validator_type == "required":
        return ErrorType.MISSING_FIELD
    elif validator_type in ("type", "enum", "format", "pattern"):
        return ErrorType.TYPE_MISMATCH
    elif validator_type == "additionalProperties":
        return ErrorType.SCHEMA_VIOLATION
    elif validator_type in ("minItems", "minLength", "minimum", "maximum"):
        return ErrorType.SCHEMA_VIOLATION
    else:
        return ErrorType.SCHEMA_VIOLATION


def _format_path(path) -> str:
    """Format a jsonschema path deque into a readable JSON path string."""
    parts = []
    for part in path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            if parts:
                parts.append(f".{part}")
            else:
                parts.append(str(part))
    return "".join(parts) if parts else "$"
