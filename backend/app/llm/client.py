"""Anthropic Claude client wrapper with retry logic and structured logging."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from anthropic import APIError, APITimeoutError, AsyncAnthropic, RateLimitError

from app.config import get_settings

logger = logging.getLogger("appcompiler.llm")


@dataclass
class LLMResponse:
    """Structured response from an LLM call."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    retries: int = 0


@dataclass
class LLMUsageAccumulator:
    """Accumulates token usage across multiple calls."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    calls: list[LLMResponse] = field(default_factory=list)

    def record(self, response: LLMResponse) -> None:
        self.total_input_tokens += response.input_tokens
        self.total_output_tokens += response.output_tokens
        self.calls.append(response)


class LLMClient:
    """Async Anthropic client with retry, rate-limit handling, and logging."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._max_retries = settings.max_retries
        self._timeout = settings.llm_timeout

    async def complete(
        self,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a completion request to the Anthropic API.

        Args:
            system: System prompt.
            user: User message content.
            model: Model identifier (defaults to settings.default_model).
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            LLMResponse with content, token counts, and latency.

        Raises:
            APIError: If all retries are exhausted.
        """
        settings = get_settings()
        model = model or settings.default_model
        retries = 0
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            start = time.perf_counter()
            try:
                response = await self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    timeout=self._timeout,
                )

                latency_ms = int((time.perf_counter() - start) * 1000)

                content = ""
                for block in response.content:
                    if block.type == "text":
                        content += block.text

                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

                logger.info(
                    "LLM call completed",
                    extra={
                        "model": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "latency_ms": latency_ms,
                        "attempt": attempt + 1,
                        "temperature": temperature,
                    },
                )

                return LLMResponse(
                    content=content,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    retries=retries,
                )

            except RateLimitError as e:
                retries += 1
                last_error = e
                wait_time = min(2 ** attempt, 8)
                logger.warning(
                    "Rate limited, retrying",
                    extra={
                        "attempt": attempt + 1,
                        "wait_seconds": wait_time,
                        "model": model,
                    },
                )
                await asyncio.sleep(wait_time)

            except APITimeoutError as e:
                retries += 1
                last_error = e
                logger.warning(
                    "API timeout, retrying",
                    extra={"attempt": attempt + 1, "model": model},
                )
                await asyncio.sleep(1)

            except APIError as e:
                retries += 1
                last_error = e
                logger.error(
                    "API error",
                    extra={
                        "attempt": attempt + 1,
                        "status_code": getattr(e, "status_code", None),
                        "model": model,
                        "error": str(e),
                    },
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

        raise last_error or APIError("All retries exhausted")

    async def complete_with_retry_feedback(
        self,
        system: str,
        user: str,
        error_message: str | None = None,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Complete with optional error feedback from a previous attempt.

        If error_message is provided, it is appended to the user message
        to guide the LLM to fix the issue.
        """
        if error_message:
            user = (
                f"{user}\n\n"
                f"IMPORTANT: Your previous response had an error:\n{error_message}\n\n"
                f"Please fix this issue and return ONLY valid JSON."
            )

        return await self.complete(
            system=system,
            user=user,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def check_available(self) -> bool:
        """Check if the LLM API is accessible."""
        try:
            await self._client.messages.create(
                model="claude-haiku-3-5-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()
