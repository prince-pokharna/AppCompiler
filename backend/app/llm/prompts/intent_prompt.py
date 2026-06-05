"""Stage 1 prompts — loaded from versioned Jinja2 templates."""

from app.llm.prompt_loader import load_prompt

PROMPT_VERSION = "v1"
PROMPT_NAME = "01_intent_extraction"

INTENT_SYSTEM_PROMPT = load_prompt(PROMPT_VERSION, PROMPT_NAME, "system")


def get_intent_user_prompt(user_input: str) -> str:
    """Build the user message for intent extraction."""
    return load_prompt(PROMPT_VERSION, PROMPT_NAME, "user", user_input=user_input)
