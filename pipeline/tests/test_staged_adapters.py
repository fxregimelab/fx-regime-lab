"""Unit tests for production staged pipeline adapters."""

from __future__ import annotations

import asyncio
import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest

from src.staged.contracts import IngestionSnapshot
from src.staged.ports import AlertPort, FetcherPort, WriterPort
from src.types import CotRow, RegimeCall, SpotBar

# ── ProductionFetcherPort tests ───────────────────────────────────────────────


def test_fetcher_adapter_is_a_fetcher_port() -> None:
    """ProductionFetcherPort satisfies the FetcherPort ABC."""

    from src.staged.adapters.fetcher import ProductionFetcherPort

    fetcher: FetcherPort = ProductionFetcherPort()
    assert isinstance(fetcher, FetcherPort)


def test_fetcher_adapter_delegates_to_build_master_buffer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ProductionFetcherPort builds a core snapshot and maps it to staged."""

    from src.staged.adapters import fetcher as fetcher_module
    from src.staged.adapters.fetcher import ProductionFetcherPort

    as_of = datetime.date(2026, 2, 20)

    captured: dict[str, Any] = {}

    async def fake_build_master_buffer(
        *,
        spot_lookback_days: int = 120,
        yield_lookback_days: int = 5,
    ) -> dict[str, Any]:
        captured["spot_lookback"] = spot_lookback_days
        captured["yield_lookback"] = yield_lookback_days
        return {
            "fx_spot": {
                "EURUSD": [
                    {
                        "date": as_of,
                        "pair": "EURUSD",
                        "open": 1.05,
                        "high": 1.05,
                        "low": 1.05,
                        "close": 1.05,
                        "volume": 1_000_000.0,
                    }
                ]
            },
            "yields": {"us_10y": 4.5},
            "cot": [{"date": as_of, "pair": "EURUSD", "net_long": 1, "open_interest": 1}],
            "cross_asset": {"vix": 18.0, "dxy": 104.0},
        }

    @dataclass(frozen=True)
    class FakeCoreSnapshot:
        date: datetime.date
        spots: dict[str, Sequence[SpotBar]]
        yields: dict[str, float | None]
        cot_rows: list[CotRow]
        cross_asset: dict[str, float | None]
        macro: dict[str, Any] | None
        dqs_score: float | None
        stress_level: str | None

        @classmethod
        def from_buffer(
            cls,
            as_of: datetime.date,
            buffer: dict[str, Any],
            *,
            macro: dict[str, Any] | None = None,
            dqs_score: float | None = None,
            stress_level: str | None = None,
        ) -> FakeCoreSnapshot:
            captured["from_buffer_as_of"] = as_of
            captured["from_buffer_macro"] = macro
            return cls(
                date=as_of,
                spots={
                    "EURUSD": (
                        SpotBar(
                            date=as_of,
                            pair="EURUSD",
                            open=1.05,
                            high=1.05,
                            low=1.05,
                            close=1.05,
                            volume=1_000_000.0,
                        ),
                    )
                },
                yields={"us_10y": 4.5},
                cot_rows=[CotRow(date=as_of, pair="EURUSD", net_long=1, open_interest=1)],
                cross_asset={"vix": 18.0, "dxy": 104.0},
                macro=macro,
                dqs_score=dqs_score,
                stress_level=stress_level,
            )

    monkeypatch.setattr(fetcher_module, "build_master_buffer", fake_build_master_buffer)
    monkeypatch.setattr(fetcher_module, "CoreIngestionSnapshot", FakeCoreSnapshot)

    fetcher = ProductionFetcherPort(
        spot_lookback_days=60,
        yield_lookback_days=3,
        macro={"foo": 1.0},
        dqs_score=0.92,
        stress_level="GREEN",
    )
    result = asyncio.run(fetcher.fetch(as_of))

    assert isinstance(result, IngestionSnapshot)
    assert result.date == as_of
    assert result.spots == {
        "EURUSD": (
            SpotBar(
                date=as_of,
                pair="EURUSD",
                open=1.05,
                high=1.05,
                low=1.05,
                close=1.05,
                volume=1_000_000.0,
            ),
        )
    }
    assert result.yields == {"us_10y": 4.5}
    assert result.cot_rows == [CotRow(date=as_of, pair="EURUSD", net_long=1, open_interest=1)]
    assert result.cross_asset == {"vix": 18.0, "dxy": 104.0}
    assert result.macro == {"foo": 1.0}
    assert result.dqs_score == 0.92
    assert result.stress_level == "GREEN"
    assert result.health.stage_name == "IngestionStage"
    assert result.health.status == "OK"
    assert captured["spot_lookback"] == 60
    assert captured["yield_lookback"] == 3
    assert captured["from_buffer_as_of"] == as_of
    assert captured["from_buffer_macro"] == {"foo": 1.0}


def test_fetcher_adapter_fails_on_critical_missing_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ProductionFetcherPort raises when critical inputs (spots/yields) are missing."""

    from src.staged.adapters import fetcher as fetcher_module
    from src.staged.adapters.fetcher import ProductionFetcherPort

    @dataclass(frozen=True)
    class FakeCoreSnapshot:
        date: datetime.date
        spots: dict[str, Sequence[SpotBar]]
        yields: dict[str, float | None]
        cot_rows: list[CotRow]
        cross_asset: dict[str, float | None]
        macro: dict[str, Any] | None = None
        dqs_score: float | None = None
        stress_level: str | None = None

        @classmethod
        def from_buffer(
            cls,
            as_of: datetime.date,
            buffer: dict[str, Any],
            **kwargs: Any,
        ) -> FakeCoreSnapshot:
            return cls(date=as_of, spots={}, yields={}, cot_rows=[], cross_asset={})

    async def fake_build_empty(
        *,
        spot_lookback_days: int = 120,
        yield_lookback_days: int = 5,
    ) -> dict[str, Any]:
        return {"fx_spot": {}, "yields": {}, "cot": [], "cross_asset": {}}

    monkeypatch.setattr(
        fetcher_module,
        "build_master_buffer",
        fake_build_empty,
    )
    monkeypatch.setattr(fetcher_module, "CoreIngestionSnapshot", FakeCoreSnapshot)

    fetcher = ProductionFetcherPort()

    with pytest.raises(ValueError, match="Critical ingestion inputs missing: spots"):
        asyncio.run(fetcher.fetch(datetime.date(2026, 2, 20)))


