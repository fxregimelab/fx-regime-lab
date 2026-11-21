"""IngestionSnapshot adapter edge-case tests."""

from __future__ import annotations

import datetime

import pytest

from src.core.ingestion_snapshot import IngestionSnapshot
from src.core.spot_history import SpotHistoryError
from src.fetchers.buffer_keys import KEY_COT, KEY_CROSS_ASSET, KEY_FX_SPOT, KEY_YIELDS
from src.types import CotRow, SpotBar


def _bar(*, pair: str = "EURUSD", close: float = 1.1) -> SpotBar:
    d = datetime.date(2026, 1, 15)
    return SpotBar(date=d, pair=pair, open=close, high=close, low=close, close=close)


def test_from_buffer_empty_defaults() -> None:
    """Missing fetcher outputs become safe defaults, not crashes."""

    snapshot = IngestionSnapshot.from_buffer(
        datetime.date(2026, 1, 15),
        {},
    )
    assert snapshot.spots == {}
    assert snapshot.yields == {}
    assert snapshot.cot_rows == []
    assert snapshot.cross_asset == {
        "vix": None,
        "dxy": None,
        "oil": None,
        "gold": None,
        "copper": None,
        "stoxx": None,
    }


def test_from_buffer_partial_spots() -> None:
    """Partial spot buffer is coerced; malformed bars are dropped."""

    buffer = {
        KEY_FX_SPOT: {
            "EURUSD": [
                _bar(pair="EURUSD", close=1.1),
                {"date": "not-a-date", "pair": "EURUSD", "close": 1.2},
            ],
            "USDJPY": "not-a-list",
        },
    }
    snapshot = IngestionSnapshot.from_buffer(datetime.date(2026, 1, 15), buffer)
    assert list(snapshot.spots.keys()) == ["EURUSD"]
    assert len(snapshot.spots["EURUSD"]) == 1
    assert snapshot.spots["EURUSD"][0].close == 1.1


def test_from_buffer_malformed_yields() -> None:
    """Non-float yield values are coerced to None."""

    buffer = {
        KEY_YIELDS: {
            "us_2y": 4.0,
            "de_2y": "n/a",
            "us_10y": None,
        },
    }
    snapshot = IngestionSnapshot.from_buffer(datetime.date(2026, 1, 15), buffer)
    assert snapshot.yields["us_2y"] == 4.0
    assert snapshot.yields["de_2y"] is None
    assert snapshot.yields["us_10y"] is None


def test_from_buffer_malformed_cot() -> None:
    """Malformed COT rows are dropped; valid rows survive."""

    buffer = {
        KEY_COT: [
            CotRow(
                date=datetime.date(2026, 1, 13),
                pair="EURUSD",
                net_long=10000,
                open_interest=20000,
            ),
            {"date": "bad-date", "pair": "EURUSD", "net_long": 10000},
            {"pair": "EURUSD", "net_long": "not-a-number"},
        ],
    }
    snapshot = IngestionSnapshot.from_buffer(datetime.date(2026, 1, 15), buffer)
    assert len(snapshot.cot_rows) == 1
    assert snapshot.cot_rows[0].net_long == 10000


def test_from_buffer_cross_asset_defaults() -> None:
    """Unknown cross-asset legs are ignored; known legs default to None."""

    buffer = {
        KEY_CROSS_ASSET: {
            "vix": 18.0,
            "dxy": "high",
            "bitcoin": 100000.0,
        },
    }
    snapshot = IngestionSnapshot.from_buffer(datetime.date(2026, 1, 15), buffer)
    assert snapshot.cross_asset["vix"] == 18.0
    assert snapshot.cross_asset["dxy"] is None
    assert "bitcoin" not in snapshot.cross_asset


