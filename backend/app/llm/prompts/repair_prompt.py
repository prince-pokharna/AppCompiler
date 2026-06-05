"""System prompt for surgical repair of specific schema issues."""

import json

from app.llm.prompt_loader import load_prompt

REPAIR_SYSTEM_PROMPT = load_prompt("v1", "07_repair", "system")

def get_repair_missing_field_prompt(
    layer: str,
    field_name: str,
    field_type: str,
    context_json: dict,
) -> str:
    """Prompt for adding a missing required field."""
    return (
        f"The following {layer} schema is missing a required field.\n\n"
        f"MISSING FIELD: '{field_name}' of type '{field_type}'\n\n"
        f"CURRENT JSON:\n{json.dumps(context_json, indent=2)}\n\n"
        f"Add the missing field with a sensible default value and return the complete corrected JSON."
    )


def get_repair_orphan_ref_prompt(
    source_layer: str,
    reference: str,
    target_layer: str,
    source_json: dict,
    target_json: dict,
) -> str:
    """Prompt for fixing orphaned references between layers."""
    return (
        f"There is an orphaned reference in the {source_layer} schema.\n\n"
        f"ORPHAN REFERENCE: '{reference}' in {source_layer} has no matching target in {target_layer}.\n\n"
        f"SOURCE ({source_layer}):\n{json.dumps(source_json, indent=2)}\n\n"
        f"TARGET ({target_layer}):\n{json.dumps(target_json, indent=2)}\n\n"
        f"Either add the missing target to the {target_layer} schema or remove/fix the reference "
        f"in the {source_layer} schema. Return a JSON object with two keys: "
        f"'source' (corrected {source_layer} section) and 'target' (corrected {target_layer} section). "
        f"Only include sections that were changed."
    )


def get_repair_inconsistency_prompt(
    conflict_description: str,
    layers_json: dict[str, dict],
) -> str:
    """Prompt for resolving an inconsistency between layers."""
    layers_text = "\n\n".join(
        f"{layer.upper()} SCHEMA:\n{json.dumps(data, indent=2)}"
        for layer, data in layers_json.items()
    )
    return (
        f"There is an inconsistency between schema layers.\n\n"
        f"CONFLICT: {conflict_description}\n\n"
        f"{layers_text}\n\n"
        f"Return a JSON object with the corrected sections for each affected layer. "
        f"Keys should be layer names, values should be the corrected JSON for that layer."
    )
