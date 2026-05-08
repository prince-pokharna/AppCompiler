"""SQLAlchemy ORM models for evaluation runs."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EvaluationRun(Base):
    """Tracks a batch evaluation run."""

    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    total_prompts: Mapped[int] = mapped_column(Integer, default=0)
    completed_prompts: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvaluationResult(Base):
    """Result for a single prompt within an evaluation run."""

    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    eval_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    prompt_id: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(default=False)

    # Metrics
    stage_times: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    retry_counts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    repair_counts: Mapped[int] = mapped_column(Integer, default=0)
    errors_found: Mapped[int] = mapped_column(Integer, default=0)
    errors_resolved: Mapped[int] = mapped_column(Integer, default=0)
    token_usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    failure_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assumptions_made: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
