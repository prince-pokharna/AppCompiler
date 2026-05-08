"""Evaluator — tracks metrics for a single pipeline run."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RunMetrics:
    """Metrics collected during a single evaluation run."""
    prompt_id: str = ""
    prompt_text: str = ""
    success: bool = False
    stage_times: dict[str, int] = field(default_factory=dict)
    total_latency_ms: int = 0
    retry_counts: dict[str, int] = field(default_factory=dict)
    repair_counts: int = 0
    errors_found: int = 0
    errors_resolved: int = 0
    token_usage: dict[str, dict[str, int]] = field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    failure_type: str | None = None
    assumptions_made: list[str] = field(default_factory=list)
    error_message: str | None = None

    _start_time: float = field(default=0.0, repr=False)
    _stage_start: float = field(default=0.0, repr=False)
    _current_stage: str = field(default="", repr=False)

    def start(self) -> None:
        """Mark the start of the evaluation run."""
        self._start_time = time.perf_counter()

    def start_stage(self, stage: str) -> None:
        """Mark the start of a pipeline stage."""
        self._current_stage = stage
        self._stage_start = time.perf_counter()

    def end_stage(self, stage: str, retries: int = 0) -> None:
        """Mark the end of a pipeline stage and record its duration."""
        duration_ms = int((time.perf_counter() - self._stage_start) * 1000)
        self.stage_times[stage] = duration_ms
        if retries > 0:
            self.retry_counts[stage] = retries

    def finish(self, success: bool, failure_type: str | None = None) -> None:
        """Mark the evaluation run as complete."""
        self.total_latency_ms = int((time.perf_counter() - self._start_time) * 1000)
        self.success = success
        self.failure_type = failure_type

    def record_tokens(self, stage: str, input_tokens: int, output_tokens: int) -> None:
        """Record token usage for a stage."""
        self.token_usage[stage] = {
            "input": input_tokens,
            "output": output_tokens,
        }

    def record_validation(self, errors_found: int, errors_resolved: int, repair_counts: int) -> None:
        """Record validation and repair metrics."""
        self.errors_found = errors_found
        self.errors_resolved = errors_resolved
        self.repair_counts = repair_counts

    def to_dict(self) -> dict:
        """Convert metrics to a serializable dict."""
        return {
            "prompt_id": self.prompt_id,
            "prompt_text": self.prompt_text,
            "success": self.success,
            "stage_times": self.stage_times,
            "total_latency_ms": self.total_latency_ms,
            "retry_counts": self.retry_counts,
            "repair_counts": self.repair_counts,
            "errors_found": self.errors_found,
            "errors_resolved": self.errors_resolved,
            "token_usage": self.token_usage,
            "estimated_cost_usd": self.estimated_cost_usd,
            "failure_type": self.failure_type,
            "assumptions_made": self.assumptions_made,
            "error_message": self.error_message,
        }
