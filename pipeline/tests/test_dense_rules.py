"""Tests for the interpretable dense rule baselines (research only)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np

from src.paper.backtest.dense import FEATURE_NAMES, DenseConfig, FeatureFrame
from src.paper.backtest.rules import (
    _asian_ranges,
    evaluate_signals,
    london_breakout,
    mean_reversion,
)
from src.paper.features import OHLCBar

MONDAY = datetime(2024, 3, 4, tzinfo=UTC)


def _bar(minutes: int, *, open_: float, high: float, low: float, close: float) -> OHLCBar:
    return OHLCBar(
        timestamp=MONDAY + timedelta(minutes=minutes),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1.0,
    )


def _frame(n: int, atr: float = 0.0010) -> FeatureFrame:
    return FeatureFrame(
        times=tuple(MONDAY + timedelta(minutes=15 * i) for i in range(n)),
        base=np.zeros((n, len(FEATURE_NAMES)), dtype=np.float64),
        atr=np.full(n, atr, dtype=np.float64),
        valid=np.ones(n, dtype=np.bool_),
    )


def test_asian_range_covers_only_the_pre_london_window() -> None:
    bars = [
        _bar(15, open_=1.1000, high=1.1005, low=1.0995, close=1.1000),
        _bar(30, open_=1.1000, high=1.1010, low=1.0990, close=1.1005),
        _bar(7 * 60, open_=1.1005, high=1.1020, low=1.1000, close=1.1015),
    ]
    ranges = _asian_ranges(bars)
    high, low = ranges[MONDAY.date()]
    assert high == 1.1010
    assert low == 1.0990


def test_london_breakout_requires_the_first_close_beyond_the_range() -> None:
    bars: list[OHLCBar] = []
    # 00:15-06:45 range: high 1.1010, low 1.0990
    for i in range(27):
        bars.append(
            _bar(15 * (i + 1), open_=1.1000, high=1.1010, low=1.0990, close=1.1000)
        )
    # 07:00 breakout close above the range
    bars.append(_bar(7 * 60, open_=1.1000, high=1.1016, low=1.0999, close=1.1015))
    # 07:15 another close above: not a fresh breakout
    bars.append(_bar(7 * 60 + 15, open_=1.1015, high=1.1020, low=1.1012, close=1.1018))

    frame = _frame(len(bars))
    signals = london_breakout(bars, frame)
    assert signals == [(27, 1)]


def test_london_breakout_ignores_narrow_ranges() -> None:
    bars: list[OHLCBar] = []
    for i in range(27):
        bars.append(
            _bar(15 * (i + 1), open_=1.1000, high=1.1001, low=1.0999, close=1.1000)
        )
    bars.append(_bar(7 * 60, open_=1.1000, high=1.1005, low=1.0999, close=1.1004))
    frame = _frame(len(bars), atr=0.0100)  # range 0.0002 < 0.5 * 0.0100
    assert london_breakout(bars, frame) == []


def test_mean_reversion_fades_a_stretched_band() -> None:
    bars = [
        _bar(15 * (i + 1), open_=1.1000, high=1.1002, low=1.0998, close=1.1000)
        for i in range(40)
    ]
    frame = _frame(len(bars))
    # index 30: bb_z = -2.5, RSI = 25 -> long
    frame.base[30, 6] = -2.5
    frame.base[30, 5] = (25.0 - 50.0) / 50.0
    signals = mean_reversion(bars, frame)
    assert signals == [(30, 1)]


def test_evaluate_signals_pays_costs_and_respects_one_position() -> None:
    bars = [
        _bar(0, open_=1.1000, high=1.1005, low=1.0995, close=1.1000),
        _bar(15, open_=1.1000, high=1.1005, low=1.0995, close=1.1000),
        _bar(30, open_=1.1000, high=1.1006, low=1.0996, close=1.1001),
        _bar(45, open_=1.1001, high=1.1005, low=1.0997, close=1.1002),
    ]
    frame = _frame(len(bars))
    cfg = DenseConfig(stop_atr_mult=1.0, target_r=2.0, max_hold_bars=2)
    trades = evaluate_signals("EURUSD", bars, frame, [(0, 1), (1, 1)], cfg=cfg)
    assert len(trades) == 1
    trade = trades[0]
    assert trade.cost_r > 0.0
    assert trade.net_r == trade.gross_r - trade.cost_r
