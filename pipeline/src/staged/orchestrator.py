"""Staged pipeline orchestrator flows."""

from __future__ import annotations

import datetime
import logging
from collections.abc import Sequence
from typing import Any

from prefect import flow, task

from src.core.price_archive_stage import (
    PriceArchiveStageResult,
    archive_price_snapshot,
)
from src.staged.contracts import (
    IngestionSnapshot,
    MultiPairRunOutput,
    PublishOutput,
    SignalPipelineResult,
    StageHealth,
    combine_stage_health,
)
from src.staged.ports import AlertPort, FetcherPort, WriterPort
from src.staged.stages import (
    IngestionStage,
    PublishStage,
    RegimeStage,
    SignalStage,
    ValidateStage,
)
from src.types import RegimeCall, SignalRow, SpotBar
from src.validation.coverage import ValidationRunResult

logger = logging.getLogger(__name__)

_ALLOWED_PAIRS: frozenset[str] = frozenset({"EURUSD", "USDJPY", "USDINR"})
_DEFAULT_PAIR_ORDER: tuple[str, ...] = ("EURUSD", "USDJPY", "USDINR")

# Shared retry policy for stage boundaries: two attempts with a short delay
# to retry transient failures. Signal and call writes are not yet atomic.
_STAGE_RETRIES = 2
_STAGE_RETRY_DELAY_SECONDS = 30


@flow(name="single-pair-regime-flow")
async def run_single_pair_flow(
    pair: str,
    as_of: datetime.date,
    *,
    fetcher: FetcherPort,
    writer: WriterPort,
    alert: AlertPort,
    correlation_id: str | None = None,
) -> PublishOutput:
    """Run the staged pipeline for a single pair.

    The flow composes Ingestion → Signal → Regime → Publish. Validation is
    intentionally date-scoped and is expected to be invoked by a parent flow
    after all pairs have been published.
    """

    if pair not in _ALLOWED_PAIRS:
        raise ValueError(f"Pair {pair!r} is not in the allowed universe {_ALLOWED_PAIRS}")

    cid = correlation_id or _new_correlation_id()

    try:
        snapshot = await _ingestion_task(fetcher, as_of)
        _require_snapshot(snapshot, as_of)
    except Exception as exc:
        _report_stage_failure(alert, as_of, "IngestionStage", exc, pair=pair)
        raise
    try:
        archive_result = _archive_price_task(
            writer,
            {pair: snapshot.spots.get(pair, ())},
            as_of,
            datetime.datetime.now(datetime.UTC),
        )
        archive_health = _price_archive_health(archive_result)
    except Exception as exc:
        _report_stage_failure(alert, as_of, "PriceArchiveStage", exc, pair=pair)
        raise
    return await _run_pair_pipeline(
        pair=pair,
        snapshot=snapshot,
        writer=writer,
        alert=alert,
        correlation_id=cid,
        archive_health=archive_health,
    )


