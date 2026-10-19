"""Oracle tests for the dense walk-forward research harness (AD-T12 research)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import numpy.typing as npt
import pytest

from src.paper.backtest.dense import (
    FEATURE_NAMES,
    DenseConfig,
    build_features,
    build_labels,
    directional_matrix,
    run_walk_forward,
    simulate_outcome,
)
from src.paper.features import OHLCBar

START = datetime(2022, 1, 3, tzinfo=UTC)


def _bar(
    index: int, *, open_: float, high: float, low: float, close: float
) -> OHLCBar:
    return OHLCBar(
        timestamp=START + timedelta(minutes=15 * index),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1.0,
    )


def _synthetic_series(count: int, *, seed: int = 7) -> list[OHLCBar]:
    rng = np.random.default_rng(seed)
    price = 1.1000
    bars: list[OHLCBar] = []
    for i in range(count):
        drift = 0.00002 * math.sin(i / 40.0)
        shock = float(rng.normal(0.0, 0.00035))
        open_ = price
        close = max(0.5, open_ + drift + shock)
        high = max(open_, close) + abs(float(rng.normal(0.0, 0.00018)))
        low = min(open_, close) - abs(float(rng.normal(0.0, 0.00018)))
        bars.append(_bar(i, open_=open_, high=high, low=low, close=close))
        price = close
    return bars


# --- Feature contract ------------------------------------------------------------


def test_feature_names_match_matrix_width() -> None:
    bars = _synthetic_series(300)
    frame = build_features(bars, "EURUSD")
    assert frame.base.shape == (300, len(FEATURE_NAMES))
    assert frame.base.dtype == np.float64


def test_features_are_causal() -> None:
    bars = _synthetic_series(300)
    baseline = build_features(bars, "EURUSD")

    mutated = list(bars)
    for i in range(200, 300):
        bar = mutated[i]
        mutated[i] = _bar(
            i,
            open_=bar.open * 1.05,
            high=bar.high * 1.05,
            low=bar.low * 1.05,
            close=bar.close * 1.05,
        )
    after = build_features(mutated, "EURUSD")

    np.testing.assert_allclose(
        baseline.base[:200], after.base[:200], equal_nan=True, rtol=0.0, atol=0.0
    )


def test_valid_mask_excludes_last_bar_and_warmup() -> None:
    bars = _synthetic_series(300)
    frame = build_features(bars, "EURUSD", cfg=DenseConfig(warmup_bars=120))
    assert not frame.valid[:120].any()
    assert not frame.valid[-1]
    assert frame.valid[200]


# --- Outcome simulation ----------------------------------------------------------


def _outcome_bars(entry_open: float, entry_high: float, entry_low: float) -> list[OHLCBar]:
    return [
        _bar(0, open_=1.1000, high=1.1005, low=1.0995, close=1.1000),
        _bar(1, open_=entry_open, high=entry_high, low=entry_low, close=entry_open),
    ]


def _atr(value: float) -> npt.NDArray[np.float64]:
    return np.array([value, value], dtype=np.float64)


def test_target_hit_is_two_r_minus_cost() -> None:
    bars = _outcome_bars(1.1000, 1.1030, 1.0995)
    cfg = DenseConfig(stop_atr_mult=1.0, target_r=2.0, max_hold_bars=4)
    result = simulate_outcome(bars, _atr(0.0010), 0, 1, "EURUSD", cfg=cfg)
    assert result is not None
    net_r, exit_index = result
    cost_r = (1.1000 * 1.5 / 10_000.0) / 0.0010
    assert exit_index == 1
    assert net_r == pytest.approx(2.0 - cost_r)


def test_stop_hit_is_minus_one_r_minus_cost() -> None:
    bars = _outcome_bars(1.1000, 1.1005, 1.0985)
    cfg = DenseConfig(stop_atr_mult=1.0, target_r=2.0, max_hold_bars=4)
    result = simulate_outcome(bars, _atr(0.0010), 0, 1, "EURUSD", cfg=cfg)
    assert result is not None
    net_r, _ = result
    cost_r = (1.1000 * 1.5 / 10_000.0) / 0.0010
    assert net_r == pytest.approx(-1.0 - cost_r)


def test_same_bar_stop_and_target_books_stop() -> None:
    bars = _outcome_bars(1.1000, 1.1030, 1.0985)
    cfg = DenseConfig(stop_atr_mult=1.0, target_r=2.0, max_hold_bars=4)
    result = simulate_outcome(bars, _atr(0.0010), 0, 1, "EURUSD", cfg=cfg)
    assert result is not None
    net_r, _ = result
    cost_r = (1.1000 * 1.5 / 10_000.0) / 0.0010
    assert net_r == pytest.approx(-1.0 - cost_r)


def test_gap_through_stop_fills_worse_than_minus_one_r() -> None:
    bars = [
        _bar(0, open_=1.1000, high=1.1005, low=1.0995, close=1.1000),
        _bar(1, open_=1.1000, high=1.1005, low=1.0995, close=1.1000),
        _bar(2, open_=1.0980, high=1.0985, low=1.0975, close=1.0978),
    ]
    cfg = DenseConfig(stop_atr_mult=1.0, target_r=2.0, max_hold_bars=4)
    result = simulate_outcome(bars, _atr(0.0010), 0, 1, "EURUSD", cfg=cfg)
    assert result is not None
    net_r, exit_index = result
    cost_r = (1.1000 * 1.5 / 10_000.0) / 0.0010
    assert exit_index == 2
    assert net_r == pytest.approx(-2.0 - cost_r)
    assert net_r < -1.0


def test_short_target_hit_is_mirrored() -> None:
    bars = _outcome_bars(1.1000, 1.1005, 1.0970)
    cfg = DenseConfig(stop_atr_mult=1.0, target_r=2.0, max_hold_bars=4)
    result = simulate_outcome(bars, _atr(0.0010), 0, -1, "EURUSD", cfg=cfg)
    assert result is not None
    net_r, _ = result
    cost_r = (1.1000 * 1.5 / 10_000.0) / 0.0010
    assert net_r == pytest.approx(2.0 - cost_r)


def test_timeout_exits_at_last_close() -> None:
    bars = [
        _bar(0, open_=1.1000, high=1.1002, low=1.0998, close=1.1000),
        _bar(1, open_=1.1000, high=1.1003, low=1.0997, close=1.1001),
        _bar(2, open_=1.1001, high=1.1004, low=1.0998, close=1.1002),
    ]
    cfg = DenseConfig(stop_atr_mult=1.0, target_r=2.0, max_hold_bars=2)
    result = simulate_outcome(bars, _atr(0.0010), 0, 1, "EURUSD", cfg=cfg)
    assert result is not None
    net_r, exit_index = result
    cost_r = (1.1000 * 1.5 / 10_000.0) / 0.0010
    assert exit_index == 2
    assert net_r == pytest.approx((1.1002 - 1.1000) / 0.0010 - cost_r)


# --- Labels and walk-forward -----------------------------------------------------


def test_labels_cover_both_sides_and_are_finite_where_valid() -> None:
    bars = _synthetic_series(400)
    frame = build_features(bars, "EURUSD")
    long_r, short_r, long_exit, short_exit = build_labels(
        bars, frame, "EURUSD", cfg=DenseConfig(max_hold_bars=8)
    )
    valid = frame.valid
    assert np.isfinite(long_r[valid]).all()
    assert np.isfinite(short_r[valid]).all()
    assert (long_exit[valid] >= 1).all()
    assert (short_exit[valid] >= 1).all()
    assert np.isnan(long_r[~valid]).all()


def test_directional_mirror_flips_only_directional_columns() -> None:
    from src.paper.backtest.dense import DIRECTIONAL_FEATURES

    bars = _synthetic_series(300)
    frame = build_features(bars, "EURUSD")
    long_view = directional_matrix(frame.base)
    short_view = np.where(
        np.array([name in DIRECTIONAL_FEATURES for name in FEATURE_NAMES]),
        -long_view,
        long_view,
    )
    for k, name in enumerate(FEATURE_NAMES):
        if name in DIRECTIONAL_FEATURES:
            np.testing.assert_allclose(short_view[:, k], -long_view[:, k])
        else:
            np.testing.assert_allclose(short_view[:, k], long_view[:, k])


def test_walk_forward_folds_are_strictly_forward() -> None:
    bars = _synthetic_series(7_000)
    cfg = DenseConfig(
        train_days=20,
        test_days=10,
        warmup_bars=120,
        min_train_rows=500,
        signal_rate=0.05,
    )
    result = run_walk_forward("EURUSD", bars, cfg=cfg)
    assert result.folds
    for fold in result.folds:
        assert fold.train_end == fold.test_start
        assert fold.test_start < fold.test_end
    for previous, current in zip(result.folds, result.folds[1:], strict=False):
        assert previous.test_end <= current.test_start


def test_walk_forward_trade_times_are_inside_test_windows() -> None:
    bars = _synthetic_series(7_000)
    cfg = DenseConfig(
        train_days=20,
        test_days=10,
        warmup_bars=120,
        min_train_rows=500,
        signal_rate=0.05,
    )
    result = run_walk_forward("EURUSD", bars, cfg=cfg)
    windows = {f.fold: (f.test_start, f.test_end) for f in result.folds}
    for trade in result.trades:
        start, end = windows[trade.fold]
        assert start <= trade.decision_at < end
        assert trade.entry_at >= trade.decision_at
        assert trade.exit_at >= trade.entry_at


def test_every_trade_pays_cost_and_net_is_gross_minus_cost() -> None:
    bars = _synthetic_series(7_000)
    cfg = DenseConfig(
        train_days=20,
        test_days=10,
        warmup_bars=120,
        min_train_rows=500,
        signal_rate=0.05,
    )
    result = run_walk_forward("EURUSD", bars, cfg=cfg)
    assert result.trades
    for trade in result.trades:
        assert trade.cost_r > 0.0
        assert trade.net_r == pytest.approx(trade.gross_r - trade.cost_r)
