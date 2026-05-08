"""Token usage and cost tracking per pipeline stage."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("appcompiler.utils.cost_tracker")

# Anthropic pricing per million tokens (as of 2025)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-3-5-20241022": {"input": 0.80, "output": 4.0},
}

# Fallback pricing for unknown models
DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


@dataclass
class StageUsage:
    """Token usage for a single pipeline stage."""
    stage: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    calls: int = 0


class CostTracker:
    """Tracks token usage and cost across all pipeline stages."""

    def __init__(self) -> None:
        self._stages: dict[str, StageUsage] = {}

    def record(
        self,
        stage: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int = 0,
    ) -> None:
        """Record a single LLM call's usage.

        Args:
            stage: Pipeline stage name.
            model: Model identifier.
            input_tokens: Number of input tokens used.
            output_tokens: Number of output tokens used.
            latency_ms: Call latency in milliseconds.
        """
        if stage not in self._stages:
            self._stages[stage] = StageUsage(stage=stage, model=model)

        usage = self._stages[stage]
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        usage.latency_ms += latency_ms
        usage.calls += 1
        usage.model = model

        # Calculate cost
        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
        )
        usage.cost_usd += cost

        logger.debug(
            f"Cost recorded for {stage}",
            extra={
                "stage": stage,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost, 6),
            },
        )

    def get_stage_usage(self, stage: str) -> dict:
        """Get usage dict for a specific stage."""
        # Aggregate stages that start with the same prefix (e.g. schemas_ui, schemas_api)
        prefix = stage
        aggregated = StageUsage(stage=stage)

        for key, usage in self._stages.items():
            if key == prefix or key.startswith(f"{prefix}_"):
                aggregated.input_tokens += usage.input_tokens
                aggregated.output_tokens += usage.output_tokens
                aggregated.cost_usd += usage.cost_usd
                aggregated.latency_ms += usage.latency_ms
                aggregated.calls += usage.calls
                if usage.model:
                    aggregated.model = usage.model

        return {
            "input_tokens": aggregated.input_tokens,
            "output_tokens": aggregated.output_tokens,
            "cost_usd": round(aggregated.cost_usd, 6),
            "model": aggregated.model,
            "latency_ms": aggregated.latency_ms,
            "calls": aggregated.calls,
        }

    def total_cost(self) -> float:
        """Get total cost across all stages."""
        return round(sum(u.cost_usd for u in self._stages.values()), 6)

    def total_tokens(self) -> dict[str, int]:
        """Get total token counts."""
        return {
            "input": sum(u.input_tokens for u in self._stages.values()),
            "output": sum(u.output_tokens for u in self._stages.values()),
        }

    def summary(self) -> dict:
        """Get a complete cost summary."""
        return {
            "total_cost_usd": self.total_cost(),
            "total_tokens": self.total_tokens(),
            "stages": {
                name: {
                    "model": u.model,
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "cost_usd": round(u.cost_usd, 6),
                    "calls": u.calls,
                }
                for name, u in self._stages.items()
            },
        }
