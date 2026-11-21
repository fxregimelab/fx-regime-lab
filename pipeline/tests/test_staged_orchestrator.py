"""Tests for the staged pipeline single-pair orchestrator flow."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Any

os.environ.setdefault("PREFECT_LOGGING_LEVEL", "CRITICAL")

import pytest

from src.staged.adapters.writer import ProductionWriterPort, regime_persist_module
from src.staged.contracts import PublishOutput
from src.staged.fakes import FakeAlertPort, FakeFetcherPort, FakeWriterPort
from src.staged.orchestrator import run_single_pair_flow
from src.types import RegimeCall
from tests.fixtures.eurusd_snapshot import make_recorded_eurusd_snapshot


def test_orchestrator_runs_single_pair_flow_with_recorded_fixture() -> None:
    """Run the single-pair flow end-to-end with a recorded EUR/USD snapshot."""

    pair = "EURUSD"
    snapshot = make_recorded_eurusd_snapshot()
    fetcher = FakeFetcherPort(snapshot)
    writer = FakeWriterPort()
    alert = FakeAlertPort()

    output = asyncio.run(
        run_single_pair_flow(
            pair,
            snapshot.date,
            fetcher=fetcher,
            writer=writer,
            alert=alert,
        )
    )

    assert isinstance(output, PublishOutput)
    assert output.pair == pair
    assert output.date == snapshot.date
    assert output.regime_call.pair == pair
    assert output.regime_call.date == snapshot.date
    assert output.regime_call.predicted_direction == "NEUTRAL"
    assert output.regime_call.directional_bias == "NEUTRAL"
    assert output.regime_call.entry_timing == "WAIT"
    assert output.regime_call.position_size == "HALF"
    assert output.regime_call.confidence == pytest.approx(0.4, abs=1e-9)
    # Raw COT and smart-spread COT are both at the 100th percentile, so COT is
    # +1.0. The EUR special is pair-oriented to +0.233333: raw USD-strength is
    # ((-0.8) + 1/3) / 2 = -0.233333, then EURUSD inverts it once. With rate
    # history unavailable, the retained directional weights renormalize:
    # (1.0 * 0.25 + 0.233333 * 0.05) / (0.25 + 0.05) = 0.872222.
    assert output.regime_call.signal_composite == pytest.approx(0.8722222222)
    assert output.regime_call.data_quality_score == 0.95
    assert output.regime_call.special_signal_label == "Bund-BTP + ECB BS"
    assert output.health.status == "DEGRADED"
    assert len(writer.regime_calls) == 1
    assert writer.regime_calls[0][0] == output.regime_call
    assert writer.regime_calls[0][1]["correlation_id"] is not None
    assert not alert.successes
    assert len(alert.statuses) == 1
    assert "status_alert" in output.alerts_sent
    assert len(writer.signal_rows) == 1
    assert "rate_history_unavailable" in output.health.notes


def test_orchestrator_rejects_disallowed_pair() -> None:
    """The single-pair flow enforces the 3-pair lock at runtime."""

    snapshot = make_recorded_eurusd_snapshot()
    fetcher = FakeFetcherPort(snapshot)
    writer = FakeWriterPort()
    alert = FakeAlertPort()

    with pytest.raises(ValueError, match="Pair 'GBPUSD' is not in the allowed universe"):
        asyncio.run(
            run_single_pair_flow(
                "GBPUSD",
                snapshot.date,
                fetcher=fetcher,
                writer=writer,
                alert=alert,
            )
        )


def test_orchestrator_flow_uses_production_writer_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The flow works when injecting the production writer with a patched DB layer."""

    pair = "EURUSD"
    snapshot = make_recorded_eurusd_snapshot()
    fetcher = FakeFetcherPort(snapshot)
    alert = FakeAlertPort()

    calls: list[tuple[RegimeCall, Mapping[str, Any]]] = []

    def fake_persist_regime_call(
        call: RegimeCall,
        signals: Any,
        *,
        correlation_id: str | None = None,
    ) -> int:
        calls.append((call, {"signals": signals, "correlation_id": correlation_id}))
        return 7

    monkeypatch.setattr(regime_persist_module, "persist_regime_call", fake_persist_regime_call)

    writer = ProductionWriterPort()

    output = asyncio.run(
        run_single_pair_flow(
            pair,
            snapshot.date,
            fetcher=fetcher,
            writer=writer,
            alert=alert,
            correlation_id="prod-test",
        )
    )

    assert output.pair == pair
    assert len(calls) == 1
    assert calls[0][0] == output.regime_call
    assert calls[0][1]["correlation_id"] == "prod-test"
    assert calls[0][1]["signals"].pair == pair
    assert not alert.successes
    assert len(alert.statuses) == 1
