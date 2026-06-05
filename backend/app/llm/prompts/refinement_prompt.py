"""System prompt for Stage 5: Cross-layer Refinement."""

import json

from app.llm.prompt_loader import load_prompt

REFINEMENT_SYSTEM_PROMPT = load_prompt("v1", "08_refinement", "system")

def get_refinement_user_prompt(
    full_schema_json: dict,
    unresolved_issues: list[dict],
) -> str:
    """Build the user message for refinement."""
    return (
        f"Resolve the following inconsistencies in this application schema.\n\n"
        f"FULL APPLICATION SCHEMA:\n{json.dumps(full_schema_json, indent=2)}\n\n"
        f"UNRESOLVED ISSUES:\n{json.dumps(unresolved_issues, indent=2)}\n\n"
        f"Fix each issue and return the corrected sections."
    )
