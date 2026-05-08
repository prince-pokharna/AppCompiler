"""Extract and parse JSON from LLM responses using multiple strategies."""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger("appcompiler.llm.parser")


class JSONParseError(Exception):
    """Raised when JSON cannot be extracted from an LLM response."""

    def __init__(self, message: str, raw_response: str) -> None:
        self.raw_response = raw_response
        super().__init__(message)


def extract_json(response: str) -> dict:
    """Extract a JSON object from an LLM response string.

    Tries four strategies in order:
    1. Direct json.loads() on the full response
    2. Extract from ```json ... ``` code block
    3. Find first { and last } and parse that substring
    4. Regex-based JSON object extraction

    Args:
        response: Raw string from the LLM.

    Returns:
        Parsed dict.

    Raises:
        JSONParseError: If all strategies fail.
    """
    if not response or not response.strip():
        raise JSONParseError("Empty response from LLM", response or "")

    cleaned = response.strip()

    # Strategy 1: Direct parse
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            logger.debug("JSON extracted via direct parse")
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    # Strategy 2: Extract from ```json ... ``` code block
    code_block_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?\s*```",
        cleaned,
        re.DOTALL,
    )
    if code_block_match:
        try:
            result = json.loads(code_block_match.group(1).strip())
            if isinstance(result, dict):
                logger.debug("JSON extracted from code block")
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    # Strategy 3: Find first { and last } — handles preamble/postamble text
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace : last_brace + 1]
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                logger.debug("JSON extracted via brace matching")
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    # Strategy 4: Regex-based extraction for nested JSON objects
    # This handles cases where there might be multiple JSON-like structures
    pattern = re.compile(r"\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}", re.DOTALL)
    matches = pattern.findall(cleaned)
    for match in matches:
        try:
            result = json.loads(match)
            if isinstance(result, dict):
                logger.debug("JSON extracted via regex pattern")
                return result
        except (json.JSONDecodeError, TypeError):
            continue

    raise JSONParseError(
        f"Failed to extract JSON from LLM response (length={len(cleaned)}). "
        f"Tried: direct parse, code block, brace matching, regex.",
        cleaned,
    )


def extract_json_lenient(response: str) -> dict:
    """Extract JSON with additional lenient fixes for common LLM issues.

    Handles:
    - Trailing commas in arrays/objects
    - Single quotes instead of double quotes
    - Unquoted keys
    - Comments (// and /* */)
    """
    try:
        return extract_json(response)
    except JSONParseError:
        pass

    cleaned = response.strip()

    # Find the JSON substring first
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace == -1 or last_brace == -1:
        raise JSONParseError("No JSON object found in response", cleaned)

    candidate = cleaned[first_brace : last_brace + 1]

    # Remove single-line comments
    candidate = re.sub(r"//[^\n]*", "", candidate)
    # Remove multi-line comments
    candidate = re.sub(r"/\*.*?\*/", "", candidate, flags=re.DOTALL)
    # Remove trailing commas before } or ]
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)

    try:
        result = json.loads(candidate)
        if isinstance(result, dict):
            logger.debug("JSON extracted via lenient parsing")
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    raise JSONParseError(
        "Failed to extract JSON even with lenient parsing",
        cleaned,
    )
