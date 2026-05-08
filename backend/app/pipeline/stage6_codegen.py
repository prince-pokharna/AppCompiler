"""Stage 6: Code Generation — generates Next.js project from validated schema."""

from __future__ import annotations

import logging

from app.codegen.nextjs_generator import generate_nextjs_project
from app.codegen.runtime_simulator import simulate_runtime
from app.schemas.app_schema import CompletedAppSchema
from app.schemas.pipeline_schemas import CodeGenerationResult
from app.utils.cost_tracker import CostTracker

logger = logging.getLogger("appcompiler.pipeline.stage6")


async def generate_code(
    schema: CompletedAppSchema,
    cost_tracker: CostTracker,
    skip_validation: bool = False,
) -> CodeGenerationResult:
    """Generate a complete Next.js project from the validated schema.

    Args:
        schema: The fully validated CompletedAppSchema.
        cost_tracker: Cost tracker.
        skip_validation: If True, skip TypeScript and Prisma validation.

    Returns:
        CodeGenerationResult with generated files and execution report.
    """
    logger.info("Starting code generation")

    generated_files = generate_nextjs_project(schema)

    total_lines = sum(
        content.count("\n") + 1 for content in generated_files.values()
    )

    logger.info(
        f"Generated {len(generated_files)} files ({total_lines} total lines)",
        extra={"file_count": len(generated_files), "total_lines": total_lines},
    )

    # Runtime simulation
    execution_report = await simulate_runtime(
        generated_files=generated_files,
        skip_checks=skip_validation,
    )

    from app.schemas.pipeline_schemas import GeneratedFile

    file_list = [
        GeneratedFile(
            path=path,
            content=content,
            language=_detect_language(path),
        )
        for path, content in generated_files.items()
    ]

    result = CodeGenerationResult(
        generated_files=file_list,
        execution_report=execution_report,
        total_files=len(generated_files),
        total_lines=total_lines,
    )

    logger.info(
        f"Code generation complete: compilation_success={execution_report.compilation_success}"
    )
    return result


def _detect_language(path: str) -> str:
    """Detect language from file extension."""
    ext_map = {
        ".tsx": "typescript",
        ".ts": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".json": "json",
        ".prisma": "prisma",
        ".css": "css",
        ".md": "markdown",
    }
    for ext, lang in ext_map.items():
        if path.endswith(ext):
            return lang
    return "text"
