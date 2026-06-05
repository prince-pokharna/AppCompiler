"""Request/response models for all API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.schemas.app_schema import CompletedAppSchema, GenerationMeta
from app.schemas.pipeline_schemas import (
    CodeGenerationResult,
    JobStatus,
    PipelineOptions,
    PipelineProgress,
    ValidationReport,
)


# ──────────────────────────────────────────────
# Generation
# ──────────────────────────────────────────────

_FORBIDDEN_PROMPT_FRAGMENTS = ("ignore previous", "system:", "assistant:")


class GenerateRequest(BaseModel):
    """Request body for POST /api/generate."""
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Natural language app description",
    )
    options: PipelineOptions = Field(default_factory=PipelineOptions)

    @field_validator("prompt")
    @classmethod
    def validate_prompt_safety(cls, v: str) -> str:
        lowered = v.lower()
        for fragment in _FORBIDDEN_PROMPT_FRAGMENTS:
            if fragment in lowered:
                raise ValueError("Invalid prompt content")
        return v.strip()


class GenerateResponse(BaseModel):
    """Response body for POST /api/generate."""
    job_id: str
    status: JobStatus = JobStatus.QUEUED


# ──────────────────────────────────────────────
# Status
# ──────────────────────────────────────────────

class StatusResponse(BaseModel):
    """Response body for GET /api/status/{job_id}."""
    job_id: str
    status: JobStatus
    current_stage: str | None = None
    progress_pct: float = 0.0
    app_schema: CompletedAppSchema | None = Field(default=None, alias="schema")
    code_result: CodeGenerationResult | None = None
    validation_report: ValidationReport | None = None
    error: str | None = None

    class Config:
        populate_by_name = True


# ──────────────────────────────────────────────
# Result
# ──────────────────────────────────────────────

class TokenUsage(BaseModel):
    """Token and cost metrics for a completed job."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    total_duration_ms: int = 0


class ResultResponse(BaseModel):
    """Response body for GET /api/result/{job_id}."""
    job_id: str
    app_schema: CompletedAppSchema = Field(alias="schema")
    code_result: CodeGenerationResult | None = None
    validation_report: ValidationReport | None = None
    token_usage: TokenUsage | None = None

    class Config:
        populate_by_name = True


# ──────────────────────────────────────────────
# Evaluation
# ──────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    """Request body for POST /api/evaluate."""
    prompt_ids: list[str] = Field(
        default_factory=list,
        description="Prompt IDs to evaluate. Empty = run all 20.",
    )


class EvaluateResponse(BaseModel):
    """Response body for POST /api/evaluate."""
    eval_id: str
    status: str = "started"
    total_prompts: int = 0


class PromptResult(BaseModel):
    """Result for a single evaluation prompt."""
    prompt_id: str
    prompt_text: str
    success: bool = False
    stage_times: dict[str, int] = Field(default_factory=dict)
    total_latency_ms: int = 0
    retry_counts: dict[str, int] = Field(default_factory=dict)
    repair_counts: int = 0
    errors_found: int = 0
    errors_resolved: int = 0
    token_usage: dict[str, dict[str, int]] = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    failure_type: str | None = None
    assumptions_made: list[str] = Field(default_factory=list)
    error_message: str | None = None


class EvaluationResultsResponse(BaseModel):
    """Response body for GET /api/evaluate/{eval_id}/results."""
    eval_id: str
    status: str
    results: list[PromptResult] = Field(default_factory=list)
    summary: EvaluationSummary | None = None


class EvaluationSummary(BaseModel):
    """Summary statistics for an evaluation run."""
    total_prompts: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate_pct: float = 0.0
    avg_latency_ms: float = 0.0
    avg_retries: float = 0.0
    avg_repairs: float = 0.0
    total_cost_usd: float = 0.0
    failure_types: dict[str, int] = Field(default_factory=dict)


# ──────────────────────────────────────────────
# Health
# ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Response body for GET /api/health."""
    status: str = "ok"
    version: str = ""
    uptime_seconds: float = 0.0
    environment: str = ""
    llm_available: bool = False
    database_connected: bool = False
    redis_connected: bool = False
