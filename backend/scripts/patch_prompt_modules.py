"""Patch prompt modules to load system prompts from Jinja2."""

from __future__ import annotations

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

UPDATES = [
    ("app/llm/prompts/ui_schema_prompt.py", "UI_SCHEMA_SYSTEM_PROMPT", "03_ui_schema"),
    ("app/llm/prompts/api_schema_prompt.py", "API_SCHEMA_SYSTEM_PROMPT", "04_api_schema"),
    ("app/llm/prompts/db_schema_prompt.py", "DB_SCHEMA_SYSTEM_PROMPT", "05_db_schema"),
    ("app/llm/prompts/auth_schema_prompt.py", "AUTH_SCHEMA_SYSTEM_PROMPT", "06_auth_schema"),
    ("app/llm/prompts/repair_prompt.py", "REPAIR_SYSTEM_PROMPT", "07_repair"),
    ("app/llm/prompts/refinement_prompt.py", "REFINEMENT_SYSTEM_PROMPT", "08_refinement"),
]


def patch_file(path: Path, const: str, base: str) -> None:
    text = path.read_text(encoding="utf-8")
    if "from app.llm.prompt_loader import load_prompt" in text:
        print(f"skip {path.name}")
        return

    marker = f"{const} = \"\"\""
    start = text.find(marker)
    if start < 0:
        raise ValueError(f"{const} not found in {path}")
    end = text.find('"""', start + len(marker)) + 3
    while end < len(text) and text[end] in "\r\n":
        end += 1

    replacement = (
        "from app.llm.prompt_loader import load_prompt\n\n"
        f'{const} = load_prompt("v1", "{base}", "system")\n\n'
    )
    new_text = text[:start] + replacement + text[end:]

    if "from app.llm.prompt_loader import load_prompt" not in new_text:
        new_text = "from app.llm.prompt_loader import load_prompt\n" + new_text

    path.write_text(new_text, encoding="utf-8")
    print(f"patched {path.name}")


def main() -> None:
    for rel, const, base in UPDATES:
        patch_file(BACKEND / rel, const, base)


if __name__ == "__main__":
    main()
