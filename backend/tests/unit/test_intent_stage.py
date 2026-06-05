"""Unit tests for Stage 1 intent extraction."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.client import LLMResponse
from app.pipeline.stage1_intent import extract_intent
from app.utils.cost_tracker import CostTracker


@pytest.mark.asyncio
async def test_extract_intent_success(intent_fixture: dict):
    llm = MagicMock()
    llm.complete = AsyncMock(
        return_value=LLMResponse(
            content=json.dumps(intent_fixture),
            model="gpt-4o",
            input_tokens=100,
            output_tokens=200,
            latency_ms=50,
        )
    )
    llm.complete_with_retry_feedback = llm.complete

    tracker = CostTracker()
    intent, retries = await extract_intent(
        user_input="Build a CRM with contacts and deals",
        llm_client=llm,
        cost_tracker=tracker,
        fast_mode=False,
    )

    assert intent.app_name == "ContactManager"
    assert intent.app_type == "crm"
    assert retries == 0
    assert tracker.total_input_tokens() == 100


@pytest.mark.asyncio
async def test_extract_intent_retries_then_succeeds(intent_fixture: dict):
    bad = LLMResponse(
        content="not valid json {{{",
        model="gpt-4o",
        input_tokens=10,
        output_tokens=5,
        latency_ms=10,
    )
    good = LLMResponse(
        content=json.dumps(intent_fixture),
        model="gpt-4o",
        input_tokens=10,
        output_tokens=50,
        latency_ms=10,
    )

    llm = MagicMock()
    llm.complete = AsyncMock(side_effect=[bad, good])
    llm.complete_with_retry_feedback = llm.complete

    intent, retries = await extract_intent(
        user_input="Build a CRM",
        llm_client=llm,
        cost_tracker=CostTracker(),
    )

    assert intent.app_name == "ContactManager"
    assert retries >= 1
