"""Unit tests for production staged pipeline adapters."""

from __future__ import annotations

import asyncio
import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest

from src.staged.contracts import IngestionSnapshot, StageHealth, StageStatus
from src.staged.ports import AlertPort, FetcherPort, WriterPort
from src.types import CotRow, RegimeCall, SignalRow, SpotBar


def _signal_row() -> SignalRow:
    return SignalRow(
        pair="EURUSD",
        date=datetime.date(2026, 2, 20),
        rate_diff_2y=1.25,
        rate_diff_10y=1.1,
        cot_percentile=0.7,
        realized_vol_20d=0.08,
        realized_vol_5d=0.09,
        implied_vol_30d=0.1,
        spot=1.08,
        day_change=0.002,
        day_change_pct=0.2,
        cross_asset_vix=18.0,
        cross_asset_dxy=104.0,
        cross_asset_oil=72.0,
        cross_asset_us10y=4.2,
        cross_asset_gold=2_600.0,
        cross_asset_copper=4.1,
        cross_asset_stoxx=510.0,
        oi_delta=50,
        data_quality_notes=["COT source lagged"],
    )

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

    as_of = datetime.datetime.now(datetime.UTC).date()

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


def test_fetcher_adapter_rejects_non_current_date_before_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The live fetcher cannot label current provider data as a historical snapshot."""

    from src.staged.adapters import fetcher as fetcher_module
    from src.staged.adapters.fetcher import ProductionFetcherPort

    calls: list[str] = []

    async def forbidden_fetch(**kwargs: Any) -> dict[str, Any]:
        calls.append("fetch")
        return {}

    monkeypatch.setattr(fetcher_module, "build_master_buffer", forbidden_fetch)
    historical = datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=1)

    with pytest.raises(ValueError, match="current UTC date"):
        asyncio.run(ProductionFetcherPort().fetch(historical))

    assert calls == []


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
    current = datetime.datetime.now(datetime.UTC).date()

    with pytest.raises(ValueError, match="Critical ingestion inputs missing: spots"):
        asyncio.run(fetcher.fetch(current))


# ── ProductionWriterPort tests ────────────────────────────────────────────────


def test_writer_adapter_delegates_price_archive_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.staged.adapters.writer import ProductionWriterPort
    from src.staged.adapters.writer import writer_module as db_writer

    observations = [{"pair": "EURUSD", "date": "2026-02-20"}]
    receipt = {"observation_ids": [17], "inserted_count": 1, "existing_count": 0}
    calls: list[Sequence[Mapping[str, Any]]] = []

    def fake_archive(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        calls.append(rows)
        return receipt

    monkeypatch.setattr(db_writer, "archive_price_observations", fake_archive)

    assert ProductionWriterPort().archive_price_observations(observations) == receipt
    assert calls == [observations]


def test_writer_adapter_delegates_atomic_publication_to_core_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ProductionWriterPort uses the shared atomic core persistence boundary."""

    from src.staged.adapters.writer import (
        ProductionWriterPort,
        regime_persist_module,
    )
    from src.staged.adapters.writer import (
        writer_module as db_writer,
    )

    calls: list[tuple[RegimeCall, SignalRow, str | None]] = []
    validation_rows: list[Mapping[str, Any]] = []
    reader_calls: list[tuple[str, int | None]] = []
    evidence_calls: list[int] = []
    price_calls: list[tuple[str, str]] = []

    def fake_persist_regime_call(
        call: RegimeCall,
        signals: SignalRow,
        *,
        correlation_id: str | None = None,
    ) -> int:
        calls.append((call, signals, correlation_id))
        return 42

    def fake_write_validation_row(row: Mapping[str, Any]) -> None:
        validation_rows.append(row)

    def fake_get_historical_regime_calls(
        pair: str,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        reader_calls.append((pair, limit))
        return [
            {
                "id": 91,
                "date": "2026-02-20",
                "pair": pair,
                "regime": "RISK_OFF_DOLLAR_BID",
                "predicted_direction": "BULLISH",
                "confidence": 0.65,
            }
        ]

    existing = {"call_id": 91, "call_date": "2026-02-20", "pair": "EURUSD"}

    def fake_get_validation_log_for_call(call_id: int | str) -> dict[str, Any]:
        assert call_id == 91
        return existing

    def fake_get_publication_signal_for_call(
        call_id: int,
    ) -> dict[str, Any]:
        evidence_calls.append(call_id)
        return {"pair": "EURUSD", "date": "2026-02-20", "spot": 1.08}

    def fake_get_exact_historical_price_for_date(
        pair: str,
        date_str: str,
    ) -> dict[str, Any]:
        price_calls.append((pair, date_str))
        return {"pair": pair, "date": date_str, "close": 1.09}

    monkeypatch.setattr(regime_persist_module, "persist_regime_call", fake_persist_regime_call)
    monkeypatch.setattr(db_writer, "write_validation_row", fake_write_validation_row)
    monkeypatch.setattr(
        db_writer,
        "get_historical_regime_calls",
        fake_get_historical_regime_calls,
    )
    monkeypatch.setattr(
        db_writer,
        "get_validation_log_for_call",
        fake_get_validation_log_for_call,
    )
    monkeypatch.setattr(
        db_writer,
        "get_publication_signal_for_call",
        fake_get_publication_signal_for_call,
    )
    monkeypatch.setattr(
        db_writer,
        "get_exact_historical_price_for_date",
        fake_get_exact_historical_price_for_date,
    )

    writer: WriterPort = ProductionWriterPort()
    call = RegimeCall(
        pair="EURUSD",
        date=datetime.date(2026, 2, 20),
        regime="RISK_OFF_DOLLAR_BID",
        confidence=0.65,
        signal_composite=0.8,
        rate_signal="BULLISH",
    )
    signal_row = _signal_row()
    call_id = writer.publish_regime_call(call, signal_row, correlation_id="corr-123")
    writer.write_validation_rows([{"pair": "EURUSD", "date": "2026-02-20"}])
    published = writer.read_published_calls("EURUSD", limit=None)
    evaluation = writer.read_validation_entry(91)
    publication_signal = writer.get_publication_signal_for_call(91)
    historical_price = writer.get_exact_historical_price_for_date(
        "EURUSD", "2026-02-27"
    )

    assert call_id == 42
    assert calls == [(call, signal_row, "corr-123")]
    assert validation_rows == [{"pair": "EURUSD", "date": "2026-02-20"}]
    assert reader_calls == [("EURUSD", None)]
    assert published[0]["call_id"] == 91
    assert evaluation is existing
    assert publication_signal is not None
    assert historical_price is not None
    assert publication_signal["spot"] == 1.08
    assert historical_price["close"] == 1.09
    assert evidence_calls == [91]
    assert price_calls == [("EURUSD", "2026-02-27")]

    with pytest.raises(RuntimeError, match="publish_regime_call with signal evidence"):
        writer.write_regime_call(call)


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


def test_alert_adapter_sends_explicit_non_ok_status_without_healthy_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-OK health uses a plain status notice, never the healthy heartbeat."""

    from src.staged.adapters.alert import ProductionAlertPort
    from src.staged.adapters.alert import alerts_module as alerts

    notices: list[str] = []

    def fake_send_slack_alert(
        message: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> None:
        assert blocks is None
        notices.append(message)

    def unexpected_healthy_helper(*args: Any, **kwargs: Any) -> None:
        pytest.fail("non-OK status called a healthy heartbeat helper")

    monkeypatch.setattr(alerts, "send_slack_alert", fake_send_slack_alert)
    monkeypatch.setattr(alerts, "send_success_heartbeat", unexpected_healthy_helper)

    statuses: tuple[StageStatus, ...] = ("DEGRADED", "FAILED")
    for status in statuses:
        notices.clear()
        health = StageHealth(
            "SignalStage",
            status,
            missing_fields=["cot_percentile", "implied_vol_30d"],
            notes=["COT source lagged", "implied vol fallback used"],
        )
        ProductionAlertPort().send_status(
            datetime.date(2026, 2, 20),
            health,
            pair="EURUSD",
        )

        assert len(notices) == 1
        notice = notices[0]
        assert status in notice
        assert "SignalStage" in notice
        assert "EURUSD" in notice
        assert "cot_percentile, implied_vol_30d" in notice
        assert "COT source lagged; implied vol fallback used" in notice
        assert "success" not in notice.lower()
        assert "healthy" not in notice.lower()


def test_alert_adapter_rejects_ok_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Healthy status must continue through the existing success APIs."""

    from src.staged.adapters.alert import ProductionAlertPort
    from src.staged.adapters.alert import alerts_module as alerts

    sent: list[str] = []
    monkeypatch.setattr(alerts, "send_slack_alert", sent.append)

    with pytest.raises(ValueError, match="only DEGRADED or FAILED"):
        ProductionAlertPort().send_status(
            datetime.date(2026, 2, 20),
            StageHealth("SignalStage", "OK"),
            pair="EURUSD",
        )

    assert sent == []


def test_alert_adapter_redacts_credentials_and_raw_exception_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Status notices preserve useful notes without exposing operational secrets."""

    from src.staged.adapters.alert import ProductionAlertPort
    from src.staged.adapters.alert import alerts_module as alerts

    notices: list[str] = []
    monkeypatch.setattr(alerts, "send_slack_alert", notices.append)

    ProductionAlertPort().send_status(
        datetime.date(2026, 2, 20),
        StageHealth(
            "PublishStage",
            "FAILED",
            notes=[
                "token=private-value",
                "TimeoutError",
                "RuntimeError: database request failed",
                "retry is required",
            ],
        ),
    )

    assert len(notices) == 1
    assert "private-value" not in notices[0]
    assert "database request failed" not in notices[0]
    assert "token=[REDACTED]" in notices[0]
    assert "TimeoutError" in notices[0]
    assert "RuntimeError: details withheld" in notices[0]
    assert "retry is required" in notices[0]
