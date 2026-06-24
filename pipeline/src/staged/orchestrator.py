"""Single-pair staged pipeline orchestrator flow."""

from __future__ import annotations

import datetime

from prefect import flow

from src.staged.contracts import PublishOutput
from src.staged.ports import AlertPort, FetcherPort, WriterPort
from src.staged.stages import (
    IngestionStage,
    PublishStage,
    RegimeStage,
    SignalStage,
)

_ALLOWED_PAIRS: frozenset[str] = frozenset({"EURUSD", "USDJPY", "USDINR"})


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


def _new_correlation_id() -> str:
    """Return a short unique correlation id for a flow run."""

    import uuid

    return uuid.uuid4().hex[:12]
