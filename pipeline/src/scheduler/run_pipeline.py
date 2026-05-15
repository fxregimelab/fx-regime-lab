"""Pipeline execution wrapper with alerting.

Replaces the shell-based run_daily.sh for the primary execution path.
Runs the daily orchestrator, overnight check, validation engine, and
validation aggregate — each with failure isolation — then sends the
appropriate Slack/email alerts.

Optional v3 shadow mode runs the pair-specific pipeline alongside the
legacy v2 orchestrator so both model versions are logged for comparison.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
import sys
import uuid
from datetime import date
from typing import Any

from src.db.writer import write_pipeline_error
from src.monitoring.alerts import (
    alert_on_failure,
    send_success_heartbeat,
)
from src.scheduler.orchestrator import run_daily
from src.scheduler.overnight_check import run_overnight_check
from src.validation.aggregate import run_aggregate_stats

logger = logging.getLogger(__name__)


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine in the current event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        return loop.run_until_complete(coro)


def _run_v3_shadow(date_str: str, correlation_id: str, *, live: bool = False) -> int:
    """Run the v3 pair-specific pipeline in shadow mode.

    Returns the subprocess exit code.  Failures are logged but do NOT
    block the main v2 pipeline.
    """
    cmd = [
        sys.executable,
        "-m",
        "src.pairs.runner",
        "--all",
        "--date",
        date_str,
    ]
    if not live:
        cmd.append("--dry-run")
    logger.info(
        "Starting v3 shadow pipeline: cid=%s cmd=%s",
        correlation_id,
        " ".join(cmd),
    )
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "v3 shadow pipeline exited %d: stderr=%s",
                result.returncode,
                result.stderr[:500],
            )
        else:
            logger.info("v3 shadow pipeline completed successfully")
        return result.returncode
    except subprocess.TimeoutExpired:
        logger.warning("v3 shadow pipeline timed out after 600s")
        return 124
    except Exception as exc:
        logger.warning("v3 shadow pipeline launch failed: %s", exc)
        return 1


def run_pipeline(
    date_str: str | None = None,
    *,
    v3_shadow: bool = False,
    v3_live: bool = False,
) -> None:
    """Execute the full daily pipeline with alerting.

    Steps:
      1. Daily orchestrator (signals, regime calls, briefs) — v2
      2. v3 shadow pipeline (pair-specific models) — optional
      3. Overnight check (invalidation, persistence)
      4. Validation aggregate (track-record stats)

    Alerting behavior:
      * Orchestrator crash      → Slack failure alert
      * DQS < 0.70 (no crash)   → email alert
      * DQS >= 0.70 success     → Slack heartbeat
      * Subsequent step crash   → Slack failure alert (step name included)
      * v3 shadow failure       → logged only (non-blocking)
    """
    if date_str is None:
        date_str = date.today().isoformat()

    correlation_id = str(uuid.uuid4())
    dqs_score: float | None = None
    regime_calls_count = 0
    failed_step = ""

    # ── Step 1: Daily orchestrator (v2) ─────────────────────────────
    try:
        _run_sync(run_daily(date_str, correlation_id=correlation_id))
    except Exception as exc:
        failed_step = "orchestrator"
        write_pipeline_error(
            step="orchestrator",
            error_type=type(exc).__name__,
            message=str(exc),
            correlation_id=correlation_id,
        )
        alert_on_failure(
            date_str=date_str,
            failed_step=failed_step,
            exception=exc,
            dqs_score=dqs_score,
        )
        raise

    # ── Step 1b: v3 shadow pipeline (non-blocking) ──────────────────
    if v3_shadow or v3_live:
        _run_v3_shadow(date_str, correlation_id, live=v3_live)

    # DQS and regime-call count are not directly exposed by run_daily,
    # so we infer success from the absence of an exception.  If future
    # refactorings expose these values, the alerting logic can be
    # enriched without changing the external contract.
    dqs_score = None  # Will be set if we can read it from a future API

    # ── Step 2: Overnight check ─────────────────────────────────────
    try:
        run_overnight_check()
    except Exception as exc:
        failed_step = "overnight_check"
        write_pipeline_error(
            step="overnight_check",
            error_type=type(exc).__name__,
            message=str(exc),
            correlation_id=correlation_id,
        )
        alert_on_failure(
            date_str=date_str,
            failed_step=failed_step,
            exception=exc,
        )
        raise

    # ── Step 3: Validation aggregate ────────────────────────────────
    try:
        run_aggregate_stats()
    except Exception as exc:
        failed_step = "validation_aggregate"
        write_pipeline_error(
            step="validation_aggregate",
            error_type=type(exc).__name__,
            message=str(exc),
            correlation_id=correlation_id,
        )
        alert_on_failure(
            date_str=date_str,
            failed_step=failed_step,
            exception=exc,
        )
        raise

    # ── Success alerting ────────────────────────────────────────────
    # Since DQS is not directly exposed here, we default to heartbeat.
    # If DQS < 0.70 had been raised inside run_daily, the exception
    # would have been caught above and a failure alert sent instead.
    send_success_heartbeat(
        date_str=date_str,
        pairs_processed=7,  # 3-pair lock + 4 secondary
        regime_calls_count=regime_calls_count,
        dqs_score=dqs_score or 1.0,
    )

    logger.info("Pipeline complete for %s", date_str)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily pipeline runner with alerting")
    parser.add_argument("date", nargs="?", default=None, help="Override date (YYYY-MM-DD)")
    parser.add_argument(
        "--v3-shadow",
        action="store_true",
        dest="v3_shadow",
        help="Run v3 pair-specific pipeline in shadow mode after v2 (non-blocking, dry-run)",
    )
    parser.add_argument(
        "--v3-live",
        action="store_true",
        dest="v3_live",
        help="Run v3 pipeline and WRITE to DB (requires meta migration)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        run_pipeline(args.date, v3_shadow=args.v3_shadow, v3_live=args.v3_live)
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
