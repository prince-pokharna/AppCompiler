"""SQLAlchemy ORM models for generation jobs."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GenerationJob(Base):
    """Tracks a single pipeline generation run."""

    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    current_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    fast_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_codegen: Mapped[bool] = mapped_column(Boolean, default=False)

    # Result storage
    result_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    code_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    errors_found: Mapped[int] = mapped_column(Integer, default=0)
    errors_repaired: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
