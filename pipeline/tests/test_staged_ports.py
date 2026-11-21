"""Tests for the staged pipeline external ports."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pytest

from src.staged.contracts import IngestionSnapshot, StageHealth
from src.staged.ports import AlertPort, FetcherPort, WriterPort
from src.types import RegimeCall, SignalRow


def test_fetcher_port_can_be_subclassed() -> None:
    """FetcherPort defines a narrow async fetch method that can be implemented."""

    class FakeFetcher(FetcherPort):
        async def fetch(self, as_of: date) -> IngestionSnapshot:
            return IngestionSnapshot(
                date=as_of,
                spots={},
                yields={},
                cot_rows=[],
                cross_asset={},
                health=StageHealth("IngestionStage", "OK"),
            )

    fetcher: FetcherPort = FakeFetcher()
    snapshot = asyncio.run(fetcher.fetch(date(2026, 5, 20)))

    assert snapshot.date == date(2026, 5, 20)


def test_fetcher_port_is_abstract() -> None:
    """FetcherPort cannot be instantiated without implementing fetch."""

    with pytest.raises(TypeError):
        FetcherPort()  # type: ignore[abstract]


def test_writer_port_can_be_subclassed() -> None:
    """WriterPort defines narrow write methods that can be implemented."""

    class FakeWriter(WriterPort):
        def __init__(self) -> None:
            self.observations: list[Mapping[str, Any]] = []
            self.calls: list[RegimeCall] = []
            self.signal_rows: list[SignalRow] = []
            self.validation_rows: list[Mapping[str, Any]] = []

        def archive_price_observations(
            self,
            observations: Sequence[Mapping[str, Any]],
        ) -> Mapping[str, Any]:
            self.observations.extend(observations)
            return {
                "observation_ids": list(range(1, len(observations) + 1)),
                "inserted_count": len(observations),
                "existing_count": 0,
            }

        def read_published_calls(
            self,
            pair: str,
            *,
            limit: int | None,
        ) -> Sequence[Mapping[str, Any]]:
            calls = self.calls if limit is None else self.calls[-limit:]
            return [
                {
                    "call_id": index + 1,
                    "date": call.date,
                    "pair": call.pair,
                    "regime": call.regime,
                    "predicted_direction": call.predicted_direction,
                    "confidence": call.confidence,
                }
                for index, call in enumerate(calls)
                if call.pair == pair
            ]

        def read_validation_entry(
            self,
            call_id: int | str,
        ) -> Mapping[str, Any] | None:
            return next(
                (
                    row
                    for row in reversed(self.validation_rows)
                    if row.get("call_id") == call_id
                ),
                None,
            )

        def get_publication_signal_for_call(
            self,
            call_id: int,
        ) -> Mapping[str, Any] | None:
            del call_id
            return None

        def get_exact_historical_price_for_date(
            self,
            pair: str,
            date_str: str,
        ) -> Mapping[str, Any] | None:
            del pair, date_str
            return None

        def publish_regime_call(
            self,
            call: RegimeCall,
            signal_row: SignalRow,
            *,
            correlation_id: str | None = None,
        ) -> int | str | None:
            del correlation_id
            self.calls.append(call)
            self.signal_rows.append(signal_row)
            return len(self.calls)

        def write_regime_call(
            self,
            call: RegimeCall,
            *,
            correlation_id: str | None = None,
            write_hash: str | None = None,
        ) -> int | str | None:
            self.calls.append(call)
            return len(self.calls)

        def write_signal_row(self, row: SignalRow) -> None:
            self.signal_rows.append(row)

        def write_validation_rows(
            self,
            rows: Sequence[Mapping[str, Any]],
        ) -> None:
            self.validation_rows.extend(rows)

    writer = FakeWriter()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="NEUTRAL",
        confidence=0.6,
        signal_composite=0.1,
        rate_signal="NEUTRAL",
    )
    signal_row = SignalRow(
        pair="EURUSD",
        date=date(2026, 5, 20),
        rate_diff_2y=None,
        rate_diff_10y=None,
        cot_percentile=None,
        realized_vol_20d=None,
        realized_vol_5d=None,
        implied_vol_30d=None,
        spot=1.08,
        day_change=None,
        day_change_pct=None,
        cross_asset_vix=None,
        cross_asset_dxy=None,
        cross_asset_oil=None,
        cross_asset_us10y=None,
        cross_asset_gold=None,
        cross_asset_copper=None,
        cross_asset_stoxx=None,
        oi_delta=None,
        data_quality_notes=["COT unavailable"],
    )
    call_id = writer.publish_regime_call(call, signal_row, correlation_id="abc-123")
    writer.write_validation_rows([{"pair": "EURUSD", "date": "2026-05-20"}])

    assert call_id == 1
    assert writer.calls == [call]
    assert writer.signal_rows == [signal_row]
    assert writer.validation_rows == [{"pair": "EURUSD", "date": "2026-05-20"}]
    assert writer.read_published_calls("EURUSD", limit=None)[0]["call_id"] == 1
    assert writer.read_validation_entry(1) is None


def test_alert_port_can_be_subclassed() -> None:
    """AlertPort defines narrow alert methods that can be implemented."""

    class FakeAlert(AlertPort):
        def __init__(self) -> None:
            self.heartbeats: list[dict[str, Any]] = []
            self.successes: list[RegimeCall] = []
            self.low_dqs: list[dict[str, Any]] = []
            self.statuses: list[dict[str, Any]] = []

        def send_heartbeat(
            self,
            as_of: date,
            *,
            pairs_processed: int,
            regime_calls_count: int,
            dqs_score: float,
        ) -> None:
            self.heartbeats.append(
                {
                    "as_of": as_of,
                    "pairs_processed": pairs_processed,
                    "regime_calls_count": regime_calls_count,
                    "dqs_score": dqs_score,
                }
            )

        def send_success(self, call: RegimeCall) -> None:
            self.successes.append(call)

        def send_status(
            self,
            as_of: date,
            health: StageHealth,
            *,
            pair: str | None = None,
        ) -> None:
            self.statuses.append({"as_of": as_of, "health": health, "pair": pair})

        def send_low_dqs(
            self,
            as_of: date,
            dqs_score: float,
            stale_sources: list[str],
        ) -> None:
            self.low_dqs.append(
                {
                    "as_of": as_of,
                    "dqs_score": dqs_score,
                    "stale_sources": stale_sources,
                }
            )

    alert = FakeAlert()
    call = RegimeCall(
        pair="EURUSD",
        date=date(2026, 5, 20),
        regime="NEUTRAL",
        confidence=0.6,
        signal_composite=0.1,
        rate_signal="NEUTRAL",
    )
    alert.send_success(call)
    alert.send_heartbeat(
        date(2026, 5, 20),
        pairs_processed=3,
        regime_calls_count=3,
        dqs_score=0.95,
    )
    alert.send_low_dqs(date(2026, 5, 20), 0.55, ["cot"])
    health = StageHealth("SignalStage", "DEGRADED", missing_fields=["cot"])
    alert.send_status(date(2026, 5, 20), health, pair="EURUSD")

    assert alert.successes == [call]
    assert alert.heartbeats[0]["pairs_processed"] == 3
    assert alert.low_dqs[0]["stale_sources"] == ["cot"]
    assert alert.statuses == [
        {"as_of": date(2026, 5, 20), "health": health, "pair": "EURUSD"}
    ]
