"""Oracle tests for the dense walk-forward research harness (AD-T12 research)."""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import numpy as np
import numpy.typing as npt
import pytest

from src.paper.backtest.dense import (
    FEATURE_NAMES,
    DenseConfig,
    _labels_resolved_before,
    build_features,
    build_labels,
    directional_matrix,
    feature_views,
    run_walk_forward,
    simulate_outcome,
)
from src.paper.config import COSTS
from src.paper.features import OHLCBar

START = datetime(2022, 1, 3, tzinfo=UTC)


def _bar(
    index: int,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 1.0,
) -> OHLCBar:
    return OHLCBar(
        timestamp=START + timedelta(minutes=15 * index),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
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
        volume = 1.0 + 0.5 * (1.0 + math.sin(i / 7.0))
        bars.append(
            _bar(i, open_=open_, high=high, low=low, close=close, volume=volume)
        )
        price = close
    return bars


def _synthetic_series_h1(count: int, *, seed: int = 7) -> list[OHLCBar]:
    bars = _synthetic_series(count, seed=seed)
    return [
        OHLCBar(
            timestamp=START + timedelta(hours=i),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        for i, bar in enumerate(bars)
    ]


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
    # Constant volume once left only ~26% of bars valid via NaN volume z-scores;
    # require at least 60% so that regression cannot silently shrink the sample.
    assert valid.sum() > 0.6 * len(bars)


def test_directional_mirror_flips_only_directional_columns() -> None:
    from src.paper.backtest.dense import DIRECTIONAL_FEATURES

    bars = _synthetic_series(300)
    frame = build_features(bars, "EURUSD")
    long_view, short_view = feature_views(frame.base)
    for k, name in enumerate(FEATURE_NAMES):
        if name in DIRECTIONAL_FEATURES:
            np.testing.assert_allclose(short_view[:, k], -long_view[:, k])
        else:
            np.testing.assert_allclose(short_view[:, k], long_view[:, k])


def test_context_features_are_not_zeroed() -> None:
    """Regression: the long view once multiplied context columns by zero."""
    from src.paper.backtest.dense import DIRECTIONAL_FEATURES

    bars = _synthetic_series(400)
    frame = build_features(bars, "EURUSD")
    long_view = directional_matrix(frame.base)
    context = [k for k, name in enumerate(FEATURE_NAMES) if name not in DIRECTIONAL_FEATURES]
    assert context
    for k in context:
        np.testing.assert_allclose(long_view[:, k], frame.base[:, k])
    # Every context column must carry real variance, not just one of them.
    context_slice = frame.base[200:, context]
    assert np.isfinite(context_slice).any(axis=0).all()
    stds = np.nanstd(context_slice, axis=0)
    flat = [FEATURE_NAMES[k] for k, value in zip(context, stds) if not value > 0.0]
    assert not flat, f"constant context columns: {flat}"


def test_labels_resolved_before_purges_rows_that_reach_the_test_window() -> None:
    times = [START + timedelta(minutes=15 * i) for i in range(6)]
    cutoff = times[4]
    long_exit = np.array([3, 4, 5, 2, -1, 1], dtype=np.int64)
    short_exit = np.array([3, 4, 5, 2, -1, 1], dtype=np.int64)
    ready = _labels_resolved_before(times, long_exit, short_exit, cutoff)
    assert ready.tolist() == [True, False, False, True, False, True]


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
    total_bps = COSTS.round_trip_bps["EURUSD"] + COSTS.slippage_bps
    for trade in result.trades:
        # Independent recomputation from entry price and risk distance.
        expected = (trade.entry_price * total_bps / 10_000.0) / trade.risk_price
        assert trade.cost_r == pytest.approx(expected)
        assert trade.gross_r == pytest.approx(trade.net_r + trade.cost_r)
        assert trade.bars_held >= 1


def test_entry_timestamp_is_the_next_bar_open() -> None:
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
        # On a contiguous series the next bar's open equals the decision close.
        assert trade.entry_at == trade.decision_at


def test_h1_entry_timestamp_is_the_next_bar_open() -> None:
    bars = _synthetic_series_h1(6_000)
    cfg = DenseConfig(
        train_days=40,
        test_days=20,
        warmup_bars=120,
        min_train_rows=500,
        signal_rate=0.10,
    )
    result = run_walk_forward("EURUSD", bars, cfg=cfg)
    assert result.trades
    for trade in result.trades:
        assert trade.entry_at == trade.decision_at
        expected_held = int(
            (trade.exit_at - trade.decision_at).total_seconds() / 3600.0
        )
        assert trade.bars_held == expected_held


def test_purge_is_applied_inside_walk_forward() -> None:
    """Integration: training rows whose label resolves in the test window are removed."""
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
    frame = build_features(bars, "EURUSD", cfg=cfg)
    long_r, short_r, long_exit, short_exit = build_labels(bars, frame, "EURUSD", cfg=cfg)
    times = list(frame.times)
    all_valid = frame.valid & np.isfinite(long_r) & np.isfinite(short_r)
    purged_any = False
    for fold in result.folds:
        resolved = _labels_resolved_before(times, long_exit, short_exit, fold.train_end)
        train_only = np.array(
            [fold.train_start <= ts < fold.train_end for ts in times], dtype=np.bool_
        ) & all_valid
        expected = 2 * int(np.sum(train_only & resolved))
        assert fold.train_rows == expected
        unpurged = 2 * int(np.sum(train_only))
        assert fold.train_rows <= unpurged
        purged_any = purged_any or fold.train_rows < unpurged
    assert purged_any, "no fold lost a row to the purge; the guard is not active"


def test_weeks_denominator_starts_at_the_first_test_window() -> None:
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
    expected = (
        result.end - result.folds[0].test_start
    ).total_seconds() / (7 * 86400.0)
    assert result.weeks == pytest.approx(expected)


def test_no_accepted_fold_returns_nan_unconditional_not_training_bars() -> None:
    bars = _synthetic_series(500)
    cfg = DenseConfig(train_days=400, test_days=30, warmup_bars=120)
    result = run_walk_forward("EURUSD", bars, cfg=cfg)
    assert result.folds == []
    assert math.isnan(result.unconditional_r)


def test_concurrency_can_admit_more_trades() -> None:
    bars = _synthetic_series(7_000)
    base = DenseConfig(
        train_days=20,
        test_days=10,
        warmup_bars=120,
        min_train_rows=500,
        signal_rate=0.30,
        min_edge_r=0.0,
    )
    one = run_walk_forward("EURUSD", bars, cfg=replace(base, max_concurrent=1))
    two = run_walk_forward("EURUSD", bars, cfg=replace(base, max_concurrent=2))
    three = run_walk_forward("EURUSD", bars, cfg=replace(base, max_concurrent=3))
    assert len(two.trades) > len(one.trades)
    assert len(three.trades) > len(two.trades)


def test_matched_benchmark_uses_the_selected_decision_bars() -> None:
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
    frame = build_features(bars, "EURUSD", cfg=cfg)
    long_r, short_r, _, _ = build_labels(bars, frame, "EURUSD", cfg=cfg)
    expected = float(
        np.mean(
            [
                (float(long_r[t.decision_index]) + float(short_r[t.decision_index])) / 2.0
                for t in result.trades
            ]
        )
    )
    assert result.matched_unconditional_r == pytest.approx(expected)


def test_upper_wick_is_negative_when_the_high_is_rejected() -> None:
    bars = _synthetic_series(200)
    index = 150
    original = bars[index]
    bars[index] = OHLCBar(
        timestamp=original.timestamp,
        open=original.open,
        high=original.open + 0.0100,
        low=original.low,
        close=original.open,
        volume=1.0,
    )
    frame = build_features(bars, "EURUSD")
    column = FEATURE_NAMES.index("upper_wick")
    assert frame.base[index, column] < 0.0
