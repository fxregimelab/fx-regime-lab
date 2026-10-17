"""Tests for desk bar validation + sync (pure logic; no terminal needed)."""

from __future__ import annotations

from pathlib import Path

from src.paper.prices import sync_bars, validate_bars
from src.paper.store import Bar, DeskStore


def _bar(t: int, o: float, h: float, lo: float, c: float) -> Bar:
    return Bar(
        symbol="EURUSDm",
        timeframe="D1",
        time_srv=t,
        open=o,
        high=h,
        low=lo,
        close=c,
        tick_volume=10,
        spread_points=8,
    )


def test_valid_bars_pass() -> None:
    result = validate_bars([_bar(1, 1.0, 1.1, 0.95, 1.05), _bar(2, 1.05, 1.2, 1.0, 1.1)])
    assert len(result.clean) == 2
    assert not result.quarantined


def test_out_of_order_input_sorted() -> None:
    late = _bar(2, 1.05, 1.2, 1.0, 1.1)
    early = _bar(1, 1.0, 1.1, 0.95, 1.05)
    result = validate_bars([late, early])
    assert [b.time_srv for b in result.clean] == [1, 2]


def test_duplicate_time_keeps_later_bar() -> None:
    first = _bar(1, 1.0, 1.1, 0.95, 1.05)
    second = _bar(1, 1.0, 1.1, 0.95, 1.06)
    result = validate_bars([first, second])
    assert len(result.clean) == 1
    assert result.clean[0].close == 1.06


def test_high_below_body_rejected() -> None:
    result = validate_bars([_bar(1, 1.0, 0.99, 0.95, 1.05)])
    assert not result.clean
    assert result.quarantined[0][1] == "high_below_body"


def test_low_above_body_rejected() -> None:
    result = validate_bars([_bar(1, 1.0, 1.1, 1.01, 1.05)])
    assert not result.clean
    assert result.quarantined[0][1] == "low_above_body"


def test_nonpositive_or_nan_price_rejected() -> None:
    zero = validate_bars([_bar(1, 0.0, 1.1, 0.95, 1.05)])
    assert not zero.clean
    assert zero.quarantined[0][1].startswith("bad_")
    nan = validate_bars([_bar(1, 1.0, float("nan"), 0.95, 1.05)])
    assert not nan.clean
    assert nan.quarantined[0][1].startswith("bad_")


def test_day_jump_quarantined_against_last_clean() -> None:
    a = _bar(1, 1.0, 1.05, 0.98, 1.0)
    b = _bar(2, 1.0, 1.5, 0.99, 1.4)  # +40%: quarantined
    c = _bar(3, 1.01, 1.03, 1.0, 1.02)  # +2% vs last clean bar (a): clean
    result = validate_bars([a, b, c])
    assert [x.close for x in result.clean] == [1.0, 1.02]
    assert len(result.quarantined) == 1
    assert result.quarantined[0][1].startswith("day_move")


def test_sync_bars_upserts_clean_only(tmp_path: Path) -> None:
    with DeskStore(tmp_path / "paper_desk.sqlite3") as store:
        bars = [
            _bar(1, 1.0, 1.05, 0.98, 1.0),
            _bar(2, 1.0, 1.5, 0.99, 1.4),  # quarantined
            _bar(3, 1.01, 1.03, 1.0, 1.02),
        ]
        report = sync_bars(store, "EURUSD", "EURUSDm", bars, timeframe="D1")
        assert report.fetched == 3
        assert report.stored == 2
        assert len(report.quarantined) == 1
        assert report.pair == "EURUSD"
        assert report.symbol == "EURUSDm"
        assert [b.close for b in store.bars("EURUSDm", "D1")] == [1.0, 1.02]