@flow(name="multi-pair-regime-flow")
async def run_multi_pair_flow(
    as_of: datetime.date,
    *,
    fetcher: FetcherPort,
    writer: WriterPort,
    alert: AlertPort,
    pairs: Sequence[str] | None = None,
    correlation_id: str | None = None,
    run_validation: bool = True,
    send_run_status: bool = True,
) -> MultiPairRunOutput:
    """Run the staged pipeline for all locked pairs on ``as_of``.

    Ingestion is date-scoped and executed once. Signal, Regime, and Publish
    run per pair so that a non-critical degradation for one pair does not
    prevent the others from publishing. Validation is date-scoped and runs
    after all pairs have been published.
    """

    requested_pairs = pairs if pairs is not None else _DEFAULT_PAIR_ORDER
    disallowed = [p for p in requested_pairs if p not in _ALLOWED_PAIRS]
    if disallowed:
        raise ValueError(f"Pairs {disallowed!r} are not in the allowed universe {_ALLOWED_PAIRS}")

    if not requested_pairs or len(set(requested_pairs)) != len(requested_pairs):
        raise ValueError("Requested pairs must be nonempty and unique")
    cid = correlation_id or _new_correlation_id()

    try:
        snapshot = await _ingestion_task(fetcher, as_of)
        _require_snapshot(snapshot, as_of)
    except Exception as exc:
        _report_stage_failure(alert, as_of, "IngestionStage", exc)
        raise

    try:
        archive_result = _archive_price_task(
            writer,
            {pair: snapshot.spots.get(pair, ()) for pair in requested_pairs},
            as_of,
            datetime.datetime.now(datetime.UTC),
        )
        archive_health = _price_archive_health(archive_result)
    except Exception as exc:
        _report_stage_failure(alert, as_of, "PriceArchiveStage", exc)
        raise

    outputs: dict[str, PublishOutput] = {}
    for pair in requested_pairs:
        outputs[pair] = await _run_pair_pipeline(
            pair=pair,
            snapshot=snapshot,
            writer=writer,
            alert=alert,
            correlation_id=cid,
            archive_health=archive_health,
        )

    validation_rows: list[dict[str, Any]] = []
    validation_health = StageHealth("ValidateStage", "DEGRADED", notes=["validation_not_run"])
    if run_validation:
        try:
            validation_result = _validate_task(
                as_of,
                list(requested_pairs),
                writer,
                snapshot,
            )
            validation_health = _validation_health(validation_result)
            if isinstance(validation_result, ValidationRunResult):
                validation_rows = validation_result.rows
        except Exception as exc:
            _report_stage_failure(alert, as_of, "ValidateStage", exc)
            raise

    overall_health = _overall_health(snapshot, archive_health, outputs, validation_health)
    if send_run_status:
        if overall_health.status == "OK":
            assert snapshot.dqs_score is not None
            alert.send_heartbeat(
                as_of,
                pairs_processed=len(outputs),
                regime_calls_count=len(outputs),
                dqs_score=snapshot.dqs_score,
            )
        else:
            alert.send_status(as_of, overall_health)

    return MultiPairRunOutput(
        date=as_of,
        outputs=outputs,
        validation_rows=validation_rows,
        health=overall_health,
        pairs_processed=len(outputs),
        regime_calls_count=len(outputs),
        stage_health=(
            snapshot.health,
            archive_health,
            *(o.health for o in outputs.values()),
            validation_health,
        ),
    )


async def _run_pair_pipeline(
    *,
    pair: str,
    snapshot: IngestionSnapshot,
    writer: WriterPort,
    alert: AlertPort,
    correlation_id: str | None,
    archive_health: StageHealth,
) -> PublishOutput:
    """Run Signal → Regime → Publish for a single pair.

    Each stage call has bounded Prefect retries. Persistence atomicity is
    handled separately from this orchestration contract.
    """

    stage = "SignalStage"
    try:
        if not snapshot.spots.get(pair):
            raise ValueError(f"No spot history for {pair}")
        signal_result = _signal_task(pair, snapshot)
        if signal_result.health.status == "FAILED":
            raise ValueError("Signal stage reported FAILED")
        if (signal_result.pair, signal_result.date) != (pair, snapshot.date):
            raise ValueError("Signal result identity differs from requested snapshot")
        stage = "RegimeStage"
        regime_call = _regime_task(pair, signal_result)
        stage = "PublishStage"
        return await _publish_task(
            pair,
            regime_call,
            writer,
            alert,
            correlation_id,
            signal_result.signal_row,
            (snapshot.health, archive_health, signal_result.health),
        )
    except Exception as exc:
        _report_stage_failure(alert, snapshot.date, stage, exc, pair=pair)
        raise


@task(retries=_STAGE_RETRIES, retry_delay_seconds=_STAGE_RETRY_DELAY_SECONDS)
async def _ingestion_task(
    fetcher: FetcherPort,
    as_of: datetime.date,
) -> IngestionSnapshot:
    """Prefect task wrapper around ``IngestionStage.run``."""

    return await IngestionStage(fetcher).run(as_of)


@task(retries=_STAGE_RETRIES, retry_delay_seconds=_STAGE_RETRY_DELAY_SECONDS)
def _archive_price_task(
    writer: WriterPort,
    spots: dict[str, Sequence[SpotBar]],
    as_of: datetime.date,
    cutoff: datetime.datetime,
) -> PriceArchiveStageResult:
    """Archive one date-scoped snapshot before any pair publication."""

    return archive_price_snapshot(spots, as_of=as_of, cutoff=cutoff, writer=writer)


