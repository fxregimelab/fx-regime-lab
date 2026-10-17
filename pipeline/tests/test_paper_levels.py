"""Tests for the desk liquidity & structure map (pure; synthetic bars)."""

from __future__ import annotations

import pytest

from src.paper.levels import (
    Level,
    build_liquidity_map,
    distance_to_nearest,
    find_swings,
    nearest_level,
    recent_extremes,
    round_levels,
    significant_only,
)
from src.paper.store import Bar


def _bar(t: int, high: float, low: float, tf: str = "H1") -> Bar:
    close = (high + low) / 2.0
    return Bar(
        symbol="EURUSDm",
        timeframe=tf,
        time_srv=t,
        open=close,
        high=high,
        low=low,
        close=close,
        tick_volume=10,
        spread_points=8,
    )


def _tags_near(levels: list[Level], price: float) -> tuple[str, ...]:
    for lv in levels:
        if abs(lv.price - price) < 1e-9:
            return lv.tags
    raise AssertionError(f"no level near {price}")


def test_find_swings_detects_unique_fractals() -> None:
    highs = [1.0, 2.0, 3.0, 10.0, 4.0, 3.0, 2.0, 1.0, 1.0]
    lows = [5.0, 5.0, 5.0, 5.0, 5.0, 4.0, 5.0, 5.0, 5.0]
    bars = [_bar(i, highs[i], lows[i]) for i in range(9)]
    swings = find_swings(bars, k=2)
    assert [(s.kind, s.price) for s in swings] == [("high", 10.0), ("low", 4.0)]


def test_find_swings_rejects_ties() -> None:
    highs = [1.0, 2.0, 10.0, 10.0, 4.0, 3.0, 2.0]
    bars = [_bar(i, highs[i], 0.5) for i in range(7)]
    assert find_swings(bars, k=2) == []


def test_round_levels_eurusd_merges_major_and_minor() -> None:
    levels = round_levels("EURUSD", 1.1234, span=1)
    assert [lv.price for lv in levels] == pytest.approx([1.11, 1.115, 1.12, 1.125, 1.13])
    assert _tags_near(levels, 1.12) == ("round_major", "round_minor")
    assert _tags_near(levels, 1.115) == ("round_minor",)
    assert _tags_near(levels, 1.11) == ("round_major",)


def test_round_levels_usdjpy() -> None:
    levels = round_levels("USDJPY", 157.3, span=1)
    assert [lv.price for lv in levels] == pytest.approx([156.0, 156.5, 157.0, 157.5, 158.0])
    assert _tags_near(levels, 157.0) == ("round_major", "round_minor")
    assert _tags_near(levels, 156.5) == ("round_minor",)


def test_recent_extremes_and_empty() -> None:
    bars = [_bar(1, 1.10, 1.00), _bar(2, 1.20, 0.95), _bar(3, 1.05, 1.02)]
    assert recent_extremes(bars, 2) == (1.20, 0.95)
    assert recent_extremes([], 5) is None


def test_build_liquidity_map_sorted_and_tagged() -> None:
    h1 = [_bar(i, c, c - 0.0020) for i, c in enumerate(
        [1.1000, 1.1005, 1.1010, 1.1005, 1.1000]
    )]
    h4_highs = [1.1000, 1.1010, 1.1020, 1.1030, 1.1040, 1.1030, 1.1020, 1.1010, 1.1000, 1.0990]
    h4 = [_bar(i, h, h - 0.0020, tf="H4") for i, h in enumerate(h4_highs)]
    levels = build_liquidity_map({"H1": h1, "H4": h4}, "EURUSD")
    prices = [lv.price for lv in levels]
    assert prices == sorted(prices)
    tags = {t for lv in levels for t in lv.tags}
    assert {"swing_h1", "swing_h4", "session_ext", "round_major", "round_minor"} <= tags


def test_significant_only_filters_minor_rounds() -> None:
    levels = [
        Level(1.10, ("round_minor",)),
        Level(1.1050, ("round_minor", "round_major")),
        Level(1.1010, ("swing_h1", "high")),
        Level(1.0990, ("session_ext", "low")),
    ]
    assert significant_only(levels) == [levels[1], levels[2], levels[3]]


def test_nearest_level_and_distance() -> None:
    levels = [Level(1.0, ("x",)), Level(1.1, ("x",)), Level(1.15, ("x",)), Level(1.2, ("x",))]
    above = nearest_level(levels, 1.12, "above")
    below = nearest_level(levels, 1.12, "below")
    assert above is not None and above.price == 1.15
    assert below is not None and below.price == 1.1
    assert distance_to_nearest(levels, 1.12, "above") == pytest.approx(0.03)
    assert nearest_level(levels, 2.0, "above") is None
