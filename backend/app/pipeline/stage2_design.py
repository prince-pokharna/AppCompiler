"""Stage 2: System Design — generates ArchitectureSchema from IntentSchema."""

from __future__ import annotations

import logging

from app.llm.client import LLMClient
from app.llm.prompts.design_prompt import DESIGN_SYSTEM_PROMPT, get_design_user_prompt
from app.llm.response_parser import JSONParseError, extract_json_lenient
from app.schemas.app_schema import ArchitectureSchema, IntentSchema
from app.utils.cost_tracker import CostTracker

logger = logging.getLogger("appcompiler.pipeline.stage2")


async def design_architecture(
    intent: IntentSchema,
    llm_client: LLMClient,
    cost_tracker: CostTracker,
    fast_mode: bool = False,
) -> tuple[ArchitectureSchema, int]:
    """Generate system architecture from structured intent.

    Args:
        intent: The parsed intent from Stage 1.
        llm_client: The LLM client to use.
        cost_tracker: Cost tracker for recording usage.
        fast_mode: If True, use the fast (cheaper) model.

    Returns:
        Tuple of (ArchitectureSchema, retry_count).
    """
    from app.config import get_settings
    settings = get_settings()

    model = settings.fast_model if fast_mode else settings.default_model
    intent_dict = intent.model_dump()
    user_prompt = get_design_user_prompt(intent_dict)
    max_retries = 3
    last_error: str | None = None
    retries = 0

    for attempt in range(max_retries):
        try:
            if last_error and attempt > 0:
                response = await llm_client.complete_with_retry_feedback(
                    system=DESIGN_SYSTEM_PROMPT,
                    user=user_prompt,
                    error_message=last_error,
                    model=model,
                    temperature=0.2,
                    max_tokens=4096,
                )
            else:
                response = await llm_client.complete(
                    system=DESIGN_SYSTEM_PROMPT,
                    user=user_prompt,
                    model=model,
                    temperature=0.2,
                    max_tokens=4096,
                )

            cost_tracker.record(
                stage="design",
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
            )

            parsed = extract_json_lenient(response.content)
            architecture = ArchitectureSchema(**parsed)

            logger.info(
                f"Architecture designed: {len(architecture.entities)} entities, "
                f"{len(architecture.pages)} pages",
                extra={
                    "entity_count": len(architecture.entities),
                    "page_count": len(architecture.pages),
                    "retries": retries,
                },
            )
            return architecture, retries

        except JSONParseError as e:
            retries += 1
            last_error = f"JSON parse error: {str(e)[:200]}"
            logger.warning(f"Design attempt {attempt + 1} failed: {last_error}")

        except Exception as e:
            retries += 1
            last_error = f"Validation error: {str(e)[:200]}"
            logger.warning(f"Design attempt {attempt + 1} failed: {last_error}")

    # Fallback: minimal architecture
    logger.warning("All design retries exhausted, using minimal architecture")
    fallback = ArchitectureSchema(
        entities=[],
        pages=["/login", "/dashboard"],
        api_groups=["auth"],
        role_permissions={role: ["read"] for role in intent.roles},
        business_rules=["Standard CRUD operations for all entities"],
        tech_decisions=["Next.js 14 with App Router", "PostgreSQL with Prisma"],
    )
    return fallback, retries
