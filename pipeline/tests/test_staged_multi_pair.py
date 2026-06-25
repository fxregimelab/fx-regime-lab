"""Tests for the staged multi-pair orchestrator flow and resilience."""

from __future__ import annotations

import asyncio
import datetime

import pytest

from src.staged.constants import (
    STAGE_TASK_RETRIES,
    STAGE_TASK_RETRY_DELAY_SECONDS,
)
from src.staged.contracts import IngestionSnapshot, StageHealth
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from src.staged.orchestrator import (
    _ingestion_task,
    _publish_task,
    _regime_task,
    _signal_task,
    _validate_task,
    run_multi_pair_flow,
)
from src.types import CotRow, SpotBar


def _spot_bar(pair: str, d: datetime.date, close: float) -> SpotBar:
    return SpotBar(
        date=d,
        pair=pair,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000_000.0,
    )


def _trading_date_range(start: datetime.date, days: int) -> list[datetime.date]:
    dates: list[datetime.date] = []
    current = start
    while len(dates) < days:
        if current.weekday() < 5:
            dates.append(current)
        current += datetime.timedelta(days=1)
    return dates


def _make_pair_spots(pair: str, as_of: datetime.date, base: float) -> tuple[SpotBar, ...]:
    start = as_of - datetime.timedelta(days=60)
    dates = _trading_date_range(start, 40)
    return tuple(
        _spot_bar(pair, d, round(base + i * 0.0005, 4))
        for i, d in enumerate(dates)
    )


def _make_cot_rows(pair: str, as_of: datetime.date) -> list[CotRow]:
    cot_start = as_of - datetime.timedelta(weeks=11)
    rows: list[CotRow] = []
    for i in range(10):
        report_date = cot_start + datetime.timedelta(weeks=i)
        rows.append(
            CotRow(
                date=report_date,
                pair=pair,
                net_long=10_000 + i * 500,
                open_interest=50_000 + i * 1_000,
                asset_mgr_net=6_000 + i * 300,
                lev_money_net=-2_000 - i * 100,
            )
        )
    return rows


def _make_multi_pair_snapshot() -> IngestionSnapshot:
    as_of = datetime.date(2026, 5, 20)
    pairs = [("EURUSD", 1.0800), ("USDJPY", 145.00), ("USDINR", 85.50)]
    spots = {pair: _make_pair_spots(pair, as_of, base) for pair, base in pairs}
    cot_rows: list[CotRow] = []
    for pair, _ in pairs:
        cot_rows.extend(_make_cot_rows(pair, as_of))

    return IngestionSnapshot(
        date=as_of,
        spots=spots,
        yields={
            "DGS2": 4.0,
            "ECBDFR": 2.0,
            "IRLTLT01JPM156N": 0.5,
            "INDIRLTLT01STM": 6.5,
            "us_10y": 4.5,
            "de_10y": 2.5,
            "jp_10y": 1.0,
            "in_10y": 7.0,
            "T10YIE": 2.0,
        },
        cot_rows=cot_rows,
        cross_asset={
            "vix": 18.0,
            "dxy": 104.0,
            "oil": 75.0,
            "gold": 2000.0,
            "copper": 4.0,
            "stoxx": 4500.0,
        },
        macro={
            "ecb_balance_sheet": 7000.0,
            "bund_btp_spread": 1.5,
            "boj_policy_rate": 0.25,
            "india_vix": 15.0,
            "inr_forward_premium": 1.5,
        },
        dqs_score=0.95,
        stress_level="GREEN",
    )


