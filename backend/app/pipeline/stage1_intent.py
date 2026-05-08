"""Stage 1: Intent Extraction — parses NL input into structured IntentSchema."""

from __future__ import annotations

import logging

from app.llm.client import LLMClient, LLMResponse
from app.llm.prompts.intent_prompt import INTENT_SYSTEM_PROMPT, get_intent_user_prompt
from app.llm.response_parser import JSONParseError, extract_json_lenient
from app.schemas.app_schema import IntentSchema
from app.utils.cost_tracker import CostTracker

logger = logging.getLogger("appcompiler.pipeline.stage1")


def _fallback_intent(user_input: str) -> dict:
    """Return a minimal valid IntentSchema when all retries fail."""
    words = user_input.strip().split()
    app_name = "".join(w.capitalize() for w in words[:3]) if words else "MyApp"
    app_name = "".join(c for c in app_name if c.isalnum()) or "MyApp"
    return {
        "app_name": app_name,
        "app_type": "other",
        "description": f"An application based on: {user_input[:200]}",
        "core_features": ["user_management", "dashboard", "data_management"],
        "entities": ["User"],
        "roles": ["admin", "user"],
        "auth_required": True,
        "payment_required": False,
        "analytics_required": False,
        "assumptions": [
            "Input was too vague or could not be parsed; using minimal defaults",
            f"Original input: {user_input[:100]}",
        ],
        "clarifications_needed": [
            "What specific features does this app need?",
            "What types of data will it manage?",
        ],
    }


async def extract_intent(
    user_input: str,
    llm_client: LLMClient,
    cost_tracker: CostTracker,
    fast_mode: bool = False,
) -> tuple[IntentSchema, int]:
    """Extract structured intent from natural language input.

    Args:
        user_input: Raw NL description from user.
        llm_client: The LLM client to use.
        cost_tracker: Cost tracker for recording usage.
        fast_mode: If True, use the fast (cheaper) model.

    Returns:
        Tuple of (IntentSchema, retry_count).
    """
    from app.config import get_settings
    settings = get_settings()

    model = settings.fast_model if fast_mode else settings.default_model
    user_prompt = get_intent_user_prompt(user_input)
    max_retries = 3
    last_error: str | None = None
    retries = 0

    for attempt in range(max_retries):
        try:
            if last_error and attempt > 0:
                response: LLMResponse = await llm_client.complete_with_retry_feedback(
                    system=INTENT_SYSTEM_PROMPT,
                    user=user_prompt,
                    error_message=last_error,
                    model=model,
                    temperature=0.1,
                    max_tokens=2000,
                )
            else:
                response = await llm_client.complete(
                    system=INTENT_SYSTEM_PROMPT,
                    user=user_prompt,
                    model=model,
                    temperature=0.1,
                    max_tokens=2000,
                )

            cost_tracker.record(
                stage="intent",
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
            )

            parsed = extract_json_lenient(response.content)
            intent = IntentSchema(**parsed)

            logger.info(
                f"Intent extracted: {intent.app_name} ({intent.app_type})",
                extra={"retries": retries, "app_name": intent.app_name},
            )
            return intent, retries

        except JSONParseError as e:
            retries += 1
            last_error = f"JSON parse error: {str(e)[:200]}"
            logger.warning(f"Intent extraction attempt {attempt + 1} failed: {last_error}")

        except Exception as e:
            retries += 1
            last_error = f"Validation error: {str(e)[:200]}"
            logger.warning(f"Intent extraction attempt {attempt + 1} failed: {last_error}")

    # All retries exhausted — use fallback
    logger.warning("All intent extraction retries exhausted, using fallback")
    fallback = _fallback_intent(user_input)
    return IntentSchema(**fallback), retries
