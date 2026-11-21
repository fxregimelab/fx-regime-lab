"""One scheduled entrypoint with recorded stage results and honest completion."""

from __future__ import annotations

import asyncio
import logging
import sys
import time
import uuid
from collections.abc import Coroutine, Sequence
from dataclasses import asdict
from datetime import date
from math import isfinite
from typing import Any, TypeVar

from prefect import flow

from src import config
from src.db.writer import (
    get_brief_for_date,
    get_current_live_regime_history,
    write_pipeline_error,
    write_pipeline_run,
)
from src.monitoring.accuracy_alerts import check_accuracy_alerts, send_accuracy_alerts
from src.monitoring.alerts import send_success_heartbeat
from src.scheduler.contracts import DailyRunOutput
from src.scheduler.orchestrator import _regime_call_from_db, run_daily
from src.scheduler.overnight_check import run_overnight_check
from src.staged.adapters.alert import ProductionAlertPort
from src.staged.adapters.fetcher import ProductionFetcherPort
from src.staged.adapters.writer import ProductionWriterPort
from src.staged.contracts import MultiPairRunOutput, StageHealth, combine_stage_health
from src.staged.orchestrator import run_multi_pair_flow
from src.staged.shadow_runner import run_shadow_comparison
from src.types import RegimeCall
from src.validation.aggregate import run_aggregate_stats

logger = logging.getLogger(__name__)
_T = TypeVar("_T")
_LOCKED_PAIRS = ("EURUSD", "USDJPY", "USDINR")


