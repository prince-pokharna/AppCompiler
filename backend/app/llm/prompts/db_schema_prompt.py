"""System prompt for Stage 3c: Database Schema generation."""

import json

from app.llm.prompt_loader import load_prompt

DB_SCHEMA_SYSTEM_PROMPT = load_prompt("v1", "05_db_schema", "system")

def get_db_schema_user_prompt(intent_json: dict, architecture_json: dict) -> str:
    """Build the user message for database schema generation."""
    return (
        f"Generate the complete database schema for this application.\n\n"
        f"APPLICATION INTENT:\n{json.dumps(intent_json, indent=2)}\n\n"
        f"ARCHITECTURE:\n{json.dumps(architecture_json, indent=2)}"
    )
