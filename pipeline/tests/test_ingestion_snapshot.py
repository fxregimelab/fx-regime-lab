"""IngestionSnapshot adapter edge-case tests."""

from __future__ import annotations

import datetime

from src.core.ingestion_snapshot import IngestionSnapshot
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
                {"date": "2026-01-15", "pair": "EURUSD", "close": 0.0},
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
