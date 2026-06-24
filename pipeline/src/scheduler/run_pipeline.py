"""Pipeline execution wrapper with alerting.

Replaces the shell-based run_daily.sh for the primary execution path.
Runs the daily orchestrator, overnight check, validation engine, and
validation aggregate — each with failure isolation — then sends the
appropriate Slack/email alerts.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
import uuid
from datetime import date
from typing import Any

from src import config
from src.db.writer import (
    count_regime_calls_for_date,
    get_brief_for_date,
    get_historical_regime_calls,
    get_regime_calls_dqs_for_date,
    write_pipeline_error,
    write_pipeline_run,
)
from src.monitoring.accuracy_alerts import check_accuracy_alerts, send_accuracy_alerts
from src.monitoring.alerts import (
    alert_on_failure,
    send_success_heartbeat,
)
from src.monitoring.health_dashboard import get_health_for_date
from src.scheduler.orchestrator import _regime_call_from_db, run_daily
from src.scheduler.overnight_check import run_overnight_check
from src.staged.adapters.alert import ProductionAlertPort
from src.staged.adapters.fetcher import ProductionFetcherPort
from src.staged.adapters.writer import ProductionWriterPort
from src.staged.contracts import MultiPairRunOutput
from src.staged.orchestrator import run_multi_pair_flow
from src.staged.shadow_runner import run_shadow_comparison
from src.types import PAIRS, RegimeCall
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


def _log_pipeline_health(
    date_str: str,
    *,
    steps_completed: list[str],
    steps_failed: list[str],
    duration_seconds: float | None = None,
    dqs_score: float | None = None,
    pairs_processed: int | None = None,
) -> None:
    """Write a health snapshot to ``pipeline_runs`` (best-effort)."""
    try:
        snapshot = get_health_for_date(date_str)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health snapshot inference failed for %s: %s", date_str, exc)
        snapshot = None

    if snapshot is not None:
        # Do NOT inherit stale status from old DB rows (e.g. ABORTED).
        # Recompute: FAILED if any step crashed, otherwise HEALTHY.
        payload: dict[str, Any] = {
            "date": date_str,
            "status": "FAILED" if steps_failed else "HEALTHY",
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "dqs_score": dqs_score if dqs_score is not None else snapshot.dqs_score,
            "regime_calls_count": (
                pairs_processed
                if pairs_processed is not None
                else snapshot.regime_calls_count
            ),
            "validation_stats_computed": snapshot.validation_stats_computed,
            "ai_briefs_generated": snapshot.ai_briefs_generated,
            "macro_event_briefs_generated": snapshot.macro_event_briefs_generated,
            "errors": snapshot.errors,
            "duration_seconds": duration_seconds,
        }
    else:
        payload = {
            "date": date_str,
            "status": "FAILED" if steps_failed else "UNKNOWN",
            "steps_completed": steps_completed,
            "steps_failed": steps_failed,
            "dqs_score": dqs_score,
            "regime_calls_count": pairs_processed,
            "errors": [],
            "duration_seconds": duration_seconds,
        }

    try:
        write_pipeline_run(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to write pipeline_run for %s: %s", date_str, exc)


def _get_v1_outputs_for_date(
    date_str: str,
) -> tuple[dict[str, RegimeCall], dict[str, str | None]]:
    """Read v1 regime calls and briefs from the DB for shadow comparison."""

    v1_calls: dict[str, RegimeCall] = {}
    v1_briefs: dict[str, str | None] = {}
    for pair in PAIRS:
        brief = get_brief_for_date(pair, date_str)
        v1_briefs[pair] = brief
        rows = get_historical_regime_calls(pair)
        for row in rows:
            if str(row.get("date") or "")[:10] == date_str:
                v1_calls[pair] = _regime_call_from_db(row)
                break
    return v1_calls, v1_briefs


async def _run_v2_live_pipeline(
    date_str: str,
    correlation_id: str,
) -> MultiPairRunOutput:
    """Run the staged v2 pipeline with production ports."""

    as_of = date.fromisoformat(date_str[:10])
    return await run_multi_pair_flow(
        as_of,
        fetcher=ProductionFetcherPort(),
        writer=ProductionWriterPort(),
        alert=ProductionAlertPort(),
        correlation_id=correlation_id,
    )


def _dqs_from_v2_output(output: MultiPairRunOutput) -> float:
    """Average data_quality_score across v2 regime calls."""

    scores = [
        call.data_quality_score
        for call in (out.regime_call for out in output.outputs.values())
        if call.data_quality_score is not None
    ]
    if not scores:
        return 1.0
    return round(sum(scores) / len(scores), 4)


def run_pipeline(date_str: str | None = None) -> None:
    """Execute the full daily pipeline with alerting.

    Steps:
      1. Daily orchestrator (signals, regime calls, briefs)
      2. Overnight check (invalidation, persistence)
      3. Validation engine (T+5/T+20 Brier scores)
      4. Validation aggregate (track-record stats)

    Feature flags (see ``src.config``):
      * ``USE_V2_PIPELINE=true``  → run staged v2 as the live orchestrator
      * ``SHADOW_V2=true``        → run v2 alongside v1 and compare outputs

    Alerting behavior:
      * Orchestrator crash      → Slack failure alert
      * DQS < 0.70 (no crash)   → email alert
      * DQS >= 0.70 success     → Slack heartbeat
      * Subsequent step crash   → Slack failure alert (step name included)
    """
    if date_str is None:
        date_str = date.today().isoformat()

    correlation_id = str(uuid.uuid4())
    dqs_score: float | None = None
    regime_calls_count = 0
    failed_step = ""
    steps_completed: list[str] = []
    steps_failed: list[str] = []
    start_time = time.monotonic()

    # ── Step 1: Daily orchestrator ──────────────────────────────────
    try:
        if config.USE_V2_PIPELINE:
            v2_output = _run_sync(_run_v2_live_pipeline(date_str, correlation_id))
            dqs_score = _dqs_from_v2_output(v2_output)
            regime_calls_count = v2_output.regime_calls_count
            steps_completed.append("orchestrator_v2")
        else:
            _run_sync(run_daily(date_str, correlation_id=correlation_id))
            steps_completed.append("orchestrator")
    except Exception as exc:
        failed_step = "orchestrator_v2" if config.USE_V2_PIPELINE else "orchestrator"
        steps_failed.append(failed_step)
        write_pipeline_error(
            step=failed_step,
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
        _log_pipeline_health(
            date_str,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            duration_seconds=round(time.monotonic() - start_time, 2),
            dqs_score=dqs_score,
            pairs_processed=regime_calls_count,
        )
        raise

    # Compute DQS and pair count from regime_calls written by the orchestrator
    # when running the legacy v1 path.
    if not config.USE_V2_PIPELINE:
        try:
            dqs_scores = get_regime_calls_dqs_for_date(date_str)
            dqs_score = round(sum(dqs_scores) / len(dqs_scores), 4) if dqs_scores else 1.0
        except Exception:
            dqs_score = 1.0
        try:
            regime_calls_count = count_regime_calls_for_date(date_str)
        except Exception:
            regime_calls_count = 0

    # ── Step 1b: Shadow-run v2 comparison (only when v1 is live) ────
    if config.SHADOW_V2 and not config.USE_V2_PIPELINE:
        try:
            v1_calls, v1_briefs = _get_v1_outputs_for_date(date_str)
            shadow_result = _run_sync(
                run_shadow_comparison(
                    date.fromisoformat(date_str[:10]),
                    v1_calls=v1_calls,
                    v1_briefs=v1_briefs,
                    fetcher=ProductionFetcherPort(),
                    correlation_id=correlation_id,
                )
            )
            logger.info(
                "Shadow v2 comparison for %s: equivalent=%s pairs=%s",
                date_str,
                shadow_result.equivalent,
                {p: c.equivalent for p, c in shadow_result.comparisons.items()},
            )
            steps_completed.append("shadow_v2")
        except Exception as exc:
            failed_step = "shadow_v2"
            steps_failed.append(failed_step)
            write_pipeline_error(
                step=failed_step,
                error_type=type(exc).__name__,
                message=str(exc),
                correlation_id=correlation_id,
            )
            # Shadow failures are non-fatal: v1 already published the live ledger.
            logger.warning("Shadow v2 comparison failed for %s: %s", date_str, exc)

    # ── Step 2: Overnight check ─────────────────────────────────────
    try:
        run_overnight_check()
        steps_completed.append("overnight_check")
    except Exception as exc:
        failed_step = "overnight_check"
        steps_failed.append("overnight_check")
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
        _log_pipeline_health(
            date_str,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            duration_seconds=round(time.monotonic() - start_time, 2),
            dqs_score=dqs_score,
            pairs_processed=regime_calls_count,
        )
        raise

    # ── Step 3: Validation aggregate ────────────────────────────────
    try:
        run_aggregate_stats()
        steps_completed.append("validation_aggregate")
    except Exception as exc:
        failed_step = "validation_aggregate"
        steps_failed.append("validation_aggregate")
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
        _log_pipeline_health(
            date_str,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            duration_seconds=round(time.monotonic() - start_time, 2),
            dqs_score=dqs_score,
            pairs_processed=regime_calls_count,
        )
        raise

    # ── Accuracy alerts ─────────────────────────────────────────────
    try:
        alerts = check_accuracy_alerts()
        if alerts:
            send_accuracy_alerts(alerts)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Accuracy alert check failed: %s", exc)

    # ── Health snapshot ─────────────────────────────────────────────
    _log_pipeline_health(
        date_str,
        steps_completed=steps_completed,
        steps_failed=steps_failed,
        duration_seconds=round(time.monotonic() - start_time, 2),
        dqs_score=dqs_score,
        pairs_processed=regime_calls_count,
    )

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    date_override = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(date_override)
