"""Production readiness checks for Vercel and Prefect deployments.

Runs pre-deploy validation to catch issues before they reach production.

@agent_context: Auto-readiness for FX Regime Lab CEO Mode
@allowed_imports: [json, os, re, subprocess, sys, dataclasses, pathlib]
@forbidden_imports: [src.db, src.ai]
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str  # "pass", "fail", "warn", "skip"
    message: str
    detail: str | None = None


@dataclass(frozen=True)
class ReadinessResult:
    target: str
    overall: str  # "ready", "not_ready", "warning"
    checks: list[ReadinessCheck]
    summary: str


# Patterns that indicate secrets in build output
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenRouter, OpenAI keys
    re.compile(r"supabase.*key.*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"),
    re.compile(r"api[_-]?key.*[=:]\s*['\"]?[a-zA-Z0-9_-]{10,}", re.IGNORECASE),
    re.compile(r"secret.*[=:]\s*['\"]?[a-zA-Z0-9_-]{10,}", re.IGNORECASE),
    re.compile(r"token.*[=:]\s*['\"]?[a-zA-Z0-9_-]{10,}", re.IGNORECASE),
    re.compile(r"password.*[=:]\s*['\"]?[a-zA-Z0-9_-]{8,}", re.IGNORECASE),
]

# Console.log patterns in JS/TS build output
CONSOLE_PATTERNS = [
    re.compile(r"console\.(log|warn|error|debug|info|trace)\s*\("),
]

# Maximum acceptable bundle size increase (KB)
MAX_BUNDLE_DELTA_KB = 50


def _run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out after 120 seconds"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def _check_web_build(repo_root: Path) -> ReadinessCheck:
    """Check that the Next.js build succeeds."""
    web_dir = repo_root / "web"
    if not web_dir.exists():
        return ReadinessCheck(
            name="web_build",
            status="skip",
            message="web/ directory not found",
        )

    rc, stdout, stderr = _run_command(["npm", "run", "build"], cwd=web_dir)
    if rc != 0:
        return ReadinessCheck(
            name="web_build",
            status="fail",
            message="Next.js build failed",
            detail=(stderr or stdout)[:500],
        )

    return ReadinessCheck(
        name="web_build",
        status="pass",
        message="Next.js build succeeded",
    )


def _check_web_lint(repo_root: Path) -> ReadinessCheck:
    """Check that Biome lint passes."""
    web_dir = repo_root / "web"
    if not web_dir.exists():
        return ReadinessCheck(
            name="web_lint",
            status="skip",
            message="web/ directory not found",
        )

    rc, stdout, stderr = _run_command(["npx", "biome", "check", "."], cwd=web_dir)
    if rc != 0:
        return ReadinessCheck(
            name="web_lint",
            status="fail",
            message="Biome lint failed",
            detail=(stderr or stdout)[:500],
        )

    return ReadinessCheck(
        name="web_lint",
        status="pass",
        message="Biome lint clean",
    )


def _check_no_console_logs(repo_root: Path) -> ReadinessCheck:
    """Check for console.log statements in web source."""
    web_src = repo_root / "web" / "src"
    if not web_src.exists():
        return ReadinessCheck(
            name="no_console_logs",
            status="skip",
            message="web/src/ not found",
        )

    violations = []
    for pattern in CONSOLE_PATTERNS:
        for ext in (".ts", ".tsx", ".js", ".jsx"):
            for path in web_src.rglob(f"*{ext}"):
                content = path.read_text(encoding="utf-8", errors="ignore")
                for match in pattern.finditer(content):
                    line_num = content[: match.start()].count("\n") + 1
                    violations.append(f"{path.relative_to(repo_root)}:{line_num}")

    if violations:
        # Deduplicate and limit
        unique = list(dict.fromkeys(violations))[:10]
        return ReadinessCheck(
            name="no_console_logs",
            status="warn",
            message=f"Found {len(violations)} console.log statements",
            detail="; ".join(unique),
        )

    return ReadinessCheck(
        name="no_console_logs",
        status="pass",
        message="No console.log statements found",
    )


def _check_no_secrets_in_build(repo_root: Path) -> ReadinessCheck:
    """Check for secrets in build output or source."""
    web_dir = repo_root / "web"
    if not web_dir.exists():
        return ReadinessCheck(
            name="no_secrets",
            status="skip",
            message="web/ directory not found",
        )

    # Check .env files are gitignored
    gitignore = web_dir / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if ".env" not in content and ".env.local" not in content:
            return ReadinessCheck(
                name="no_secrets",
                status="warn",
                message=".env files may not be gitignored in web/",
            )

    # Check source files for hardcoded secrets
    web_src = web_dir / "src"
    violations = []
    if web_src.exists():
        for ext in (".ts", ".tsx", ".js", ".jsx"):
            for path in web_src.rglob(f"*{ext}"):
                content = path.read_text(encoding="utf-8", errors="ignore")
                for pattern in SECRET_PATTERNS:
                    for match in pattern.finditer(content):
                        line_num = content[: match.start()].count("\n") + 1
                        violations.append(f"{path.relative_to(repo_root)}:{line_num}")

    if violations:
        unique = list(dict.fromkeys(violations))[:10]
        return ReadinessCheck(
            name="no_secrets",
            status="fail",
            message=f"Found {len(violations)} potential secrets in source",
            detail="; ".join(unique),
        )

    return ReadinessCheck(
        name="no_secrets",
        status="pass",
        message="No hardcoded secrets detected",
    )


def _check_bundle_size(repo_root: Path) -> ReadinessCheck:
    """Check Next.js build output size."""
    next_dir = repo_root / "web" / ".next"
    if not next_dir.exists():
        return ReadinessCheck(
            name="bundle_size",
            status="skip",
            message="No .next build output found — run build first",
        )

    # Estimate size from static files
    static_dir = next_dir / "static"
    total_bytes = 0
    if static_dir.exists():
        for path in static_dir.rglob("*"):
            if path.is_file():
                total_bytes += path.stat().st_size

    total_kb = total_bytes / 1024
    # This is a rough heuristic — actual bundle analysis would use @next/bundle-analyzer
    if total_kb > 500:  # 500KB heuristic threshold
        return ReadinessCheck(
            name="bundle_size",
            status="warn",
            message=f"Static assets ~{total_kb:.0f}KB — review if unexpectedly large",
        )

    return ReadinessCheck(
        name="bundle_size",
        status="pass",
        message=f"Static assets ~{total_kb:.0f}KB — within bounds",
    )


def _check_pipeline_tests(repo_root: Path) -> ReadinessCheck:
    """Check that pytest passes."""
    pipeline_dir = repo_root / "pipeline"
    if not pipeline_dir.exists():
        return ReadinessCheck(
            name="pipeline_tests",
            status="skip",
            message="pipeline/ directory not found",
        )

    rc, stdout, stderr = _run_command(["pytest", "-q", "--tb=short"], cwd=pipeline_dir)
    if rc != 0:
        return ReadinessCheck(
            name="pipeline_tests",
            status="fail",
            message="pytest failed",
            detail=(stderr or stdout)[:500],
        )

    return ReadinessCheck(
        name="pipeline_tests",
        status="pass",
        message="pytest passed",
    )


def _check_pipeline_lint(repo_root: Path) -> ReadinessCheck:
    """Check that ruff passes."""
    pipeline_dir = repo_root / "pipeline"
    if not pipeline_dir.exists():
        return ReadinessCheck(
            name="pipeline_lint",
            status="skip",
            message="pipeline/ directory not found",
        )

    rc, stdout, stderr = _run_command(["ruff", "check", "."], cwd=pipeline_dir)
    if rc != 0:
        return ReadinessCheck(
            name="pipeline_lint",
            status="fail",
            message="ruff check failed",
            detail=(stderr or stdout)[:500],
        )

    return ReadinessCheck(
        name="pipeline_lint",
        status="pass",
        message="ruff check clean",
    )


def _check_prefect_env(repo_root: Path) -> ReadinessCheck:
    """Check that Prefect environment variables are set."""
    required = ["PREFECT_API_KEY", "PREFECT_API_URL"]
    missing = [var for var in required if not os.environ.get(var)]

    if missing:
        return ReadinessCheck(
            name="prefect_env",
            status="warn",
            message=f"Missing Prefect env vars: {', '.join(missing)}",
            detail="Prefect deploy may fail without these",
        )

    return ReadinessCheck(
        name="prefect_env",
        status="pass",
        message="Prefect environment variables present",
    )


def _check_supabase_env(repo_root: Path) -> ReadinessCheck:
    """Check that Supabase environment variables are set."""
    required = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
    missing = [var for var in required if not os.environ.get(var)]

    if missing:
        return ReadinessCheck(
            name="supabase_env",
            status="warn",
            message=f"Missing Supabase env vars: {', '.join(missing)}",
            detail="Database connectivity may fail",
        )

    return ReadinessCheck(
        name="supabase_env",
        status="pass",
        message="Supabase environment variables present",
    )


def check_vercel_readiness(repo_root: Path | str) -> ReadinessResult:
    """Run all readiness checks for a Vercel deployment."""
    repo_root = Path(repo_root)

    checks = [
        _check_web_build(repo_root),
        _check_web_lint(repo_root),
        _check_no_console_logs(repo_root),
        _check_no_secrets_in_build(repo_root),
        _check_bundle_size(repo_root),
    ]

    failures = [c for c in checks if c.status == "fail"]
    warnings = [c for c in checks if c.status == "warn"]

    if failures:
        overall = "not_ready"
        summary = (
            f"Vercel deploy NOT READY — {len(failures)} failure(s),"
            f" {len(warnings)} warning(s)"
        )
    elif warnings:
        overall = "warning"
        summary = (
            f"Vercel deploy READY WITH WARNINGS — {len(warnings)} warning(s)"
        )
    else:
        overall = "ready"
        summary = "Vercel deploy READY — all checks pass"

    return ReadinessResult(
        target="vercel",
        overall=overall,
        checks=checks,
        summary=summary,
    )


def check_prefect_readiness(repo_root: Path | str) -> ReadinessResult:
    """Run all readiness checks for a Prefect flow registration."""
    repo_root = Path(repo_root)

    checks = [
        _check_pipeline_tests(repo_root),
        _check_pipeline_lint(repo_root),
        _check_prefect_env(repo_root),
        _check_supabase_env(repo_root),
    ]

    failures = [c for c in checks if c.status == "fail"]
    warnings = [c for c in checks if c.status == "warn"]

    if failures:
        overall = "not_ready"
        summary = (
            f"Prefect deploy NOT READY — {len(failures)} failure(s),"
            f" {len(warnings)} warning(s)"
        )
    elif warnings:
        overall = "warning"
        summary = (
            f"Prefect deploy READY WITH WARNINGS — {len(warnings)} warning(s)"
        )
    else:
        overall = "ready"
        summary = "Prefect deploy READY — all checks pass"

    return ReadinessResult(
        target="prefect",
        overall=overall,
        checks=checks,
        summary=summary,
    )


def main() -> None:
    """CLI entrypoint for readiness checks."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.auto.readiness <vercel|prefect> [repo_root]", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1].lower()
    repo_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()

    if target == "vercel":
        result = check_vercel_readiness(repo_root)
    elif target == "prefect":
        result = check_prefect_readiness(repo_root)
    else:
        print(f"Unknown target: {target}. Use 'vercel' or 'prefect'.", file=sys.stderr)
        sys.exit(1)

    print(json.dumps({
        "target": result.target,
        "overall": result.overall,
        "summary": result.summary,
        "checks": [asdict(c) for c in result.checks],
    }, indent=2))

    sys.exit(0 if result.overall == "ready" else 1)


if __name__ == "__main__":
    main()
