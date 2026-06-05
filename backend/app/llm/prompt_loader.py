"""Load versioned Jinja2 prompts from backend/prompts/."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

PROMPTS_ROOT = Path(__file__).resolve().parents[2] / "prompts"

_env: Environment | None = None


def _get_env(version: str) -> Environment:
    global _env
    prompts_dir = PROMPTS_ROOT / version
    if not prompts_dir.is_dir():
        raise FileNotFoundError(f"Prompt version directory not found: {prompts_dir}")
    return Environment(
        loader=FileSystemLoader(str(prompts_dir)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )


@lru_cache(maxsize=64)
def load_prompt(
    version: str,
    name: str,
    part: str = "system",
    **template_vars: object,
) -> str:
    """Load and optionally render a prompt template.

    Args:
        version: Prompt set version (e.g. "v1").
        name: Base filename without extension (e.g. "01_intent_extraction").
        part: "system" or "user".
        **template_vars: Variables passed to user templates.
    """
    env = _get_env(version)
    filename = f"{name}.{part}.jinja2"
    template = env.get_template(filename)
    if part == "system" and not template_vars:
        return template.render()
    return template.render(**template_vars)
