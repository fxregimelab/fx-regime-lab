"""Post-deploy self-healing engine.

After deployment, monitors health and auto-recovers from failures
by generating fix specs and re-delegating to Cursor.

Max 3 attempts. Escalates to human after max.

@agent_context: Auto-heal for FX Regime Lab CEO Mode
@allowed_imports: [json, os, subprocess, sys, dataclasses, time, pathlib]
@forbidden_imports: [src.db, src.ai]
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.auto.fix import auto_fix
from src.auto.monitor import monitor_prefect, monitor_vercel

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class HealAttempt:
    attempt: int
    monitor_status: str
    monitor_failures: list[str]
    fix_status: str
    fix_summary: str
    duration_seconds: float


@dataclass(frozen=True)
class HealResult:
    directive: str
    tier: int
    max_attempts: int
    attempts: list[dict[str, Any]]
    final_monitor_status: str
    final_status: str  # "healthy" | "recovered" | "failed"
    summary: str
    total_duration_seconds: float


def _run_monitor(target: str, url: str | None = None) -> tuple[str, list[str]]:
    """Run monitor and return (overall_status, list_of_failure_messages)."""
    try:
        if target == "vercel":
            if not url:
                return "unhealthy", ["No URL provided for Vercel monitoring"]
            result = monitor_vercel(url)
        elif target == "prefect":
            result = monitor_prefect()
        else:
            return "unhealthy", [f"Unknown monitor target: {target}"]

        failures = [
            f"{c.name}: {c.message}"
            for c in result.checks
            if c.status == "fail"
        ]
        return result.overall, failures
    except Exception as e:
        return "unhealthy", [f"Monitor exception: {e}"]


def self_heal(
    directive: str,
    tier: int,
    deploy_target: str,
    deploy_url: str | None,
    max_attempts: int = 3,
    repo_root: Path | str = REPO_ROOT,
) -> HealResult:
    """Monitor deployed service and auto-heal if unhealthy.

    Args:
        directive: Original directive
        tier: Safety tier
        deploy_target: "vercel" or "prefect"
        deploy_url: Deployed URL (for Vercel)
        max_attempts: Max heal attempts
        repo_root: Repository root path

    Returns:
        HealResult with per-attempt details and final status
    """
    repo_root = Path(repo_root)
    attempts = []
    overall_start = time.time()

    for attempt in range(1, max_attempts + 1):
        attempt_start = time.time()

        # Run monitor
        monitor_status, failures = _run_monitor(deploy_target, deploy_url)

        if monitor_status == "healthy":
            attempts.append(
                HealAttempt(
                    attempt=attempt,
                    monitor_status=monitor_status,
                    monitor_failures=[],
                    fix_status="skipped",
                    fix_summary="No fix needed — monitor healthy",
                    duration_seconds=round(time.time() - attempt_start, 2),
                )
            )
            final_status = "healthy" if attempt == 1 else "recovered"
            break

        # Monitor is unhealthy — try to fix
        if attempt < max_attempts:
            fix_result = auto_fix(
                f"{directive} [deploy-heal attempt {attempt}]",
                tier,
                max_attempts=1,
                repo_root=repo_root,
            )
            fix_status = fix_result.final_status
            fix_summary = fix_result.summary

            attempts.append(
                HealAttempt(
                    attempt=attempt,
                    monitor_status=monitor_status,
                    monitor_failures=failures[:5],
                    fix_status=fix_status,
                    fix_summary=fix_summary,
                    duration_seconds=round(time.time() - attempt_start, 2),
                )
            )
        else:
            # Last attempt — no fix, just record
            attempts.append(
                HealAttempt(
                    attempt=attempt,
                    monitor_status=monitor_status,
                    monitor_failures=failures[:5],
                    fix_status="failed",
                    fix_summary="Max attempts reached",
                    duration_seconds=round(time.time() - attempt_start, 2),
                )
            )
            final_status = "failed"

    total_duration = round(time.time() - overall_start, 2)

    if final_status == "healthy":
        summary = f"Monitor healthy on first check — no healing needed ({total_duration}s)"
    elif final_status == "recovered":
        summary = (
            f"Self-heal RECOVERED after {len(attempts)} attempt(s) "
            f"({sum(1 for a in attempts if a.monitor_status != 'healthy')} failures fixed). "
            f"Duration: {total_duration}s"
        )
    else:
        summary = (
            f"Self-heal FAILED after {len(attempts)} attempt(s). "
            f"Duration: {total_duration}s. "
            f"Escalate to human."
        )

    return HealResult(
        directive=directive,
        tier=tier,
        max_attempts=max_attempts,
        attempts=[asdict(a) for a in attempts],
        final_monitor_status=attempts[-1].monitor_status,
        final_status=final_status,
        summary=summary,
        total_duration_seconds=total_duration,
    )


def main() -> None:
    """CLI entrypoint for self-heal."""
    if len(sys.argv) < 4:
        print(
            "Usage: python -m src.auto.self_heal "
            "'<directive>' <tier> <vercel|prefect> [deploy_url] [max_attempts] [repo_root]",
            file=sys.stderr,
        )
        sys.exit(1)

    directive = sys.argv[1]
    tier = int(sys.argv[2])
    target = sys.argv[3]
    url = sys.argv[4] if len(sys.argv) > 4 else None
    max_attempts = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    repo_root = Path(sys.argv[6]) if len(sys.argv) > 6 else REPO_ROOT

    result = self_heal(directive, tier, target, url, max_attempts, repo_root)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
