"""Pipeline health dashboard backend.

Computes per-day pipeline health snapshots by querying Supabase tables
or inferring status from data presence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from src.db import writer

logger = logging.getLogger(__name__)

PAIRS_LOCKED = ("EURUSD", "USDJPY", "USDINR")


@dataclass
class PipelineHealthSnapshot:
    date: str
    status: str  # "HEALTHY", "DEGRADED", "FAILED"
    steps_completed: list[str]
    steps_failed: list[str]
    dqs_score: float | None
    regime_calls_count: int
    validation_stats_computed: bool
    ai_briefs_generated: bool
    macro_event_briefs_generated: bool
    errors: list[dict[str, Any]]
    duration_seconds: float | None


def _today_iso() -> str:
    return date.today().isoformat()


def _date_range_iso(n: int) -> list[str]:
    """Return the last ``n`` calendar-day ISO strings ending today."""
    base = date.today()
    return [(base - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


def _compute_status(
    steps_failed: list[str],
    errors: list[dict[str, Any]],
    dqs_score: float | None,
    signals_count: int,
    regime_calls_count: int,
) -> str:
    if steps_failed or errors:
        return "FAILED"
    if dqs_score is not None and dqs_score < 0.60:
        return "DEGRADED"
    if signals_count == 0 or regime_calls_count == 0:
        return "DEGRADED"
    return "HEALTHY"


def _infer_health_for_date(date_str: str) -> PipelineHealthSnapshot:
    """Infer health by probing data tables directly (no pipeline_runs row)."""
    steps_completed: list[str] = []
    steps_failed: list[str] = []
    errors: list[dict[str, Any]] = []

    try:
        signals_count = writer.count_signals_for_date(date_str)
        if signals_count > 0:
            steps_completed.append("signals")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check signals query failed for %s: %s", date_str, exc)
        steps_failed.append("signals")

    try:
        regime_calls_count = writer.count_regime_calls_for_date(date_str)
        if regime_calls_count > 0:
            steps_completed.append("regime_calls")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check regime_calls query failed for %s: %s", date_str, exc)
        steps_failed.append("regime_calls")

    dqs_scores: list[float] = []
    try:
        dqs_scores = writer.get_regime_calls_dqs_for_date(date_str)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check DQS query failed for %s: %s", date_str, exc)

    dqs_score = round(sum(dqs_scores) / len(dqs_scores), 4) if dqs_scores else None

    validation_stats_computed = False
    try:
        validation_stats_computed = writer.count_validation_log_for_date(date_str) > 0
        if validation_stats_computed:
            steps_completed.append("validation_log")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check validation_log query failed for %s: %s", date_str, exc)

    ai_briefs_generated = False
    try:
        ai_briefs_generated = writer.brief_log_exists_for_date(date_str)
        if ai_briefs_generated:
            steps_completed.append("brief_log")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check brief_log query failed for %s: %s", date_str, exc)

    macro_event_briefs_generated = False
    try:
        total_high, with_brief = writer.macro_events_with_ai_briefs_for_date(date_str)
        macro_event_briefs_generated = total_high == 0 or with_brief > 0
        if macro_event_briefs_generated:
            steps_completed.append("macro_event_briefs")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check macro_events query failed for %s: %s", date_str, exc)

    try:
        errors = writer.get_pipeline_errors_for_date(date_str)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Health check pipeline_errors query failed for %s: %s", date_str, exc)

    status = _compute_status(
        steps_failed=steps_failed,
        errors=errors,
        dqs_score=dqs_score,
        signals_count=signals_count if "signals" in steps_completed else 0,
        regime_calls_count=regime_calls_count if "regime_calls" in steps_completed else 0,
    )

    return PipelineHealthSnapshot(
        date=date_str,
        status=status,
        steps_completed=steps_completed,
        steps_failed=steps_failed,
        dqs_score=dqs_score,
        regime_calls_count=regime_calls_count if "regime_calls" in steps_completed else 0,
        validation_stats_computed=validation_stats_computed,
        ai_briefs_generated=ai_briefs_generated,
        macro_event_briefs_generated=macro_event_briefs_generated,
        errors=errors,
        duration_seconds=None,
    )


def _snapshot_from_db_row(row: dict[str, Any]) -> PipelineHealthSnapshot:
    """Convert a pipeline_runs DB row into a snapshot dataclass."""
    return PipelineHealthSnapshot(
        date=str(row.get("date", "")),
        status=str(row.get("status", "UNKNOWN")),
        steps_completed=list(row.get("steps_completed") or []),
        steps_failed=list(row.get("steps_failed") or []),
        dqs_score=float(row["dqs_score"]) if row.get("dqs_score") is not None else None,
        regime_calls_count=(
            int(row["regime_calls_count"]) if row.get("regime_calls_count") is not None else 0
        ),
        validation_stats_computed=bool(row.get("validation_stats_computed", False)),
        ai_briefs_generated=bool(row.get("ai_briefs_generated", False)),
        macro_event_briefs_generated=bool(row.get("macro_event_briefs_generated", False)),
        errors=list(row.get("errors") or []),
        duration_seconds=(
            float(row["duration_seconds"]) if row.get("duration_seconds") is not None else None
        ),
    )


def get_health_for_date(date_str: str) -> PipelineHealthSnapshot:
    """Return a detailed health snapshot for ``date_str``.

    Prefers an existing ``pipeline_runs`` row; falls back to inferring
    health from data presence in the relevant tables.
    """
    try:
        existing = writer.get_pipeline_run_for_date(date_str)
        if existing:
            return _snapshot_from_db_row(existing)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read pipeline_runs for %s: %s", date_str, exc)

    return _infer_health_for_date(date_str)


def get_last_n_days_health(n: int = 14) -> list[PipelineHealthSnapshot]:
    """Return health snapshots for the last ``n`` calendar days.

    Queries ``pipeline_runs`` first; missing days are inferred from
    data presence in the underlying tables.
    """
    days = _date_range_iso(n)
    start_iso, end_iso = days[0], days[-1]

    db_rows: dict[str, dict[str, Any]] = {}
    try:
        for row in writer.get_pipeline_runs_for_dates(start_iso, end_iso):
            d = str(row.get("date", ""))[:10]
            if d:
                db_rows[d] = row
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read pipeline_runs range: %s", exc)

    snapshots: list[PipelineHealthSnapshot] = []
    for d in days:
        if d in db_rows:
            snapshots.append(_snapshot_from_db_row(db_rows[d]))
        else:
            snapshots.append(_infer_health_for_date(d))
    return snapshots


def get_dqs_trend(n: int = 14) -> list[tuple[str, float | None]]:
    """Return the average Data Quality Score per day for the last ``n`` days.

    Computes a simple mean of ``data_quality_score`` from ``regime_calls``
    for each calendar date.
    """
    days = _date_range_iso(n)
    out: list[tuple[str, float | None]] = []
    for d in days:
        try:
            scores = writer.get_regime_calls_dqs_for_date(d)
            avg = round(sum(scores) / len(scores), 4) if scores else None
        except Exception as exc:  # noqa: BLE001
            logger.warning("DQS trend query failed for %s: %s", d, exc)
            avg = None
        out.append((d, avg))
    return out
