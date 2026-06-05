"""System prompt for Stage 3d: Auth Schema generation."""

import json

from app.llm.prompt_loader import load_prompt

AUTH_SCHEMA_SYSTEM_PROMPT = load_prompt("v1", "06_auth_schema", "system")

def get_auth_schema_user_prompt(intent_json: dict, architecture_json: dict) -> str:
    """Build the user message for auth schema generation."""
    return (
        f"Generate the complete authentication and authorization schema for this application.\n\n"
        f"APPLICATION INTENT:\n{json.dumps(intent_json, indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(architecture_json, indent=2)}"
    )
