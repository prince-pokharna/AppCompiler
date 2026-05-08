"""Stage 3: Parallel Schema Generation — UI, API, DB, Auth schemas in parallel."""

from __future__ import annotations

import asyncio
import logging

from app.llm.client import LLMClient
from app.llm.prompts.api_schema_prompt import API_SCHEMA_SYSTEM_PROMPT, get_api_schema_user_prompt
from app.llm.prompts.auth_schema_prompt import AUTH_SCHEMA_SYSTEM_PROMPT, get_auth_schema_user_prompt
from app.llm.prompts.db_schema_prompt import DB_SCHEMA_SYSTEM_PROMPT, get_db_schema_user_prompt
from app.llm.prompts.ui_schema_prompt import UI_SCHEMA_SYSTEM_PROMPT, get_ui_schema_user_prompt
from app.llm.response_parser import JSONParseError, extract_json_lenient
from app.schemas.app_schema import (
    APISchema,
    ArchitectureSchema,
    AuthSchema,
    DatabaseSchema,
    IntentSchema,
    UISchema,
)
from app.utils.cost_tracker import CostTracker

logger = logging.getLogger("appcompiler.pipeline.stage3")


async def _generate_single_schema(
    system_prompt: str,
    user_prompt: str,
    schema_class: type,
    schema_name: str,
    llm_client: LLMClient,
    cost_tracker: CostTracker,
    model: str,
    temperature: float,
) -> tuple[object, int]:
    """Generate a single schema with retries."""
    max_retries = 3
    last_error: str | None = None
    retries = 0

    for attempt in range(max_retries):
        try:
            if last_error and attempt > 0:
                response = await llm_client.complete_with_retry_feedback(
                    system=system_prompt,
                    user=user_prompt,
                    error_message=last_error,
                    model=model,
                    temperature=temperature,
                    max_tokens=4096,
                )
            else:
                response = await llm_client.complete(
                    system=system_prompt,
                    user=user_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=4096,
                )

            cost_tracker.record(
                stage=f"schemas_{schema_name}",
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
            )

            parsed = extract_json_lenient(response.content)
            schema = schema_class(**parsed)
            logger.info(f"{schema_name} schema generated successfully")
            return schema, retries

        except JSONParseError as e:
            retries += 1
            last_error = f"JSON parse error: {str(e)[:200]}"
            logger.warning(f"{schema_name} schema attempt {attempt + 1} failed: {last_error}")

        except Exception as e:
            retries += 1
            last_error = f"Validation error: {str(e)[:200]}"
            logger.warning(f"{schema_name} schema attempt {attempt + 1} failed: {last_error}")

    logger.error(f"All retries exhausted for {schema_name} schema, using empty default")
    return schema_class(), retries


async def generate_schemas(
    intent: IntentSchema,
    architecture: ArchitectureSchema,
    llm_client: LLMClient,
    cost_tracker: CostTracker,
    fast_mode: bool = False,
) -> tuple[UISchema, APISchema, DatabaseSchema, AuthSchema, dict[str, int]]:
    """Generate all 4 schemas in parallel.

    Args:
        intent: Parsed intent from Stage 1.
        architecture: Architecture from Stage 2.
        llm_client: The LLM client.
        cost_tracker: Cost tracker.
        fast_mode: Use cheaper model for some schemas.

    Returns:
        Tuple of (UISchema, APISchema, DatabaseSchema, AuthSchema, retry_counts).
    """
    from app.config import get_settings
    settings = get_settings()
    model = settings.default_model

    intent_dict = intent.model_dump()
    arch_dict = architecture.model_dump()

    tasks = [
        _generate_single_schema(
            system_prompt=UI_SCHEMA_SYSTEM_PROMPT,
            user_prompt=get_ui_schema_user_prompt(intent_dict, arch_dict),
            schema_class=UISchema,
            schema_name="ui",
            llm_client=llm_client,
            cost_tracker=cost_tracker,
            model=model,
            temperature=0.3,
        ),
        _generate_single_schema(
            system_prompt=API_SCHEMA_SYSTEM_PROMPT,
            user_prompt=get_api_schema_user_prompt(intent_dict, arch_dict),
            schema_class=APISchema,
            schema_name="api",
            llm_client=llm_client,
            cost_tracker=cost_tracker,
            model=model,
            temperature=0.1,
        ),
        _generate_single_schema(
            system_prompt=DB_SCHEMA_SYSTEM_PROMPT,
            user_prompt=get_db_schema_user_prompt(intent_dict, arch_dict),
            schema_class=DatabaseSchema,
            schema_name="db",
            llm_client=llm_client,
            cost_tracker=cost_tracker,
            model=model,
            temperature=0.1,
        ),
        _generate_single_schema(
            system_prompt=AUTH_SCHEMA_SYSTEM_PROMPT,
            user_prompt=get_auth_schema_user_prompt(intent_dict, arch_dict),
            schema_class=AuthSchema,
            schema_name="auth",
            llm_client=llm_client,
            cost_tracker=cost_tracker,
            model=model,
            temperature=0.1,
        ),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    ui_schema = UISchema()
    api_schema = APISchema()
    db_schema = DatabaseSchema()
    auth_schema = AuthSchema()
    retry_counts: dict[str, int] = {}

    schema_names = ["ui", "api", "db", "auth"]
    defaults = [ui_schema, api_schema, db_schema, auth_schema]

    for i, result in enumerate(results):
        name = schema_names[i]
        if isinstance(result, Exception):
            logger.error(f"Schema generation failed for {name}: {result}")
            retry_counts[name] = 3
        else:
            schema, retries = result
            retry_counts[name] = retries
            if i == 0:
                ui_schema = schema  # type: ignore
            elif i == 1:
                api_schema = schema  # type: ignore
            elif i == 2:
                db_schema = schema  # type: ignore
            elif i == 3:
                auth_schema = schema  # type: ignore

    logger.info(
        "All schemas generated",
        extra={
            "ui_pages": len(ui_schema.pages),
            "api_endpoints": len(api_schema.endpoints),
            "db_tables": len(db_schema.tables),
            "auth_roles": len(auth_schema.roles),
        },
    )

    return ui_schema, api_schema, db_schema, auth_schema, retry_counts
