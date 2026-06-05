"""Unit tests for JSON schema validation."""

from __future__ import annotations

import pytest

from app.validator.json_validator import validate_json_structure


@pytest.fixture
def valid_intent() -> dict:
    return {
        "app_name": "TestApp",
        "app_type": "crm",
        "description": "A test CRM application for unit tests.",
        "core_features": ["contacts", "deals", "dashboard"],
        "entities": ["User", "Contact"],
        "roles": ["admin", "user"],
        "auth_required": True,
        "payment_required": False,
        "analytics_required": False,
        "assumptions": [],
        "clarifications_needed": [],
    }


def test_valid_intent_passes(valid_intent: dict):
    errors = validate_json_structure(valid_intent, "intent")
    assert errors == []


def test_invalid_intent_missing_field(valid_intent: dict):
    del valid_intent["app_name"]
    errors = validate_json_structure(valid_intent, "intent")
    assert len(errors) >= 1
    assert any("app_name" in e.message.lower() or e.path for e in errors)


def test_invalid_app_type_enum(valid_intent: dict):
    valid_intent["app_type"] = "invalid_type"
    errors = validate_json_structure(valid_intent, "intent")
    assert len(errors) >= 1
