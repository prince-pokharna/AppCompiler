"""One-off utility: export embedded Python prompts to Jinja2 templates."""

from __future__ import annotations

import ast
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PROMPTS_DIR = BACKEND / "prompts" / "v1"

EXPORTS = [
    ("app/llm/prompts/design_prompt.py", "DESIGN_SYSTEM_PROMPT", "02_system_design"),
    ("app/llm/prompts/ui_schema_prompt.py", "UI_SCHEMA_SYSTEM_PROMPT", "03_ui_schema"),
    ("app/llm/prompts/api_schema_prompt.py", "API_SCHEMA_SYSTEM_PROMPT", "04_api_schema"),
    ("app/llm/prompts/db_schema_prompt.py", "DB_SCHEMA_SYSTEM_PROMPT", "05_db_schema"),
    ("app/llm/prompts/auth_schema_prompt.py", "AUTH_SCHEMA_SYSTEM_PROMPT", "06_auth_schema"),
    ("app/llm/prompts/repair_prompt.py", "REPAIR_SYSTEM_PROMPT", "07_repair"),
    ("app/llm/prompts/refinement_prompt.py", "REFINEMENT_SYSTEM_PROMPT", "08_refinement"),
]


def extract_string_constant(source: str, name: str) -> str:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    raise ValueError(f"Constant {name} not found")


def main() -> None:
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    for rel_path, const_name, base_name in EXPORTS:
        path = BACKEND / rel_path
        source = path.read_text(encoding="utf-8")
        text = extract_string_constant(source, const_name)
        out = PROMPTS_DIR / f"{base_name}.system.jinja2"
        out.write_text(text.strip() + "\n", encoding="utf-8")
        print(f"Wrote {out.name}")


if __name__ == "__main__":
    main()