def _run_sync(coro: Coroutine[Any, Any, _T]) -> _T:
    """Bridge the synchronous scheduled flow to async inference."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    coro.close()
    raise RuntimeError("Use the synchronous pipeline entrypoint outside a running event loop")


def _log_pipeline_health(
    date_str: str,
    *,
    reports: Sequence[StageHealth],
    steps_completed: list[str],
    steps_failed: list[str],
    duration_seconds: float,
    dqs_score: float | None,
    pairs_processed: int | None,
) -> None:
    """Persist execution evidence; failure must prevent a healthy heartbeat."""
    health = combine_stage_health("DailyPipeline", *reports)
    write_pipeline_run(
        {
            "date": date_str,
            "status": "HEALTHY" if health.status == "OK" else health.status,
            "steps_completed": list(steps_completed),
            "steps_failed": list(steps_failed),
            "dqs_score": dqs_score,
            "regime_calls_count": pairs_processed,
            "validation_stats_computed": any(
                report.stage_name == "validation_aggregate" and report.status == "OK"
                for report in reports
            ),
            "ai_briefs_generated": None,
            "macro_event_briefs_generated": None,
            "errors": [asdict(report) for report in reports if report.status != "OK"],
            "duration_seconds": duration_seconds,
        }
    )


def _get_v1_outputs_for_date(
    date_str: str,
) -> tuple[dict[str, RegimeCall], dict[str, str | None]]:
    """Read v1 regime calls and briefs from the DB for shadow comparison."""

    v1_calls: dict[str, RegimeCall] = {}
    v1_briefs: dict[str, str | None] = {}
    for pair in _LOCKED_PAIRS:
        brief = get_brief_for_date(pair, date_str)
        v1_briefs[pair] = brief
        rows = get_current_live_regime_history(pair, as_of=date_str, session_limit=1)
        if rows and str(rows[0].get("date") or "")[:10] == date_str:
            v1_calls[pair] = _regime_call_from_db(rows[0])
    return v1_calls, v1_briefs


async def _run_v2_live_pipeline(
    date_str: str,
    correlation_id: str,
) -> MultiPairRunOutput:
    return await run_multi_pair_flow(
        date.fromisoformat(date_str),
        fetcher=ProductionFetcherPort(),
        writer=ProductionWriterPort(),
        alert=ProductionAlertPort(),
        correlation_id=correlation_id,
        send_run_status=False,
    )


def _complete_dqs(scores: Sequence[float | None]) -> float | None:
    if not scores or any(s is None or not isfinite(s) or not 0 <= s <= 1 for s in scores):
        return None
    return round(sum(s for s in scores if s is not None) / len(scores), 4)


def _dqs_from_v2_output(output: MultiPairRunOutput) -> float | None:
    return _complete_dqs([out.regime_call.data_quality_score for out in output.outputs.values()])


def _require_validation_evidence(reports: Sequence[StageHealth]) -> None:
    validation = [report for report in reports if report.stage_name == "ValidateStage"]
    if (
        len(validation) != 1
        or validation[0].status not in ("OK", "DEGRADED")
        or "validation_scan_completed" not in validation[0].notes
        or "validation_not_run" in validation[0].notes
    ):
        raise RuntimeError("Daily inference returned without completed validation evidence")


@flow(name="FX Regime Lab scheduled pipeline", log_prints=True, timeout_seconds=2400)
def run_pipeline(date_str: str | None = None) -> StageHealth:
    """Run live inference, validation, overnight checks and aggregation exactly once.

    Shadow comparison is optional and cannot alter the live ledger. Its failures
    remain visible as degradation. Required-stage failures reach Prefect unchanged.
    """
    as_of = date.fromisoformat(date_str) if date_str is not None else date.today()
    date_str = as_of.isoformat()
    correlation_id = str(uuid.uuid4())
    started = time.monotonic()
    reports: list[StageHealth] = []
    completed: list[str] = []
    failed: list[str] = []
    dqs: float | None = None
    published_pairs: tuple[str, ...] | None = None
    stage = "orchestrator_v2" if config.USE_V2_PIPELINE else "orchestrator"

    def record_health() -> None:
        _log_pipeline_health(
            date_str,
            reports=reports,
            steps_completed=completed,
            steps_failed=failed,
            duration_seconds=round(time.monotonic() - started, 2),
            dqs_score=dqs,
            pairs_processed=len(published_pairs) if published_pairs is not None else None,
        )

    try:
        if config.USE_V2_PIPELINE:
            output = _run_sync(_run_v2_live_pipeline(date_str, correlation_id))
            if not isinstance(output, MultiPairRunOutput) or output.date != as_of:
                raise RuntimeError("Staged run returned invalid execution evidence")
            if any(
                (p, out.date, out.regime_call.pair, out.regime_call.date)
                != (out.pair, as_of, p, as_of)
                for p, out in output.outputs.items()
            ):
                raise RuntimeError("Staged publication identity mismatch")
            published_pairs = tuple(output.outputs)
            if output.pairs_processed != len(published_pairs) or output.regime_calls_count != len(
                published_pairs
            ):
                raise RuntimeError("Staged publication counts disagree with outputs")
            dqs = _dqs_from_v2_output(output)
            inference_health = combine_stage_health(
                "Inference",
                output.health,
                *(out.health for out in output.outputs.values()),
                *output.stage_health,
            )
            validation_reports = output.stage_health
        else:
            legacy = _run_sync(run_daily(date_str, correlation_id=correlation_id))
            if not isinstance(legacy, DailyRunOutput) or legacy.date != date_str:
                raise RuntimeError("Legacy run returned invalid execution evidence")
            published_pairs = legacy.published_pairs
            dqs = _complete_dqs([legacy.dqs_score])
            inference_health = combine_stage_health(
                "Inference", legacy.health, *legacy.stage_health
            )
            validation_reports = legacy.stage_health
        reports.append(inference_health)
        if inference_health.status == "FAILED":
            raise RuntimeError("Daily inference reported FAILED")
        _require_validation_evidence(validation_reports)
        if len(set(published_pairs)) != len(published_pairs) or set(published_pairs) - set(
            _LOCKED_PAIRS
        ):
            raise RuntimeError("Published pair identities violate the locked universe")
        completed.extend([stage, "validation"])
        missing = sorted(set(_LOCKED_PAIRS) - set(published_pairs))
        reports.append(
            StageHealth(
                "PublicationCoverage", "DEGRADED" if missing else "OK", missing_fields=missing
            )
        )
        reports.append(
            StageHealth(
                "DataQuality",
                "DEGRADED" if dqs is None or dqs < 0.75 else "OK",
                notes=["quality_unavailable_or_low"] if dqs is None or dqs < 0.75 else [],
            )
        )

        if config.SHADOW_V2 and not config.USE_V2_PIPELINE:
            try:
                calls, briefs = _get_v1_outputs_for_date(date_str)
                shadow = _run_sync(
                    run_shadow_comparison(
                        as_of,
                        v1_calls=calls,
                        v1_briefs=briefs,
                        fetcher=ProductionFetcherPort(),
                        correlation_id=correlation_id,
                    )
                )
                reports.append(
                    StageHealth(
                        "shadow_v2",
                        "OK" if shadow.equivalent else "DEGRADED",
                        notes=[] if shadow.equivalent else ["output_divergence"],
                    )
                )
                completed.append("shadow_v2")
            except Exception as exc:
                reports.append(StageHealth("shadow_v2", "DEGRADED", notes=[type(exc).__name__]))

        stage = "overnight_check"
        overnight = run_overnight_check(as_of=as_of)
        if not isinstance(overnight, StageHealth):
            raise RuntimeError("Overnight check returned no execution evidence")
        reports.append(overnight)
        if overnight.status == "FAILED":
            raise RuntimeError("Overnight check reported FAILED")
        completed.append(stage)

        stage = "validation_aggregate"
        aggregates = run_aggregate_stats(as_of_date=as_of)
        reports.append(
            StageHealth(
                stage,
                "OK" if aggregates else "DEGRADED",
                notes=[] if aggregates else ["no_aggregate_rows"],
            )
        )
        completed.append(stage)

        if as_of == date.today():
            try:
                alerts = check_accuracy_alerts()
                if alerts:
                    send_accuracy_alerts(alerts)
            except Exception as exc:
                reports.append(
                    StageHealth("accuracy_alerts", "DEGRADED", notes=[type(exc).__name__])
                )

        stage = "health_record"
        record_health()
        completed.append(stage)
    except Exception as exc:
        failed.append(stage)
        reports.append(StageHealth(stage, "FAILED", notes=[type(exc).__name__]))
        # Secondary diagnostics must not replace the required-stage exception.
        try:
            write_pipeline_error(
                step=stage,
                error_type=type(exc).__name__,
                message="Required pipeline stage failed; inspect run logs",
                correlation_id=correlation_id,
            )
        except Exception as diagnostic_error:
            logger.warning("Failure diagnostic write failed: %s", type(diagnostic_error).__name__)
        try:
            record_health()
        except Exception as diagnostic_error:
            logger.warning("Failure health write failed: %s", type(diagnostic_error).__name__)
        try:
            ProductionAlertPort().send_status(
                as_of, combine_stage_health("DailyPipeline", *reports)
            )
        except Exception as diagnostic_error:
            logger.warning("Failure notice failed: %s", type(diagnostic_error).__name__)
        raise

    health = combine_stage_health("DailyPipeline", *reports)
    assert published_pairs is not None
    if health.status == "OK":
        assert dqs is not None
        send_success_heartbeat(
            date_str=date_str,
            pairs_processed=len(published_pairs),
            regime_calls_count=len(published_pairs),
            dqs_score=dqs,
        )
    else:
        ProductionAlertPort().send_status(as_of, health)
    logger.info("Pipeline execution finished for %s: %s", date_str, health.status)
    return health


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline(sys.argv[1] if len(sys.argv) > 1 else None)
