"""Provider evidence remains distinct from a verified completed close."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.core.price_archive import prepare_price_observations
from src.db.writer import archive_price_observations
from src.fetchers.fx_spot import (
    _bars_from_yf_frame,
    _parse_av_fx_daily,
    _parse_polygon_aggs,
    fetch_fx_spot_async,
)
from src.types import SpotBar

DAY = date(2024, 1, 15)
RECEIPT = datetime(2024, 1, 16, 12, tzinfo=UTC)


def observation(**changes: Any) -> SpotBar:
    return replace(
        SpotBar(
            DAY,
            "EURUSD",
            1.0,
            1.1,
            0.9,
            1.05,
            10.0,
            provider="polygon",
            instrument="C:EURUSD",
            retrieved_at=RECEIPT,
            provider_timestamp=datetime(2024, 1, 15, tzinfo=UTC),
            provider_metadata={"raw_timestamp_ms": 1705276800000},
        ),
        **changes,
    )


def test_archive_preserves_revisions_and_detaches_metadata() -> None:
    bar = observation()
    batch = prepare_price_observations(
        {"EURUSD": [bar, replace(bar, close=1.06)]}, as_of=DAY, cutoff=RECEIPT
    )
    assert len(batch.observations) == 2
    assert batch.unknown_session_count == 2
    assert batch.observations[0]["window_end"] is None
    assert batch.observations[0]["retrieved_at"] == "2024-01-16T12:00:00+00:00"
    bar.provider_metadata["raw_timestamp_ms"] = 0
    assert batch.observations[0]["provider_metadata"]["raw_timestamp_ms"] == 1705276800000


def test_absent_metadata_is_counted_without_inventing_a_retrieval() -> None:
    old = SpotBar(DAY, "EURUSD", 1.0, 1.1, 0.9, 1.05)
    batch = prepare_price_observations(
        {"EURUSD": [old, observation(date=DAY + timedelta(days=1))]}, as_of=DAY, cutoff=RECEIPT
    )
    assert batch.observations == ()
    assert batch.missing_metadata_count == batch.future_count == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"pair": "USDJPY"},
        {"provider": "unknown"},
        {"instrument": " "},
        {"close": True},
        {"close": float("inf")},
        {"low": 1.2},
        {"volume": -1},
        {"retrieved_at": RECEIPT.replace(tzinfo=None)},
        {"retrieved_at": RECEIPT + timedelta(seconds=1)},
        {"provider_timestamp": RECEIPT + timedelta(seconds=1)},
        {"window_start": RECEIPT},
        {"window_start": RECEIPT, "window_end": RECEIPT},
        {"provider_metadata": {"apiKey": "should-not-be-archived"}},
        {"provider_metadata": {"request_id": {"nested": "no"}}},
        {"provider_metadata": {"raw_timestamp_ms": float("nan")}},
        {"session_timezone": ""},
    ],
)
def test_invalid_observations_are_visible(changes: dict[str, Any]) -> None:
    batch = prepare_price_observations(
        {"EURUSD": [observation(**changes)]}, as_of=DAY, cutoff=RECEIPT
    )
    assert batch.invalid_count == 1
    assert not batch.observations


def test_open_explicit_window_is_archived_without_claiming_finality() -> None:
    bar = observation(
        window_start=RECEIPT - timedelta(hours=1),
        window_end=RECEIPT + timedelta(hours=1),
        session_timezone="UTC",
        session_definition="test-window",
    )
    batch = prepare_price_observations({"EURUSD": [bar]}, as_of=DAY, cutoff=RECEIPT)
    assert len(batch.observations) == 1
    assert batch.unknown_session_count == 0
    assert "validation_eligible" not in batch.observations[0]


def polygon_row(**changes: Any) -> dict[str, Any]:
    return {"o": 1.0, "h": 1.1, "l": 0.9, "c": 1.05, "t": 1705276800000, **changes}


@pytest.mark.parametrize("hour,minute,second", [(0, 0, 0), (23, 59, 59)])
def test_polygon_epoch_is_utc_and_retains_source_without_assuming_session(
    hour: int, minute: int, second: int,
) -> None:
    instant = datetime(2024, 1, 15, hour, minute, second, tzinfo=UTC)
    data = {
        "ticker": "C:EURUSD",
        "request_id": "request-1",
        "results": [polygon_row(t=int(instant.timestamp()) * 1000)],
        "apiKey": "not-metadata",
    }
    bar = _parse_polygon_aggs("EURUSD", data, retrieved_at=RECEIPT)[0]
    assert bar.date == DAY
    assert bar.provider_timestamp == instant
    assert bar.session_timezone is None and bar.window_end is None
    assert bar.provider_metadata["request_id"] == "request-1"
    assert "apiKey" not in bar.provider_metadata
    assert bar.volume_source == "polygon"


@pytest.mark.parametrize(
    "row",
    [
        polygon_row(c=True),
        polygon_row(v=True),
        polygon_row(h=0.8),
        polygon_row(c="nan"),
        polygon_row(t=999999999999999999),
    ],
)
def test_polygon_rejects_invalid_rows(row: dict[str, Any]) -> None:
    assert not _parse_polygon_aggs("EURUSD", {"results": [row]}, retrieved_at=RECEIPT)


def test_av_preserves_metadata_and_strict_date_labels() -> None:
    row = {"1. open": "1", "2. high": "1.1", "3. low": ".9", "4. close": "1.05"}
    data: dict[str, Any] = {
        "Meta Data": {
            "2. From Symbol": "EUR",
            "3. To Symbol": "USD",
            "6. Time Zone": "UTC",
            "4. Last Refreshed": "2024-01-15",
        },
        "Time Series FX (Daily)": {"2024-01-15": row, "2024-01-15T12:00": row},
    }
    bars = _parse_av_fx_daily("EURUSD", data, retrieved_at=RECEIPT)
    assert len(bars) == 1
    assert bars[0].session_timezone == "UTC"
    assert bars[0].provider_timestamp is None and bars[0].window_end is None
    data["Meta Data"]["2. From Symbol"] = "GBP"
    assert not _parse_av_fx_daily("EURUSD", data, retrieved_at=RECEIPT)


@pytest.mark.parametrize("zone", [None, "Asia/Kolkata"])
def test_yahoo_retains_index_label_without_inventing_window(zone: str | None) -> None:
    frame = pd.DataFrame(
        {"Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [12.0]},
        index=pd.DatetimeIndex(["2024-01-15"], tz=zone),
    )
    bar = _bars_from_yf_frame(frame, "EURUSD", "EURUSD=X", retrieved_at=RECEIPT)[0]
    assert bar.date == DAY and bar.session_timezone == zone
    assert (bar.provider_timestamp is None) == (zone is None)
    assert bar.window_start is None and bar.window_end is None
    assert bar.volume_instrument == "EURUSD=X"


def test_writer_sends_one_atomic_rpc_and_checks_receipt() -> None:
    row = prepare_price_observations(
        {"EURUSD": [observation()]}, as_of=DAY, cutoff=RECEIPT
    ).observations[0]
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = {
        "observation_ids": [7, 7],
        "inserted_count": 1,
        "existing_count": 1,
    }
    with patch("src.db.writer._client", return_value=client):
        receipt = archive_price_observations([row, row])
    assert receipt["observation_ids"] == [7, 7]
    client.rpc.assert_called_once_with("append_price_observations", {"p_observations": [row, row]})
    client.table.assert_not_called()


@pytest.mark.parametrize(
    "result",
    [
        None,
        [],
        {},
        {"observation_ids": [True], "inserted_count": 1, "existing_count": 0},
        {"observation_ids": [1], "inserted_count": True, "existing_count": 0},
        {"observation_ids": [1], "inserted_count": 0, "existing_count": 0},
        {"observation_ids": [-1], "inserted_count": 1, "existing_count": 0},
    ],
)
def test_writer_rejects_invalid_receipts(result: Any) -> None:
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = result
    with patch("src.db.writer._client", return_value=client), pytest.raises(RuntimeError):
        archive_price_observations([{}])


def test_writer_propagates_failure_and_rejects_nonfinite_json_locally() -> None:
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = RuntimeError("archive unavailable")
    with patch("src.db.writer._client", return_value=client):
        with pytest.raises(RuntimeError, match="archive unavailable"):
            archive_price_observations([{}])
        with pytest.raises(ValueError):
            archive_price_observations([{"close": float("nan")}])
    client.rpc.assert_called_once()
    client.table.assert_not_called()


def test_volume_proxy_keeps_its_own_source_identity() -> None:
    spot = observation(volume_source="polygon", volume_instrument="C:EURUSD")
    proxy = observation(provider="yahoo", instrument="6E=F", volume=200.0)
    universe = {
        "EURUSD": {
            "class": "FX",
            "tickers": {
                "spot_ticker": "EURUSD=X",
                "volume_ticker": "6E=F",
            },
        }
    }
    with (
        patch("src.fetchers.fx_spot.fetch_fx_spot_polygon", return_value=[spot]),
        patch(
            "src.fetchers.fx_spot._fetch_one_spot_async",
            new=AsyncMock(return_value=("EURUSD", [proxy])),
        ),
    ):
        bars = asyncio.run(fetch_fx_spot_async(universe, MagicMock()))
    result = bars["EURUSD"][0]
    assert result.provider == "polygon" and result.instrument == "C:EURUSD"
    assert result.volume == 200.0
    assert result.volume_source == "yahoo" and result.volume_instrument == "6E=F"
