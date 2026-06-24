"""Staged pipeline orchestrator flows."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Any

from prefect import flow, task

from src.staged.contracts import (
    IngestionSnapshot,
    MultiPairRunOutput,
    PublishOutput,
    SignalPipelineResult,
    StageHealth,
    StageStatus,
)
from src.staged.ports import AlertPort, FetcherPort, WriterPort
from src.staged.stages import (
    IngestionStage,
    PublishStage,
    RegimeStage,
    SignalStage,
    ValidateStage,
)
from src.types import RegimeCall

_ALLOWED_PAIRS: frozenset[str] = frozenset({"EURUSD", "USDJPY", "USDINR"})
_DEFAULT_PAIR_ORDER: tuple[str, ...] = ("EURUSD", "USDJPY", "USDINR")

# Shared retry policy for stage boundaries: two attempts with a short delay
# to ride out transient database or Slack failures without corrupting the ledger.
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

    ingestion = IngestionStage(fetcher)
    signal_stage = SignalStage()
    regime_stage = RegimeStage()
    publish_stage = PublishStage(writer, alert, correlation_id=cid)

    snapshot = await ingestion.run(as_of)
    signal_result = signal_stage.run(pair, snapshot)
    regime_call = regime_stage.run(pair, signal_result)
    publish_output = await publish_stage.run(pair, regime_call)

    return publish_output


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
        raise ValueError(
            f"Pairs {disallowed!r} are not in the allowed universe {_ALLOWED_PAIRS}"
        )

    cid = correlation_id or _new_correlation_id()

    snapshot = await _ingestion_task(fetcher, as_of)

    outputs: dict[str, PublishOutput] = {}
    for pair in requested_pairs:
        outputs[pair] = await _run_pair_pipeline(
            pair=pair,
            snapshot=snapshot,
            writer=writer,
            alert=alert,
            correlation_id=cid,
        )

    validation_rows: list[dict[str, Any]] = []
    if run_validation:
        validation_rows = _validate_task(
            as_of,
            list(requested_pairs),
            writer,
            snapshot,
        )

    dqs = snapshot.dqs_score if snapshot.dqs_score is not None else 0.0
    alert.send_heartbeat(
        as_of,
        pairs_processed=len(requested_pairs),
        regime_calls_count=len(outputs),
        dqs_score=dqs,
    )

    overall_status = _overall_health(snapshot, outputs)

    return MultiPairRunOutput(
        date=as_of,
        outputs=outputs,
        validation_rows=validation_rows,
        health=StageHealth("MultiPairRun", overall_status),
        pairs_processed=len(requested_pairs),
        regime_calls_count=len(outputs),
    )


async def _run_pair_pipeline(
    *,
    pair: str,
    snapshot: IngestionSnapshot,
    writer: WriterPort,
    alert: AlertPort,
    correlation_id: str | None,
) -> PublishOutput:
    """Run Signal → Regime → Publish for a single pair.

    Each stage call is a Prefect task with retries so transient failures in
    signal math, regime assembly, or persistence do not corrupt the ledger.
    """

    signal_result = _signal_task(pair, snapshot)
    regime_call = _regime_task(pair, signal_result)
    publish_output = await _publish_task(
        pair,
        regime_call,
        writer,
        alert,
        correlation_id,
    )

    if snapshot.health.status == "DEGRADED":
        publish_output = PublishOutput(
            pair=publish_output.pair,
            date=publish_output.date,
            regime_call=publish_output.regime_call,
            brief_markdown=publish_output.brief_markdown,
            desk_card=publish_output.desk_card,
            alerts_sent=publish_output.alerts_sent,
            health=StageHealth(
                stage_name="PublishStage",
                status="DEGRADED",
                notes=["ingestion_degraded"] + list(publish_output.health.notes),
            ),
        )

    return publish_output


@task(retries=_STAGE_RETRIES, retry_delay_seconds=_STAGE_RETRY_DELAY_SECONDS)
async def _ingestion_task(
    fetcher: FetcherPort,
    as_of: datetime.date,
) -> IngestionSnapshot:
    """Prefect task wrapper around ``IngestionStage.run``."""

    return await IngestionStage(fetcher).run(as_of)


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
) -> PublishOutput:
    """Prefect task wrapper around ``PublishStage.run``."""

    return await PublishStage(writer, alert, correlation_id=correlation_id).run(
        pair, regime_call
    )


@task(retries=_STAGE_RETRIES, retry_delay_seconds=_STAGE_RETRY_DELAY_SECONDS)
def _validate_task(
    as_of: datetime.date,
    pairs: list[str],
    writer: WriterPort,
    snapshot: IngestionSnapshot,
) -> list[dict[str, Any]]:
    """Prefect task wrapper around ``ValidateStage.run``."""

    return ValidateStage(writer).run(as_of, pairs, snapshot=snapshot)


def _overall_health(
    snapshot: IngestionSnapshot,
    outputs: dict[str, PublishOutput],
) -> StageStatus:
    """Return OK/DEGRADED/FAILED for the whole run."""

    if snapshot.health.status == "FAILED":
        return "FAILED"
    if snapshot.health.status == "DEGRADED" or any(
        o.health.status == "DEGRADED" for o in outputs.values()
    ):
        return "DEGRADED"
    return "OK"


def _new_correlation_id() -> str:
    """Return a short unique correlation id for a flow run."""

    import uuid

    return uuid.uuid4().hex[:12]
