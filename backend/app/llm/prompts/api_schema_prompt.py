"""System prompt for Stage 3b: API Schema generation."""

import json

from app.llm.prompt_loader import load_prompt

API_SCHEMA_SYSTEM_PROMPT = load_prompt("v1", "04_api_schema", "system")

def get_api_schema_user_prompt(intent_json: dict, architecture_json: dict) -> str:
    """Build the user message for API schema generation."""
    return (
        f"Generate the complete API schema for this application.\n\n"
        f"APPLICATION INTENT:\n{json.dumps(intent_json, indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(architecture_json, indent=2)}"
    )