@pytest.fixture(autouse=True)
def _patch_staged_retry_delay_for_speed(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zero out Prefect retry delays in functional tests to keep the suite fast.

    The policy test below asserts the production retry delay value, so it is
    intentionally skipped by this fixture. Production behavior is unchanged.
    """

    if request.node.name == "test_stage_boundary_tasks_have_retry_policy":
        return

    for task in (
        _ingestion_task,
        _signal_task,
        _regime_task,
        _publish_task,
        _validate_task,
    ):
        monkeypatch.setattr(task, "retry_delay_seconds", 0, raising=False)


def test_stage_boundary_tasks_have_retry_policy() -> None:
    """Each stage boundary in the multi-pair flow is a Prefect task with retries."""

    for task in (
        _ingestion_task,
        _signal_task,
        _regime_task,
        _publish_task,
        _validate_task,
    ):
        assert task.retries == STAGE_TASK_RETRIES, f"{task.name} retries"
        assert (
            task.retry_delay_seconds == STAGE_TASK_RETRY_DELAY_SECONDS  # type: ignore[comparison-overlap]
        ), f"{task.name} retry delay"


def test_multi_pair_flow_runs_all_three_pairs() -> None:
    """The orchestrator loops over all locked pairs and publishes each one."""

    snapshot = _make_multi_pair_snapshot()
    fetcher = FakeFetcherPort(snapshot)
    writer = FakeWriterPort()
    alert = FakeAlertPort()

    output = asyncio.run(
        run_multi_pair_flow(
            snapshot.date,
            fetcher=fetcher,
            writer=writer,
            alert=alert,
            correlation_id="multi-pair-test",
        )
    )

    assert output.date == snapshot.date
    assert set(output.outputs.keys()) == {"EURUSD", "USDJPY", "USDINR"}
    assert all(o.health.status == "OK" for o in output.outputs.values())
    assert output.health.status == "OK"
    assert len(writer.regime_calls) == 3
    assert len(alert.successes) == 3
    assert len(alert.heartbeats) == 1
    assert alert.heartbeats[0]["pairs_processed"] == 3
    assert alert.heartbeats[0]["regime_calls_count"] == 3


def test_multi_pair_flow_continues_when_ingestion_degraded() -> None:
    """A non-critical fetcher failure marks the run DEGRADED but all pairs publish."""

    snapshot = _make_multi_pair_snapshot()
    degraded_snapshot = IngestionSnapshot(
        date=snapshot.date,
        spots=snapshot.spots,
        yields=snapshot.yields,
        cot_rows=snapshot.cot_rows,
        cross_asset=snapshot.cross_asset,
        macro=snapshot.macro,
        dqs_score=snapshot.dqs_score,
        stress_level=snapshot.stress_level,
        health=StageHealth(
            stage_name="IngestionStage",
            status="DEGRADED",
            missing_fields=["cot"],
        ),
    )
    fetcher = FakeFetcherPort(degraded_snapshot)
    writer = FakeWriterPort()
    alert = FakeAlertPort()

    output = asyncio.run(
        run_multi_pair_flow(
            snapshot.date,
            fetcher=fetcher,
            writer=writer,
            alert=alert,
        )
    )

    assert output.health.status == "DEGRADED"
    assert set(output.outputs.keys()) == {"EURUSD", "USDJPY", "USDINR"}
    assert all(o.health.status == "DEGRADED" for o in output.outputs.values())
    assert len(writer.regime_calls) == 3
    assert len(alert.successes) == 3


def test_multi_pair_flow_fails_on_critical_ingestion_failure() -> None:
    """A critical fetcher failure (missing spots) fails the whole flow."""

    class CriticalFailureFetcher(FakeFetcherPort):
        async def fetch(self, as_of: datetime.date) -> IngestionSnapshot:
            raise ValueError("Critical ingestion inputs missing: spots")

    snapshot = _make_multi_pair_snapshot()
    fetcher = CriticalFailureFetcher(snapshot)
    writer = FakeWriterPort()
    alert = FakeAlertPort()

    with pytest.raises(ValueError, match="Critical ingestion inputs missing"):
        asyncio.run(
            run_multi_pair_flow(
                snapshot.date,
                fetcher=fetcher,
                writer=writer,
                alert=alert,
            )
        )

    assert len(writer.regime_calls) == 0


def test_multi_pair_flow_rejects_disallowed_pair() -> None:
    """The flow enforces the 3-pair lock at runtime."""

    snapshot = _make_multi_pair_snapshot()
    fetcher = FakeFetcherPort(snapshot)
    writer = FakeWriterPort()
    alert = FakeAlertPort()

    with pytest.raises(ValueError, match="not in the allowed universe"):
        asyncio.run(
            run_multi_pair_flow(
                snapshot.date,
                pairs=["EURUSD", "GBPUSD"],
                fetcher=fetcher,
                writer=writer,
                alert=alert,
            )
        )
