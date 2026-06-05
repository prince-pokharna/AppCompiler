"""System prompt for Stage 2: System Design / Architecture."""

import json

from app.llm.prompt_loader import load_prompt

DESIGN_SYSTEM_PROMPT = load_prompt("v1", "02_system_design", "system")


def get_design_user_prompt(intent_json: dict) -> str:
    """Build the user message for system design."""
    return (
        f"Design the full system architecture for this application.\n\n"
        f"APPLICATION INTENT:\n{json.dumps(intent_json, indent=2)}"
    )