def test_today_bar_matching_date() -> None:
    """today_bar_for returns the bar matching the snapshot date."""

    d1 = datetime.date(2026, 1, 14)
    d2 = datetime.date(2026, 1, 15)
    bar1 = SpotBar(date=d1, pair="EURUSD", open=1.0, high=1.0, low=1.0, close=1.0)
    bar2 = SpotBar(date=d2, pair="EURUSD", open=1.1, high=1.1, low=1.1, close=1.1)
    snapshot = IngestionSnapshot(
        date=d2,
        spots={"EURUSD": (bar1, bar2)},
        yields={},
        cot_rows=[],
        cross_asset={},
    )
    assert snapshot.today_bar_for("EURUSD") is bar2


def test_today_bar_falls_back_to_latest() -> None:
    """today_bar_for falls back to the latest bar if snapshot date is not present."""

    d1 = datetime.date(2026, 1, 14)
    d2 = datetime.date(2026, 1, 15)
    bar1 = SpotBar(date=d1, pair="EURUSD", open=1.0, high=1.0, low=1.0, close=1.0)
    snapshot = IngestionSnapshot(
        date=d2,
        spots={"EURUSD": (bar1,)},
        yields={},
        cot_rows=[],
        cross_asset={},
    )
    assert snapshot.today_bar_for("EURUSD") is bar1


def test_yesterday_bar_returns_earlier_bar() -> None:
    """yesterday_bar_for returns the bar immediately preceding today."""

    d1 = datetime.date(2026, 1, 14)
    d2 = datetime.date(2026, 1, 15)
    bar1 = SpotBar(date=d1, pair="EURUSD", open=1.0, high=1.0, low=1.0, close=1.0)
    bar2 = SpotBar(date=d2, pair="EURUSD", open=1.1, high=1.1, low=1.1, close=1.1)
    snapshot = IngestionSnapshot(
        date=d2,
        spots={"EURUSD": (bar1, bar2)},
        yields={},
        cot_rows=[],
        cross_asset={},
    )
    assert snapshot.yesterday_bar_for("EURUSD") is bar1


def test_yesterday_bar_single_bar_returns_none() -> None:
    """yesterday_bar_for returns None when there is no preceding bar."""

    d1 = datetime.date(2026, 1, 14)
    bar1 = SpotBar(date=d1, pair="EURUSD", open=1.0, high=1.0, low=1.0, close=1.0)
    snapshot = IngestionSnapshot(
        date=d1,
        spots={"EURUSD": (bar1,)},
        yields={},
        cot_rows=[],
        cross_asset={},
    )
    assert snapshot.yesterday_bar_for("EURUSD") is None


def test_yesterday_bar_missing_pair_returns_none() -> None:
    """yesterday_bar_for returns None when the pair has no bars."""

    snapshot = IngestionSnapshot(
        date=datetime.date(2026, 1, 15),
        spots={},
        yields={},
        cot_rows=[],
        cross_asset={},
    )
    assert snapshot.yesterday_bar_for("EURUSD") is None


def test_from_buffer_rejects_conflicting_duplicate_spot_rows() -> None:
    buffer = {
        KEY_FX_SPOT: {
            "EURUSD": [
                {
                    "date": "2026-01-15",
                    "pair": "EURUSD",
                    "open": 1.1,
                    "high": 1.1,
                    "low": 1.1,
                    "close": 1.1,
                },
                {
                    "date": "2026-01-15",
                    "pair": "EURUSD",
                    "open": 1.2,
                    "high": 1.2,
                    "low": 1.2,
                    "close": 1.2,
                },
            ]
        }
    }

    with pytest.raises(SpotHistoryError, match="Conflicting EURUSD spot rows"):
        IngestionSnapshot.from_buffer(datetime.date(2026, 1, 15), buffer)


