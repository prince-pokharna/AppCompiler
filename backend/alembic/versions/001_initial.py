"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("current_stage", sa.String(30), nullable=True),
        sa.Column("progress_pct", sa.Float(), server_default="0.0"),
        sa.Column("fast_mode", sa.Boolean(), server_default="false"),
        sa.Column("skip_codegen", sa.Boolean(), server_default="false"),
        sa.Column("result_schema", postgresql.JSON(), nullable=True),
        sa.Column("code_result", postgresql.JSON(), nullable=True),
        sa.Column("validation_report", postgresql.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_duration_ms", sa.Integer(), server_default="0"),
        sa.Column("total_cost_usd", sa.Float(), server_default="0.0"),
        sa.Column("total_input_tokens", sa.Integer(), server_default="0"),
        sa.Column("total_output_tokens", sa.Integer(), server_default="0"),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("errors_found", sa.Integer(), server_default="0"),
        sa.Column("errors_repaired", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("total_prompts", sa.Integer(), server_default="0"),
        sa.Column("completed_prompts", sa.Integer(), server_default="0"),
        sa.Column("success_count", sa.Integer(), server_default="0"),
        sa.Column("failure_count", sa.Integer(), server_default="0"),
        sa.Column("total_cost_usd", sa.Float(), server_default="0.0"),
        sa.Column("summary", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("eval_run_id", sa.String(36), nullable=False, index=True),
        sa.Column("prompt_id", sa.String(50), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("success", sa.Boolean(), server_default="false"),
        sa.Column("stage_times", postgresql.JSON(), nullable=True),
        sa.Column("total_latency_ms", sa.Integer(), server_default="0"),
        sa.Column("retry_counts", postgresql.JSON(), nullable=True),
        sa.Column("repair_counts", sa.Integer(), server_default="0"),
        sa.Column("errors_found", sa.Integer(), server_default="0"),
        sa.Column("errors_resolved", sa.Integer(), server_default="0"),
        sa.Column("token_usage", postgresql.JSON(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), server_default="0.0"),
        sa.Column("failure_type", sa.String(50), nullable=True),
        sa.Column("assumptions_made", postgresql.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_schema", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_table("generation_jobs")
