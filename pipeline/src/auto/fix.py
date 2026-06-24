"""Auto-fix loop for the autonomous orchestrator.

Runs verification → fix → re-verify up to MAX_ATTEMPTS times.
Returns final status with per-attempt results.

@agent_context: Auto-fix for FX Regime Lab CEO Mode
@allowed_imports: [json, os, subprocess, sys, dataclasses, time, pathlib, re]
@forbidden_imports: [src.db, src.ai]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MAX_ATTEMPTS = 3
REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class FixAttempt:
    attempt: int
    status: str  # "passed" | "failed" | "skipped"
    errors_found: list[str]
    fix_applied: str
    duration_seconds: float


@dataclass(frozen=True)
class FixResult:
    directive: str
    max_attempts: int
    attempts: list[dict[str, Any]]
    final_status: str  # "fixed" | "partial" | "failed"
    summary: str
    total_duration_seconds: float


def _run_command(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str, str]:
    """Run a shell command and return (exit_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"


def _run_pytest(repo_root: Path) -> tuple[bool, list[str]]:
    """Run pytest and return (passed, list_of_errors)."""
    code, stdout, stderr = _run_command(
        ["python", "-m", "pytest", "-q"],
        repo_root / "pipeline",
        timeout=300,
    )
    output = stdout + stderr
    if code == 0 and "passed" in output:
        return True, []

    # Extract error lines
    errors = []
    for line in output.splitlines():
        if line.strip() and not line.startswith("="):
            errors.append(line.strip())
    return False, errors[:20]  # Cap at 20 errors


def _run_ruff(repo_root: Path) -> tuple[bool, list[str]]:
    """Run ruff and return (passed, list_of_errors)."""
    code, stdout, stderr = _run_command(
        ["python", "-m", "ruff", "check", "."],
        repo_root / "pipeline",
        timeout=120,
    )
    output = stdout + stderr
    if code == 0:
        return True, []

    errors = [line.strip() for line in output.splitlines() if line.strip()]
    return False, errors[:20]


def _run_npm_build(repo_root: Path) -> tuple[bool, list[str]]:
    """Run npm build and return (passed, list_of_errors)."""
    code, stdout, stderr = _run_command(
        ["npm", "run", "build"],
        repo_root / "web",
        timeout=300,
    )
    output = stdout + stderr
    if code == 0:
        return True, []

    errors = [
        line.strip()
        for line in output.splitlines()
        if "error" in line.lower() or "ERR!" in line
    ]
    return False, errors[:20]


def _run_npm_lint(repo_root: Path) -> tuple[bool, list[str]]:
    """Run biome lint and return (passed, list_of_errors)."""
    code, stdout, stderr = _run_command(
        ["npx", "biome", "check", "."],
        repo_root / "web",
        timeout=120,
    )
    output = stdout + stderr
    if code == 0 and "lint/suspicious" not in output:
        return True, []

    errors = [
        line.strip()
        for line in output.splitlines()
        if "error" in line.lower() or line.strip().startswith("✖")
    ]
    return False, errors[:20]


def _run_cursor_delegate(
    directive: str, tier: int, repo_root: Path
) -> tuple[bool, str]:
    """Delegate to Cursor for auto-fix via spec-based execution.

    Returns (success, message).
    """
    # Find the most recent auto-generated spec
    queue_dir = repo_root / ".cursor" / "delegation" / "queue"
    spec_files = sorted(queue_dir.glob("auto-*.md"), key=lambda p: p.stat().st_mtime)
    spec_path = spec_files[-1] if spec_files else None

    cmd = [str(repo_root / "scripts" / "cursor-delegate.sh"), "--yolo"]
    if spec_path:
        cmd.extend(["--spec", str(spec_path)])
    cmd.append(directive)

    code, stdout, stderr = _run_command(cmd, repo_root, timeout=300)
    output = stdout + stderr
    return code == 0, output


def _apply_quick_fixes(errors: list[str], repo_root: Path, tier: int) -> str:
    """Analyze errors and suggest known quick fixes.

    This is a diagnostic-only helper — it identifies the problem
    and returns a human-readable description, but does NOT modify
    files. Actual fixes are applied via Cursor delegation.

    Returns a description of what should be done.
    """
    fixes_applied = []

    for error in errors:
        error_lower = error.lower()

        # Python import fixes
        if "import" in error_lower and (
            "error" in error_lower or "module" in error_lower or "named" in error_lower
        ):
            # Try to identify missing import and add it
            match = re.search(r"no module named ['\"]([a-zA-Z_][a-zA-Z0-9_]*)['\"]", error_lower)
            if match:
                module = match.group(1)
                fixes_applied.append(f"Missing module: {module} (requires manual install)")

        # Ruff: unused import
        if "unused" in error_lower and ("import" in error_lower or "f401" in error_lower):
            match = re.search(
                r"([^:]+:\d+):\d+.*`([^`]+)`.*(?:imported but unused|unused import)",
                error,
            )
            if not match:
                # Try alternate format
                match = re.search(
                    r"([^:]+:\d+):\d+.*unused import [`\"']([^`'\"]+)[`\"']",
                    error,
                )
            if match:
                file_path = match.group(1)
                import_name = match.group(2)
                fixes_applied.append(f"Remove unused import `{import_name}` from {file_path}")

        # Ruff: undefined name
        if "undefined name" in error_lower or "f821" in error_lower:
            fixes_applied.append("Undefined name detected — needs manual fix")

        # Biome: unused variable
        if "unused" in error_lower and "biome" in error_lower:
            fixes_applied.append("Remove unused variable/parameter")

    if fixes_applied:
        return "; ".join(fixes_applied)
    return "No quick fixes applicable — requires Cursor delegation"


def auto_fix(
    directive: str,
    tier: int,
    max_attempts: int = MAX_ATTEMPTS,
    repo_root: Path | str = REPO_ROOT,
) -> FixResult:
    """Run auto-fix loop up to max_attempts.

    For each attempt:
    1. Run verification (pytest, ruff, npm build, npm lint)
    2. If all pass → done
    3. If errors → apply quick fixes or delegate to Cursor
    4. Re-run verification

    Args:
        directive: The original directive
        tier: Safety tier
        max_attempts: Max fix attempts
        repo_root: Repository root path

    Returns:
        FixResult with per-attempt details
    """
    repo_root = Path(repo_root)
    attempts = []
    overall_start = time.time()
    final_status = "failed"

    for attempt in range(1, max_attempts + 1):
        attempt_start = time.time()
        all_errors: list[str] = []

        # Run verifications based on tier
        if tier == 1:  # Frontend
            build_ok, build_errors = _run_npm_build(repo_root)
            lint_ok, lint_errors = _run_npm_lint(repo_root)
            test_ok: bool
            test_errors: list[str]
            test_ok, test_errors = True, []  # Frontend tests not in scope yet

            if not build_ok:
                all_errors.extend([f"[BUILD] {e}" for e in build_errors])
            if not lint_ok:
                all_errors.extend([f"[LINT] {e}" for e in lint_errors])

            all_passed = build_ok and lint_ok

        elif tier == 2:  # Pipeline
            test_ok, test_errors = _run_pytest(repo_root)
            lint_ok, lint_errors = _run_ruff(repo_root)

            if not test_ok:
                all_errors.extend([f"[TEST] {e}" for e in test_errors])
            if not lint_ok:
                all_errors.extend([f"[RUFF] {e}" for e in lint_errors])

            all_passed = test_ok and lint_ok
        else:
            all_passed = True
            all_errors = []

        if all_passed:
            attempts.append(
                FixAttempt(
                    attempt=attempt,
                    status="passed",
                    errors_found=[],
                    fix_applied="No fix needed — already clean",
                    duration_seconds=round(time.time() - attempt_start, 2),
                )
            )
            final_status = "fixed"
            break

        # Apply fix
        if attempt < max_attempts:
            fix_description = _apply_quick_fixes(all_errors, repo_root, tier)

            # If no quick fixes, try Cursor delegation
            if "No quick fixes" in fix_description:
                success, output = _run_cursor_delegate(directive, tier, repo_root)
                fix_description = f"Cursor delegation: {'success' if success else 'failed'}"

            attempts.append(
                FixAttempt(
                    attempt=attempt,
                    status="failed",
                    errors_found=all_errors[:10],
                    fix_applied=fix_description,
                    duration_seconds=round(time.time() - attempt_start, 2),
                )
            )
        else:
            # Last attempt — no fix applied, just record failure
            attempts.append(
                FixAttempt(
                    attempt=attempt,
                    status="failed",
                    errors_found=all_errors[:10],
                    fix_applied="Max attempts reached",
                    duration_seconds=round(time.time() - attempt_start, 2),
                )
            )
            final_status = "failed" if attempt == max_attempts else "partial"

    total_duration = round(time.time() - overall_start, 2)

    # Determine final status
    if any(a.status == "passed" for a in attempts):
        final_status = "fixed"
    elif attempts and attempts[-1].status == "failed" and len(attempts) < max_attempts:
        final_status = "partial"
    else:
        final_status = "failed"

    summary = (
        f"Auto-fix: {final_status.upper()} after {len(attempts)} attempt(s) "
        f"({sum(1 for a in attempts if a.status == 'passed')} passed, "
        f"{sum(1 for a in attempts if a.status == 'failed')} failed). "
        f"Duration: {total_duration}s"
    )

    return FixResult(
        directive=directive,
        max_attempts=max_attempts,
        attempts=[asdict(a) for a in attempts],
        final_status=final_status,
        summary=summary,
        total_duration_seconds=total_duration,
    )


def main() -> None:
    """CLI entrypoint for auto-fix."""
    if len(sys.argv) < 3:
        print(
            "Usage: python -m src.auto.fix '<directive>' <tier> "
            "[max_attempts] [repo_root]",
            file=sys.stderr,
        )
        sys.exit(1)

    directive = sys.argv[1]
    tier = int(sys.argv[2])
    max_attempts = int(sys.argv[3]) if len(sys.argv) > 3 else MAX_ATTEMPTS
    repo_root = Path(sys.argv[4]) if len(sys.argv) > 4 else REPO_ROOT

    result = auto_fix(directive, tier, max_attempts, repo_root)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
