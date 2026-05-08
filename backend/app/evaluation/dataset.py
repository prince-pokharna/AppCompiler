"""Evaluation dataset — 20 test prompts (10 real + 10 edge cases)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TestPrompt:
    """A single test prompt for evaluation."""
    id: str
    text: str
    category: str  # "real" or "edge"
    description: str


EVALUATION_PROMPTS: list[TestPrompt] = [
    # ── Real Product Prompts (10) ──
    TestPrompt(
        id="prompt_1",
        text=(
            "Build a CRM with login, contacts, deals pipeline, dashboard, admin and sales roles, "
            "email tracking, and Stripe payment for premium plan"
        ),
        category="real",
        description="Full-featured CRM with auth, roles, payments",
    ),
    TestPrompt(
        id="prompt_2",
        text=(
            "Create a project management tool like Linear with teams, issues, sprints, "
            "priorities, assignees, and GitHub integration"
        ),
        category="real",
        description="Project management with Agile features",
    ),
    TestPrompt(
        id="prompt_3",
        text=(
            "Build an e-commerce platform with products, cart, checkout, orders, "
            "seller dashboard, buyer dashboard, and Stripe payments"
        ),
        category="real",
        description="Multi-sided e-commerce marketplace",
    ),
    TestPrompt(
        id="prompt_4",
        text=(
            "Create a learning management system with courses, lessons, quizzes, "
            "student progress tracking, instructor and student roles"
        ),
        category="real",
        description="LMS with progress tracking and roles",
    ),
    TestPrompt(
        id="prompt_5",
        text=(
            "Build a multi-tenant SaaS analytics dashboard with workspaces, "
            "data sources, charts, alerts, and team collaboration"
        ),
        category="real",
        description="Multi-tenant SaaS analytics",
    ),
    TestPrompt(
        id="prompt_6",
        text=(
            "Create a booking system for a clinic with appointments, doctors, "
            "patients, availability calendar, reminders, and billing"
        ),
        category="real",
        description="Clinic booking with scheduling",
    ),
    TestPrompt(
        id="prompt_7",
        text=(
            "Build a social media scheduling tool with posts, calendars, "
            "multi-platform publishing, analytics, and team roles"
        ),
        category="real",
        description="Social media management tool",
    ),
    TestPrompt(
        id="prompt_8",
        text=(
            "Create a real estate platform with listings, agents, buyers, "
            "search filters, virtual tours, and lead management"
        ),
        category="real",
        description="Real estate listing platform",
    ),
    TestPrompt(
        id="prompt_9",
        text=(
            "Build an inventory management system with products, warehouses, "
            "suppliers, purchase orders, and low-stock alerts"
        ),
        category="real",
        description="Inventory management with alerts",
    ),
    TestPrompt(
        id="prompt_10",
        text=(
            "Create a HR platform with employees, departments, leave management, "
            "performance reviews, and payroll integration"
        ),
        category="real",
        description="HR management platform",
    ),
    # ── Edge Cases (10) ──
    TestPrompt(
        id="prompt_11",
        text="Build an app for my business",
        category="edge",
        description="[VAGUE] Minimal input",
    ),
    TestPrompt(
        id="prompt_12",
        text="I need a website with login and some features",
        category="edge",
        description="[VAGUE] Generic request",
    ),
    TestPrompt(
        id="prompt_13",
        text=(
            "Build a free platform where users pay for premium but also "
            "everything is free and admins can charge users but users have no payment info"
        ),
        category="edge",
        description="[CONFLICTING] Free vs paid contradiction",
    ),
    TestPrompt(
        id="prompt_14",
        text=(
            "All users are admins but admins cant see user data but users "
            "can see everything including admin data"
        ),
        category="edge",
        description="[CONFLICTING] Permission paradox",
    ),
    TestPrompt(
        id="prompt_15",
        text="Build a marketplace",
        category="edge",
        description="[INCOMPLETE] Single word — marketplace",
    ),
    TestPrompt(
        id="prompt_16",
        text="CRM",
        category="edge",
        description="[INCOMPLETE] Single word — CRM",
    ),
    TestPrompt(
        id="prompt_17",
        text=(
            "Build a CRM with 47 different user roles, a separate module "
            "for each of 200 contact fields, real-time sync across 15 databases, "
            "blockchain-based audit trail, AI recommendations, and quantum encryption"
        ),
        category="edge",
        description="[OVER-SPECIFIED] Unreasonable scope",
    ),
    TestPrompt(
        id="prompt_18",
        text=(
            "Build it with the best tech and make it fast and scalable "
            "and use AI everywhere and blockchain for trust"
        ),
        category="edge",
        description="[AMBIGUOUS TECH] Buzzword overload",
    ),
    TestPrompt(
        id="prompt_19",
        text=(
            "Build a HIPAA-compliant telemedicine platform with "
            "HL7 FHIR integration, ICD-10 coding, and prior auth workflows"
        ),
        category="edge",
        description="[DOMAIN-SPECIFIC] Healthcare terminology",
    ),
    TestPrompt(
        id="prompt_20",
        text=(
            "Construisez une application de gestion d'inventaire "
            "avec des rôles d'admin et de vendeur"
        ),
        category="edge",
        description="[MULTI-LANGUAGE] French input",
    ),
]


def get_prompt_by_id(prompt_id: str) -> TestPrompt | None:
    """Get a test prompt by its ID."""
    for prompt in EVALUATION_PROMPTS:
        if prompt.id == prompt_id:
            return prompt
    return None


def get_prompts_by_ids(prompt_ids: list[str]) -> list[TestPrompt]:
    """Get multiple prompts by their IDs. Empty list returns all."""
    if not prompt_ids:
        return EVALUATION_PROMPTS
    return [p for p in EVALUATION_PROMPTS if p.id in prompt_ids]


def get_prompts_by_category(category: str) -> list[TestPrompt]:
    """Get prompts filtered by category."""
    return [p for p in EVALUATION_PROMPTS if p.category == category]
