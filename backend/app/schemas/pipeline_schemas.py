"""Pydantic models for pipeline stage I/O, validation reports, and repair events."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    """Pipeline stage identifiers."""
    INTENT = "intent"
    DESIGN = "design"
    SCHEMAS = "schemas"
    VALIDATION = "validation"
    REFINEMENT = "refinement"
    CODEGEN = "codegen"


class StageStatus(str, Enum):
    """Status of a pipeline stage."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobStatus(str, Enum):
    """Overall job status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ──────────────────────────────────────────────
# Pipeline Progress
# ──────────────────────────────────────────────

class StageProgress(BaseModel):
    """Progress info for a single pipeline stage."""
    stage: PipelineStage
    status: StageStatus = StageStatus.PENDING
    duration_ms: int = 0
    message: str = ""
    retries: int = 0
    errors_found: int = 0
    errors_repaired: int = 0


class PipelineProgress(BaseModel):
    """Overall pipeline progress."""
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    current_stage: PipelineStage | None = None
    progress_pct: float = 0.0
    stages: list[StageProgress] = Field(default_factory=list)
    error: str | None = None


# ──────────────────────────────────────────────
# Validation & Repair
# ──────────────────────────────────────────────

class ErrorType(str, Enum):
    """Classification of validation errors."""
    MISSING_FIELD = "missing_field"
    TYPE_MISMATCH = "type_mismatch"
    ORPHAN_REF = "orphan_ref"
    INCONSISTENCY = "inconsistency"
    SCHEMA_VIOLATION = "schema_violation"


class ValidationError(BaseModel):
    """A single validation error."""
    error_type: ErrorType
    layer: str = Field(..., description="ui, api, database, auth, intent, architecture")
    path: str = Field(default="", description="JSON path to the error e.g. tables[0].columns[2].type")
    message: str
    severity: str = Field(default="error", description="error, warning")
    auto_repairable: bool = False


class RepairAction(BaseModel):
    """A single repair action taken."""
    error_type: ErrorType
    layer: str
    description: str
    method: str = Field(..., description="llm_repair, programmatic, refinement")
    success: bool = True
    duration_ms: int = 0


class ValidationReport(BaseModel):
    """Complete validation report for a pipeline run."""
    errors_found: list[ValidationError] = Field(default_factory=list)
    repairs_made: list[RepairAction] = Field(default_factory=list)
    unresolved_issues: list[ValidationError] = Field(default_factory=list)
    total_errors: int = 0
    total_repaired: int = 0
    total_unresolved: int = 0
    validation_time_ms: int = 0
    repair_time_ms: int = 0


# ──────────────────────────────────────────────
# SSE Events
# ──────────────────────────────────────────────

class SSEEvent(BaseModel):
    """A Server-Sent Event payload."""
    event: str = Field(
        ...,
        description="stage_start, stage_complete, repair, validation, done, error",
    )
    data: dict = Field(default_factory=dict)


# ──────────────────────────────────────────────
# Code Generation Output
# ──────────────────────────────────────────────

class GeneratedFile(BaseModel):
    """A single generated source file."""
    path: str
    content: str
    language: str = "typescript"


class ExecutionReport(BaseModel):
    """Report from runtime simulation of generated code."""
    compilation_success: bool = False
    type_errors: list[str] = Field(default_factory=list)
    schema_errors: list[str] = Field(default_factory=list)
    runtime_errors: list[str] = Field(default_factory=list)
    checks_skipped: list[str] = Field(default_factory=list)
    duration_ms: int = 0


class CodeGenerationResult(BaseModel):
    """Complete code generation output."""
    generated_files: list[GeneratedFile] = Field(default_factory=list)
    execution_report: ExecutionReport = Field(default_factory=ExecutionReport)
    total_files: int = 0
    total_lines: int = 0


# ──────────────────────────────────────────────
# Pipeline Options
# ──────────────────────────────────────────────

class PipelineOptions(BaseModel):
    """Options controlling pipeline behavior."""
    skip_codegen: bool = False
    fast_mode: bool = False
