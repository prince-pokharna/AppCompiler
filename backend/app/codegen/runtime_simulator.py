"""Runtime simulator — validates generated code via subprocess checks."""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

from app.schemas.pipeline_schemas import ExecutionReport

logger = logging.getLogger("appcompiler.codegen.runtime_simulator")


async def simulate_runtime(
    generated_files: dict[str, str],
    skip_checks: bool = False,
) -> ExecutionReport:
    """Simulate runtime validation of generated code.

    Writes files to a temp directory and runs TypeScript and Prisma checks.

    Args:
        generated_files: Dict mapping file paths to contents.
        skip_checks: If True, skip all checks.

    Returns:
        ExecutionReport with results of each check.
    """
    report = ExecutionReport(compilation_success=True)

    if skip_checks:
        report.checks_skipped = ["typescript_check", "prisma_validate"]
        logger.info("Runtime simulation skipped (fast mode)")
        return report

    has_node = shutil.which("node") is not None
    has_npx = shutil.which("npx") is not None

    if not has_node or not has_npx:
        report.checks_skipped.append("all — node/npx not available")
        logger.info("Runtime simulation skipped — node/npx not found")
        return report

    # Write files to temp directory
    tmp_dir = tempfile.mkdtemp(prefix="appcompiler_")
    try:
        for file_path, content in generated_files.items():
            full_path = Path(tmp_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

        # Check 1: TypeScript compilation check
        ts_errors = await _run_tsc_check(tmp_dir)
        if ts_errors:
            report.type_errors = ts_errors
            report.compilation_success = False

        # Check 2: Prisma schema validation
        prisma_errors = await _run_prisma_validate(tmp_dir)
        if prisma_errors:
            report.schema_errors = prisma_errors
            report.compilation_success = False

    except Exception as e:
        logger.error(f"Runtime simulation error: {e}")
        report.runtime_errors.append(str(e))
        report.compilation_success = False

    finally:
        # Clean up
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    return report


async def _run_tsc_check(project_dir: str) -> list[str]:
    """Run TypeScript type-check on the generated project."""
    errors: list[str] = []

    try:
        proc = await asyncio.create_subprocess_exec(
            "npx", "tsc", "--noEmit", "--pretty", "false",
            cwd=project_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            output = (stdout or b"").decode("utf-8", errors="replace")
            err_output = (stderr or b"").decode("utf-8", errors="replace")
            combined = (output + "\n" + err_output).strip()

            for line in combined.split("\n"):
                line = line.strip()
                if line and ("error" in line.lower() or "TS" in line):
                    errors.append(line[:200])

            if not errors and combined:
                errors.append(combined[:500])

            logger.info(f"TypeScript check found {len(errors)} error(s)")

    except asyncio.TimeoutError:
        errors.append("TypeScript check timed out after 30s")
    except FileNotFoundError:
        logger.info("npx/tsc not found, skipping TypeScript check")
    except Exception as e:
        errors.append(f"TypeScript check failed: {str(e)[:200]}")

    return errors


async def _run_prisma_validate(project_dir: str) -> list[str]:
    """Run Prisma schema validation."""
    errors: list[str] = []
    prisma_path = Path(project_dir) / "prisma" / "schema.prisma"

    if not prisma_path.exists():
        return errors

    try:
        proc = await asyncio.create_subprocess_exec(
            "npx", "prisma", "validate",
            f"--schema={prisma_path}",
            cwd=project_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            output = (stdout or b"").decode("utf-8", errors="replace")
            err_output = (stderr or b"").decode("utf-8", errors="replace")
            combined = (output + "\n" + err_output).strip()

            for line in combined.split("\n"):
                line = line.strip()
                if line and "error" in line.lower():
                    errors.append(line[:200])

            if not errors and combined:
                errors.append(combined[:500])

            logger.info(f"Prisma validation found {len(errors)} error(s)")

    except asyncio.TimeoutError:
        errors.append("Prisma validation timed out after 30s")
    except FileNotFoundError:
        logger.info("npx/prisma not found, skipping Prisma validation")
    except Exception as e:
        errors.append(f"Prisma validation failed: {str(e)[:200]}")

    return errors
