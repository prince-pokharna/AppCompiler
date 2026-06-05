"""System prompt for Stage 3a: UI Schema generation."""

import json

from app.llm.prompt_loader import load_prompt

UI_SCHEMA_SYSTEM_PROMPT = load_prompt("v1", "03_ui_schema", "system")

def get_ui_schema_user_prompt(intent_json: dict, architecture_json: dict) -> str:
    """Build the user message for UI schema generation."""
    return (
        f"Generate the complete UI schema for this application.\n\n"
        f"APPLICATION INTENT:\n{json.dumps(intent_json, indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(architecture_json, indent=2)}"
    )