def test_from_buffer_rejects_timestamp_instead_of_truncating_it() -> None:
    buffer = {
        KEY_FX_SPOT: {
            "EURUSD": [
                {
                    "date": "2026-01-15T23:59:59Z",
                    "pair": "EURUSD",
                    "close": 1.1,
                }
            ]
        }
    }

    snapshot = IngestionSnapshot.from_buffer(datetime.date(2026, 1, 15), buffer)
    assert snapshot.spots == {}


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"open": None}, "spot.open is required"),
        ({"high": True}, "spot.high must be a finite number"),
        ({"low": float("nan")}, "spot.low must be a finite number"),
        ({"close": float("inf")}, "spot.close must be a finite number"),
        ({"close": "bad"}, "spot.close must be a finite number"),
        ({"close": 0.0}, "spot.close must be positive"),
        ({"volume": -1.0}, "spot.volume must be nonnegative"),
    ],
)
def test_from_buffer_rejects_invalid_dict_prices(
    overrides: dict[str, object], message: str
) -> None:
    row: dict[str, object] = {
        "date": "2026-01-15",
        "pair": "EURUSD",
        "open": 1.0,
        "high": 1.2,
        "low": 0.9,
        "close": 1.1,
        "volume": 10.0,
    }
    row.update(overrides)

    with pytest.raises(SpotHistoryError, match=message):
        IngestionSnapshot.from_buffer(
            datetime.date(2026, 1, 15),
            {KEY_FX_SPOT: {"EURUSD": [row]}},
        )


@pytest.mark.parametrize("missing", ["open", "high", "low", "close"])
def test_from_buffer_does_not_fabricate_missing_ohlc(missing: str) -> None:
    row: dict[str, object] = {
        "date": "2026-01-15",
        "pair": "EURUSD",
        "open": 1.0,
        "high": 1.2,
        "low": 0.9,
        "close": 1.1,
    }
    del row[missing]

    with pytest.raises(SpotHistoryError, match=rf"spot\.{missing} is required"):
        IngestionSnapshot.from_buffer(
            datetime.date(2026, 1, 15),
            {KEY_FX_SPOT: {"EURUSD": [row]}},
        )


def test_today_and_yesterday_ignore_future_and_sort_input() -> None:
    as_of = datetime.date(2026, 1, 15)
    earlier = SpotBar(
        date=datetime.date(2026, 1, 14),
        pair="EURUSD",
        open=1.0,
        high=1.0,
        low=1.0,
        close=1.0,
    )
    latest = SpotBar(
        date=as_of,
        pair="EURUSD",
        open=1.1,
        high=1.1,
        low=1.1,
        close=1.1,
    )
    future = SpotBar(
        date=datetime.date(2026, 1, 16),
        pair="EURUSD",
        open=9.0,
        high=9.0,
        low=9.0,
        close=9.0,
    )
    snapshot = IngestionSnapshot(
        date=as_of,
        spots={"EURUSD": (future, latest, earlier)},
        yields={},
        cot_rows=[],
        cross_asset={},
    )

    assert snapshot.today_bar_for("EURUSD") is latest
    assert snapshot.yesterday_bar_for("EURUSD") is earlier


def test_from_buffer_preserves_provider_metadata_fields() -> None:
    retrieved_at = datetime.datetime(2026, 1, 15, 12, tzinfo=datetime.UTC)
    provider_timestamp = datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC)
    buffer = {
        KEY_FX_SPOT: {
            "EURUSD": [
                {
                    "date": "2026-01-15",
                    "pair": "EURUSD",
                    "open": 1.0,
                    "high": 1.2,
                    "low": 0.9,
                    "close": 1.1,
                    "volume": 10.0,
                    "provider": "polygon",
                    "instrument": "C:EURUSD",
                    "retrieved_at": retrieved_at,
                    "provider_timestamp": provider_timestamp,
                    "session_timezone": "UTC",
                    "provider_metadata": {"date_label_policy": "timestamp_utc_date"},
                    "volume_source": "cme",
                    "volume_instrument": "6E",
                }
            ]
        }
    }

    snapshot = IngestionSnapshot.from_buffer(datetime.date(2026, 1, 15), buffer)
    bar = snapshot.spots["EURUSD"][0]

    assert bar.provider == "polygon"
    assert bar.instrument == "C:EURUSD"
    assert bar.retrieved_at is retrieved_at
    assert bar.provider_timestamp is provider_timestamp
    assert bar.provider_metadata == {"date_label_policy": "timestamp_utc_date"}
    assert bar.volume_source == "cme"
    assert bar.volume_instrument == "6E"