# ── ProductionWriterPort tests ────────────────────────────────────────────────


def test_writer_adapter_delegates_to_writer_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ProductionWriterPort delegates regime calls and validation rows to db.writer."""

    from src.staged.adapters.writer import ProductionWriterPort
    from src.staged.adapters.writer import writer_module as db_writer

    calls: list[tuple[RegimeCall, dict[str, Any]]] = []
    validation_rows: list[Mapping[str, Any]] = []

    def fake_write_regime_call(
        call: RegimeCall,
        *,
        correlation_id: str | None = None,
        write_hash: str | None = None,
    ) -> int:
        calls.append((call, {"correlation_id": correlation_id, "write_hash": write_hash}))
        return 42

    def fake_write_validation_row(row: Mapping[str, Any]) -> None:
        validation_rows.append(row)

    monkeypatch.setattr(db_writer, "write_regime_call", fake_write_regime_call)
    monkeypatch.setattr(db_writer, "write_validation_row", fake_write_validation_row)

    writer: WriterPort = ProductionWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=datetime.date(2026, 2, 20),
        regime="RISK_OFF_DOLLAR_BID",
        confidence=0.65,
        signal_composite=0.8,
        rate_signal="BULLISH",
    )
    call_id = writer.write_regime_call(call, correlation_id="corr-123", write_hash="hash-abc")
    writer.write_validation_rows([{"pair": "EURUSD", "date": "2026-02-20"}])

    assert call_id == 42
    assert len(calls) == 1
    assert calls[0][0] == call
    assert calls[0][1]["correlation_id"] == "corr-123"
    assert calls[0][1]["write_hash"] == "hash-abc"
    assert validation_rows == [{"pair": "EURUSD", "date": "2026-02-20"}]


# ── ProductionAlertPort tests ─────────────────────────────────────────────────


def test_alert_adapter_delegates_to_alerts_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ProductionAlertPort delegates heartbeat, success, and low-DQS to monitoring.alerts."""

    from src.staged.adapters.alert import ProductionAlertPort
    from src.staged.adapters.alert import alerts_module as alerts

    heartbeats: list[dict[str, Any]] = []
    successes: list[tuple[str, list[dict[str, Any]] | None]] = []
    low_dqs: list[tuple[str, float, list[str]]] = []

    def fake_send_success_heartbeat(
        date_str: str,
        pairs_processed: int,
        regime_calls_count: int,
        dqs_score: float,
    ) -> None:
        heartbeats.append(
            {
                "date_str": date_str,
                "pairs_processed": pairs_processed,
                "regime_calls_count": regime_calls_count,
                "dqs_score": dqs_score,
            }
        )

    def fake_send_slack_alert(message: str, blocks: list[dict[str, Any]] | None = None) -> None:
        successes.append((message, blocks))

    def fake_alert_on_low_dqs(
        date_str: str,
        dqs_score: float,
        stale_sources: list[str],
    ) -> None:
        low_dqs.append((date_str, dqs_score, stale_sources))

    monkeypatch.setattr(alerts, "send_success_heartbeat", fake_send_success_heartbeat)
    monkeypatch.setattr(alerts, "send_slack_alert", fake_send_slack_alert)
    monkeypatch.setattr(alerts, "alert_on_low_dqs", fake_alert_on_low_dqs)

    alert: AlertPort = ProductionAlertPort()
    call = RegimeCall(
        pair="EURUSD",
        date=datetime.date(2026, 2, 20),
        regime="RISK_OFF_DOLLAR_BID",
        confidence=0.65,
        signal_composite=0.8,
        rate_signal="BULLISH",
    )

    alert.send_success(call)
    alert.send_heartbeat(
        datetime.date(2026, 2, 20),
        pairs_processed=3,
        regime_calls_count=3,
        dqs_score=0.95,
    )
    alert.send_low_dqs(datetime.date(2026, 2, 20), 0.55, ["cot"])

    assert len(successes) == 1
    assert "EURUSD" in successes[0][0]
    assert "RISK_OFF_DOLLAR_BID" in successes[0][0]
    assert heartbeats == [
        {
            "date_str": "2026-02-20",
            "pairs_processed": 3,
            "regime_calls_count": 3,
            "dqs_score": 0.95,
        }
    ]
    assert low_dqs == [("2026-02-20", 0.55, ["cot"])]