@task(retries=_STAGE_RETRIES, retry_delay_seconds=_STAGE_RETRY_DELAY_SECONDS)
def _signal_task(
    pair: str,
    snapshot: IngestionSnapshot,
) -> SignalPipelineResult:
    """Prefect task wrapper around ``SignalStage.run``."""

    return SignalStage().run(pair, snapshot)


@task(retries=_STAGE_RETRIES, retry_delay_seconds=_STAGE_RETRY_DELAY_SECONDS)
def _regime_task(
    pair: str,
    signal_result: SignalPipelineResult,
) -> RegimeCall:
    """Prefect task wrapper around ``RegimeStage.run``."""

    return RegimeStage().run(pair, signal_result)


@task(retries=_STAGE_RETRIES, retry_delay_seconds=_STAGE_RETRY_DELAY_SECONDS)
async def _publish_task(
    pair: str,
    regime_call: RegimeCall,
    writer: WriterPort,
    alert: AlertPort,
    correlation_id: str | None,
    signal_row: SignalRow,
    upstream_health: Sequence[StageHealth],
) -> PublishOutput:
    """Prefect task wrapper around ``PublishStage.run``."""

    return await PublishStage(writer, alert, correlation_id=correlation_id).run(
        pair, regime_call, signal_row=signal_row, upstream_health=upstream_health
    )


@task(retries=_STAGE_RETRIES, retry_delay_seconds=_STAGE_RETRY_DELAY_SECONDS)
def _validate_task(
    as_of: datetime.date,
    pairs: list[str],
    writer: WriterPort,
    snapshot: IngestionSnapshot,
) -> ValidationRunResult:
    """Prefect task wrapper around the complete validation coverage report."""

    return ValidateStage(writer).run_with_report(as_of, pairs, snapshot=snapshot)


def _validation_health(result: object) -> StageHealth:
    """Require a typed coverage report before claiming validation completion."""

    if not isinstance(result, ValidationRunResult):
        return StageHealth(
            "ValidateStage",
            "DEGRADED",
            missing_fields=["validation_report"],
            notes=["validation_report_unavailable"],
        )
    missing_fields: list[str] = []
    if result.missing_horizons:
        missing_fields.append("mature_validation_outcomes")
    if result.invalid_calls:
        missing_fields.append("valid_published_calls")
    return StageHealth(
        "ValidateStage",
        "OK" if result.healthy else "DEGRADED",
        missing_fields=missing_fields,
        notes=list(result.notes),
    )


def _overall_health(
    snapshot: IngestionSnapshot,
    archive_health: StageHealth,
    outputs: dict[str, PublishOutput],
    validation_health: StageHealth,
) -> StageHealth:
    """Retain failure/degradation and validation execution evidence for the whole run."""
    return combine_stage_health(
        "MultiPairRun",
        snapshot.health,
        archive_health,
        *(output.health for output in outputs.values()),
        validation_health,
    )


def _price_archive_health(result: PriceArchiveStageResult) -> StageHealth:
    return StageHealth(
        "PriceArchiveStage",
        "DEGRADED" if result.degraded else "OK",
        missing_fields=list(result.missing_fields),
        notes=list(result.notes),
    )


def _require_snapshot(snapshot: IngestionSnapshot, as_of: datetime.date) -> None:
    if snapshot.date != as_of:
        raise ValueError("Ingestion snapshot date differs from the requested date")
    if snapshot.health.status == "FAILED":
        raise ValueError("Ingestion stage reported FAILED")


def _report_stage_failure(
    alert: AlertPort,
    as_of: datetime.date,
    stage: str,
    error: Exception,
    *,
    pair: str | None = None,
) -> None:
    # Delivery is secondary: preserve the original exception if alerting also fails.
    try:
        alert.send_status(
            as_of, StageHealth(stage, "FAILED", notes=[type(error).__name__]), pair=pair
        )
    except Exception as alert_error:
        logger.warning("Failure notice delivery failed: %s", type(alert_error).__name__)


def _new_correlation_id() -> str:
    """Return a short unique correlation id for a flow run."""

    import uuid

    return uuid.uuid4().hex[:12]
