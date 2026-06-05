"""Integration test — full pipeline with mocked LLM stages."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.pipeline.orchestrator import run_pipeline
from app.schemas.app_schema import (
    APISchema,
    ArchitectureSchema,
    AuthSchema,
    DatabaseSchema,
    EntityDefinition,
    FieldDefinition,
    IntentSchema,
    PageSchema,
    UISchema,
)
from app.schemas.pipeline_schemas import JobStatus, PipelineOptions, ValidationReport
from app.services import job_service

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _minimal_layers():
    arch = ArchitectureSchema(
        entities=[
            EntityDefinition(
                name="Contact",
                fields=[
                    FieldDefinition(name="id", type="uuid", required=True),
                    FieldDefinition(name="name", type="string", required=True),
                ],
            )
        ],
        pages=["/dashboard", "/contacts"],
        api_groups=["contacts"],
        role_permissions={"admin": ["manage_all"]},
    )
    ui = UISchema(pages=[PageSchema(name="Dashboard", route="/dashboard")])
    api = APISchema(endpoints=[])
    database = DatabaseSchema(tables=[])
    auth = AuthSchema(roles=["admin", "user"], oauth_providers=["credentials"])
    return arch, ui, api, database, auth


@pytest.mark.asyncio
async def test_pipeline_completes_with_mocks():
    intent = IntentSchema(**_load("intent_response.json"))
    arch, ui, api, database, auth = _minimal_layers()
    report = ValidationReport(
        total_errors=0,
        total_repaired=0,
        total_unresolved=0,
        unresolved_issues=[],
        repairs_made=[],
    )

    job_id = "test-job-integration-001"
    await job_service.create_job(
        job_id=job_id,
        prompt="Build a CRM with contacts and dashboard",
        options=PipelineOptions(skip_codegen=True),
    )

    with (
        patch("app.pipeline.orchestrator.extract_intent", AsyncMock(return_value=(intent, 0))),
        patch("app.pipeline.orchestrator.design_architecture", AsyncMock(return_value=(arch, 0))),
        patch(
            "app.pipeline.orchestrator.generate_schemas",
            AsyncMock(return_value=(ui, api, database, auth, {"ui": 0, "api": 0, "database": 0, "auth": 0})),
        ),
        patch(
            "app.pipeline.orchestrator.validate_and_repair",
            AsyncMock(return_value=(ui, api, database, auth, report)),
        ),
        patch(
            "app.pipeline.orchestrator.refine_schemas",
            AsyncMock(return_value=(ui, api, database, auth, False)),
        ),
        patch("app.pipeline.orchestrator.LLMClient") as mock_llm_cls,
    ):
        mock_llm_cls.return_value.close = AsyncMock()
        await run_pipeline(
            job_id,
            "Build a CRM with contacts and dashboard",
            PipelineOptions(skip_codegen=True),
        )

    state = await job_service.get_job_state_merged(job_id)
    assert state is not None
    assert state["status"] == JobStatus.COMPLETED.value
    assert state.get("result") is not None
    assert state.get("total_input_tokens", 0) >= 0
