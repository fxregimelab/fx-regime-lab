"""Dense walk-forward research harness (research only, never execution).

Owner directive 2026-10-19: the demo desk must produce roughly 10-15 settled
trades per week so that selection can be optimised on a statistically usable
sample. The structural-setup path produced 39 trades in four years, which is too
few to distinguish an edge from noise.

This module does not change the production detectors and never places an order.
It builds a causal feature matrix from completed M15 bars, labels every bar with
the realised net R of a canonical trade entered at the *next* M15 open, and runs
an expanding-window walk-forward so that every reported number is out-of-sample.

Honesty rules, same spirit as ``engine.py``:

- Features at bar ``i`` use bars ``<= i`` only. Nothing is centred or smoothed
  with future data.
- Entry is the next bar's open. A bar that spans both stop and target books the
  STOP. Gaps through a stop fill at the open, not at the stop price.
- Costs come from the canonical table; they are subtracted from every label.
- Training only sees bars strictly before the test window. Hyper-parameters are
  fixed a priori (no per-fold tuning), so the out-of-sample numbers are not
  optimiser output.
- The unconditional expectancy of the same bars is reported next to the
  selected trades. If selection does not beat the unconditional mean, the model
  has no demonstrated edge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypeAlias

import numpy as np
import numpy.typing as npt

from src.paper.config import COSTS
from src.paper.features import OHLCBar

Array: TypeAlias = npt.NDArray[np.float64]
BoolArray: TypeAlias = npt.NDArray[np.bool_]
IntArray: TypeAlias = npt.NDArray[np.int64]

# Feature order is part of the contract: the directional mask indexes it.
FEATURE_NAMES: tuple[str, ...] = (
    "ret_1",
    "ret_4",
    "ret_16",
    "ema_dist",
    "ema_slope",
    "rsi_centered",
    "bb_z",
    "range_pos",
    "body",
    "upper_wick",
    "lower_wick",
    "dist_pdh",
    "dist_pdl",
    "dist_round",
    "streak",
    "atr_ratio",
    "atr_pct",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "session_asia",
    "session_london",
    "session_ny",
    "vol_z",
    "vol_dir",
    "vwap_dist",
    "clv",
    "range_exp",
    "gap",
)

# Features that flip sign for a short trade. A positive value always means
# "supports the proposed direction"; this keeps one model symmetric.
DIRECTIONAL_FEATURES: frozenset[str] = frozenset(
    {
        "ret_1",
        "ret_4",
        "ret_16",
        "ema_dist",
        "ema_slope",
        "rsi_centered",
        "bb_z",
        "range_pos",
        "body",
        "upper_wick",
        "lower_wick",
        "dist_pdh",
        "dist_pdl",
        "dist_round",
        "streak",
        "vol_dir",
        "vwap_dist",
        "clv",
        "gap",
    }
)

_DIRECTIONAL_MASK = np.array([name in DIRECTIONAL_FEATURES for name in FEATURE_NAMES])


@dataclass(frozen=True)
class DenseConfig:
    """Measurement choices. None of these is a production rule."""

    stop_atr_mult: float = 1.5
    target_r: float = 2.0
    max_hold_bars: int = 32
    warmup_bars: int = 120

    train_days: int = 365
    test_days: int = 90
    calibration_fraction: float = 0.25

    ridge_shrinkage: float = 0.05
    signal_rate: float = 0.02       # calibration quantile, not a realised rate
    min_edge_r: float = 0.02        # predicted net R must clear this
    min_train_rows: int = 5_000     # directional rows (both sides stacked)
    max_concurrent: int = 1         # open positions per pair at a time


@dataclass(frozen=True)
class FeatureFrame:
    times: tuple[datetime, ...]
    base: Array          # (n, F), NaN outside the valid region
    atr: Array           # (n,), M15 ATR14
    valid: npt.NDArray[np.bool_]


@dataclass(frozen=True)
class TradeRecord:
    pair: str
    fold: int
    side: str
    decision_index: int
    decision_at: datetime
    entry_at: datetime
    exit_at: datetime
    entry_price: float
    risk_price: float
    net_r: float
    gross_r: float
    cost_r: float
    score: float
    bars_held: int
    entry_spread_points: float
    matched_r: float

    @property
    def win(self) -> bool:
        return self.net_r > 0.0


@dataclass
class FoldResult:
    fold: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    threshold: float
    train_rows: int
    test_rows: int
    trades: int
    net_r: float
    mean_selected_score: float
    mean_actual_r: float
    unconditional_r: float
    coefficients: dict[str, float] = field(default_factory=dict)


@dataclass
class DenseResult:
    pair: str
    start: datetime
    end: datetime
    trades: list[TradeRecord]
    folds: list[FoldResult]
    config: DenseConfig
    unconditional_r: float
    matched_unconditional_r: float
    valid_bars: int

    @property
    def net_r(self) -> float:
        return sum(t.net_r for t in self.trades)

    @property
    def wins(self) -> list[TradeRecord]:
        return [t for t in self.trades if t.net_r > 0.0]

    @property
    def win_rate(self) -> float:
        return len(self.wins) / len(self.trades) if self.trades else 0.0

    @property
    def expectancy_r(self) -> float:
        return self.net_r / len(self.trades) if self.trades else 0.0

    @property
    def weeks(self) -> float:
        """Out-of-sample span only: training bars are not tradable evidence."""
        first_test = self.folds[0].test_start if self.folds else self.start
        return max((self.end - first_test).total_seconds() / (7 * 86400.0), 1e-9)

    @property
    def trades_per_week(self) -> float:
        return len(self.trades) / self.weeks


# --- Rolling helpers (all trailing; never centred) -------------------------------


def _rolling_mean(values: Array, window: int) -> Array:
    out = np.full(values.shape[0], np.nan, dtype=np.float64)
    if values.shape[0] < window:
        return out
    cumulative = np.concatenate(([0.0], np.cumsum(values)))
    out[window - 1 :] = (cumulative[window:] - cumulative[:-window]) / window
    return out


def _rolling_std(values: Array, window: int) -> Array:
    out = np.full(values.shape[0], np.nan, dtype=np.float64)
    if values.shape[0] < window:
        return out
    cumulative = np.concatenate(([0.0], np.cumsum(values)))
    cumulative_sq = np.concatenate(([0.0], np.cumsum(values * values)))
    mean = (cumulative[window:] - cumulative[:-window]) / window
    var = (cumulative_sq[window:] - cumulative_sq[:-window]) / window - mean * mean
    out[window - 1 :] = np.sqrt(np.maximum(var, 0.0))
    return out


def _rolling_extreme(values: Array, window: int, *, maximum: bool) -> Array:
    out = np.full(values.shape[0], np.nan, dtype=np.float64)
    if values.shape[0] < window:
        return out
    windows = np.lib.stride_tricks.sliding_window_view(values, window)
    out[window - 1 :] = windows.max(axis=1) if maximum else windows.min(axis=1)
    return out


def _ema(values: Array, period: int) -> Array:
    out = np.full(values.shape[0], np.nan, dtype=np.float64)
    if values.shape[0] < period:
        return out
    out[period - 1] = float(np.mean(values[:period]))
    alpha = 2.0 / (period + 1.0)
    for i in range(period, values.shape[0]):
        out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]
    return out


def _rsi(closes: Array, period: int = 14) -> Array:
    out = np.full(closes.shape[0], np.nan, dtype=np.float64)
    if closes.shape[0] <= period:
        return out
    deltas = np.diff(closes)
    gains = np.where(deltas > 0.0, deltas, 0.0)
    losses = np.where(deltas < 0.0, -deltas, 0.0)
    avg_gain = _rolling_mean(gains, period)
    avg_loss = _rolling_mean(losses, period)
    # align: deltas[i] belongs to closes[i+1]
    gain_aligned = np.concatenate(([np.nan], avg_gain))
    loss_aligned = np.concatenate(([np.nan], avg_loss))
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = gain_aligned / loss_aligned
    rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = np.where((loss_aligned == 0.0) & (gain_aligned > 0.0), 100.0, rsi)
    rsi = np.where((loss_aligned == 0.0) & (gain_aligned == 0.0), 50.0, rsi)
    out[:] = rsi
    return out


def _closes_streak(closes: Array) -> Array:
    out = np.zeros(closes.shape[0], dtype=np.float64)
    streak = 0.0
    for i in range(1, closes.shape[0]):
        if closes[i] > closes[i - 1]:
            streak = max(streak, 0.0) + 1.0
        elif closes[i] < closes[i - 1]:
            streak = min(streak, 0.0) - 1.0
        else:
            streak = 0.0
        out[i] = streak
    return out


def _prior_day_levels(timestamps: list[datetime], high: Array, low: Array) -> tuple[Array, Array]:
    """Prior UTC day's high/low, available from the first bar of the next day."""
    n = high.shape[0]
    pdh = np.full(n, np.nan, dtype=np.float64)
    pdl = np.full(n, np.nan, dtype=np.float64)
    current_day = timestamps[0].date()
    day_high = high[0]
    day_low = low[0]
    previous_high = np.nan
    previous_low = np.nan
    for i in range(n):
        day = timestamps[i].date()
        if day != current_day:
            previous_high = day_high
            previous_low = day_low
            current_day = day
            day_high = high[i]
            day_low = low[i]
        else:
            day_high = max(day_high, high[i])
            day_low = min(day_low, low[i])
        pdh[i] = previous_high
        pdl[i] = previous_low
    return pdh, pdl


# --- Feature construction --------------------------------------------------------


def build_features(
    bars: list[OHLCBar], pair: str, *, cfg: DenseConfig | None = None
) -> FeatureFrame:
    """Causal feature matrix from completed M15 bars."""
    cfg = cfg or DenseConfig()
    n = len(bars)
    if n < cfg.warmup_bars + 2:
        raise ValueError(f"dense features need at least {cfg.warmup_bars + 2} bars")

    open_ = np.array([b.open for b in bars], dtype=np.float64)
    high = np.array([b.high for b in bars], dtype=np.float64)
    low = np.array([b.low for b in bars], dtype=np.float64)
    close = np.array([b.close for b in bars], dtype=np.float64)
    timestamps = [b.timestamp for b in bars]

    true_range: Array = np.empty(n, dtype=np.float64)
    true_range[0] = high[0] - low[0]
    true_range[1:] = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    atr = _rolling_mean(true_range, 14)
    atr_long = _rolling_mean(true_range, 100)
    safe_atr = np.where(atr > 0.0, atr, np.nan)

    ema20 = _ema(close, 20)
    sma20 = _rolling_mean(close, 20)
    std20 = _rolling_std(close, 20)
    rsi14 = _rsi(close, 14)
    high20 = _rolling_extreme(high, 20, maximum=True)
    low20 = _rolling_extreme(low, 20, maximum=False)
    pdh, pdl = _prior_day_levels(timestamps, high, low)
    streak = _closes_streak(close)

    volume = np.array([b.volume for b in bars], dtype=np.float64)
    log_volume = np.log1p(volume)
    volume_mean = _rolling_mean(log_volume, 20)
    volume_std = _rolling_std(log_volume, 20)
    vol_z = (log_volume - volume_mean) / np.where(volume_std > 0.0, volume_std, np.nan)
    vol_dir = vol_z * np.sign(close - open_)

    vwap: Array = np.full(n, np.nan, dtype=np.float64)
    cumulative_pv = 0.0
    cumulative_volume = 0.0
    current_day = timestamps[0].date()
    for i in range(n):
        day = timestamps[i].date()
        if day != current_day:
            current_day = day
            cumulative_pv = 0.0
            cumulative_volume = 0.0
        bar_volume = max(volume[i], 1.0)
        typical = (high[i] + low[i] + close[i]) / 3.0
        cumulative_pv += typical * bar_volume
        cumulative_volume += bar_volume
        vwap[i] = cumulative_pv / cumulative_volume

    bar_range = high - low
    clv = (close - low) / np.where(bar_range > 0.0, bar_range, np.nan) - 0.5
    range_exp = bar_range / safe_atr
    gap: Array = np.full(n, np.nan, dtype=np.float64)
    gap[1:] = (open_[1:] - close[:-1]) / safe_atr[1:]

    round_step = 0.0050 if pair == "EURUSD" else 0.50
    nearest_round = np.round(close / round_step) * round_step

    minutes = np.array([ts.hour * 60 + ts.minute for ts in timestamps], dtype=np.float64)
    hour = minutes / 60.0
    weekday = np.array([ts.weekday() for ts in timestamps], dtype=np.float64)

    def lagged_return(lag: int) -> Array:
        out: Array = np.full(n, np.nan, dtype=np.float64)
        if n > lag:
            out[lag:] = np.log(close[lag:] / close[:-lag])
        return out

    columns: list[Array] = [
        lagged_return(1),
        lagged_return(4),
        lagged_return(16),
        (close - ema20) / safe_atr,
        (ema20 - np.concatenate((np.full(5, np.nan), ema20[:-5]))) / safe_atr,
        (rsi14 - 50.0) / 50.0,
        (close - sma20) / np.where(std20 > 0.0, std20, np.nan),
        (close - low20) / np.where((high20 - low20) > 0.0, high20 - low20, np.nan) - 0.5,
        (close - open_) / safe_atr,
        (np.maximum(open_, close) - high) / safe_atr,
        (np.minimum(open_, close) - low) / safe_atr,
        (close - pdh) / safe_atr,
        (close - pdl) / safe_atr,
        (close - nearest_round) / safe_atr,
        np.clip(streak, -5.0, 5.0) / 5.0,
        atr / np.where(atr_long > 0.0, atr_long, np.nan) - 1.0,
        atr / close * 10_000.0,
        np.sin(2.0 * np.pi * hour / 24.0),
        np.cos(2.0 * np.pi * hour / 24.0),
        np.sin(2.0 * np.pi * weekday / 5.0),
        np.cos(2.0 * np.pi * weekday / 5.0),
        ((hour >= 0.0) & (hour < 7.0)).astype(np.float64),
        ((hour >= 7.0) & (hour < 12.0)).astype(np.float64),
        ((hour >= 12.0) & (hour < 21.0)).astype(np.float64),
        vol_z,
        vol_dir,
        (close - vwap) / safe_atr,
        clv,
        range_exp,
        gap,
    ]
    base = np.column_stack(columns)
    if base.shape[1] != len(FEATURE_NAMES):
        raise AssertionError("feature column count drifted from FEATURE_NAMES")

    valid: BoolArray = np.ones(n, dtype=np.bool_)
    valid[: cfg.warmup_bars] = False
    # Exclude the final bar (no next open) and the final hold window, whose
    # labels would be truncated at the series end rather than resolved.
    valid[-1] = False
    valid[-min(cfg.max_hold_bars, n) :] = False
    valid[:-1] &= np.all(np.isfinite(base[:-1]), axis=1)   # need a next bar to enter
    valid &= np.isfinite(atr)

    return FeatureFrame(
        times=tuple(timestamps),
        base=base,
        atr=atr,
        valid=valid,
    )


def directional_matrix(base: Array) -> Array:
    """Long-side view.

    Directional columns already point "long-positive" by construction; context
    columns (session, volatility, clock) are not signed and must keep their
    values. The short side mirrors only the directional columns.
    """
    return base


def feature_views(base: Array) -> tuple[Array, Array]:
    """Return the long and short model views of the same feature matrix."""
    long_view = directional_matrix(base)
    short_view = np.where(_DIRECTIONAL_MASK, -long_view, long_view)
    return long_view, short_view


# --- Outcome simulation ----------------------------------------------------------


def simulate_outcome(
    bars: list[OHLCBar],
    atr: Array,
    index: int,
    side: int,
    pair: str,
    *,
    cfg: DenseConfig | None = None,
) -> tuple[float, int] | None:
    """Net R and exit index for a trade decided at bar ``index``.

    Entry is the next bar's open. Stop gaps fill at the open (pessimistic);
    target gaps are capped at the target. A bar that spans both stop and target
    books the stop.
    """
    cfg = cfg or DenseConfig()
    if side not in (-1, 1):
        raise ValueError("side must be +1 or -1")
    entry_index = index + 1
    if entry_index >= len(bars):
        return None
    risk = cfg.stop_atr_mult * float(atr[index])
    if not np.isfinite(risk) or risk <= 0.0:
        return None

    entry = bars[entry_index].open
    stop = entry - side * risk
    target = entry + side * cfg.target_r * risk
    cost_bps = COSTS.round_trip_bps.get(pair)
    if cost_bps is None:
        raise ValueError(f"no canonical cost for {pair}")
    total_bps = cost_bps + COSTS.slippage_bps
    cost_r = (entry * total_bps / 10_000.0) / risk

    last_index = min(len(bars) - 1, entry_index + cfg.max_hold_bars - 1)
    for j in range(entry_index, last_index + 1):
        bar = bars[j]
        if side > 0:
            if bar.open <= stop:
                return ((bar.open - entry) / risk) - cost_r, j
            if bar.open >= target:
                return cfg.target_r - cost_r, j
        else:
            if bar.open >= stop:
                return ((entry - bar.open) / risk) - cost_r, j
            if bar.open <= target:
                return cfg.target_r - cost_r, j

        stop_hit = bar.low <= stop if side > 0 else bar.high >= stop
        if stop_hit:
            return -1.0 - cost_r, j

        target_hit = bar.high >= target if side > 0 else bar.low <= target
        if target_hit:
            return cfg.target_r - cost_r, j

    exit_price = bars[last_index].close
    gross = side * (exit_price - entry) / risk
    return gross - cost_r, last_index


def build_labels(
    bars: list[OHLCBar],
    frame: FeatureFrame,
    pair: str,
    *,
    cfg: DenseConfig | None = None,
) -> tuple[Array, Array, npt.NDArray[np.int64], npt.NDArray[np.int64]]:
    """Net R and exit index for both sides at every valid decision bar."""
    cfg = cfg or DenseConfig()
    n = len(bars)
    long_r: Array = np.full(n, np.nan, dtype=np.float64)
    short_r: Array = np.full(n, np.nan, dtype=np.float64)
    long_exit: IntArray = np.full(n, -1, dtype=np.int64)
    short_exit: IntArray = np.full(n, -1, dtype=np.int64)
    for i in range(n):
        if not frame.valid[i]:
            continue
        long_out = simulate_outcome(bars, frame.atr, i, 1, pair, cfg=cfg)
        short_out = simulate_outcome(bars, frame.atr, i, -1, pair, cfg=cfg)
        if long_out is not None:
            long_r[i], long_exit[i] = long_out
        if short_out is not None:
            short_r[i], short_exit[i] = short_out
    return long_r, short_r, long_exit, short_exit


# --- Walk-forward model ----------------------------------------------------------


def _ridge_fit(features: Array, target: Array, shrinkage: float) -> Array:
    """Closed-form ridge with an unpenalised intercept."""
    design = np.column_stack([np.ones(features.shape[0]), features])
    gram = design.T @ design
    penalty = np.eye(gram.shape[0]) * (shrinkage * features.shape[0])
    penalty[0, 0] = 0.0
    return np.linalg.solve(gram + penalty, design.T @ target)


def _ridge_predict(weights: Array, features: Array) -> Array:
    return np.column_stack([np.ones(features.shape[0]), features]) @ weights


def _standardiser(features: Array) -> tuple[Array, Array]:
    mean = np.mean(features, axis=0)
    std = np.std(features, axis=0)
    std = np.where(std > 0.0, std, 1.0)
    return mean, std


def _fold_bounds(
    times: list[datetime], cfg: DenseConfig
) -> list[tuple[datetime, datetime, datetime, datetime]]:
    start = times[0]
    end = times[-1]
    folds: list[tuple[datetime, datetime, datetime, datetime]] = []
    test_start = start + timedelta(days=cfg.train_days)
    while test_start < end:
        test_end = min(test_start + timedelta(days=cfg.test_days), end)
        folds.append((start, test_start, test_start, test_end))
        test_start = test_end
    return folds


def _bar_delta(times: list[datetime]) -> timedelta:
    """Nominal bar size, inferred from the first few completed bars."""
    if len(times) < 2:
        return timedelta(minutes=15)
    diffs = [
        (times[i] - times[i - 1]).total_seconds()
        for i in range(1, min(len(times), 50))
    ]
    positive = [value for value in diffs if value > 0.0]
    if not positive:
        return timedelta(minutes=15)
    return timedelta(seconds=int(np.median(positive)))


def _labels_resolved_before(
    times: list[datetime],
    long_exit: IntArray,
    short_exit: IntArray,
    cutoff: datetime,
) -> BoolArray:
    """Purge training rows whose outcome is only known inside the test window.

    A label simulated from bar ``i`` can resolve up to ``max_hold_bars`` later.
    Training on such a row would let the model see test-period prices.
    """
    ready: BoolArray = np.zeros(len(times), dtype=np.bool_)
    for i in range(len(times)):
        long_index = int(long_exit[i])
        short_index = int(short_exit[i])
        if long_index < 0 or short_index < 0:
            continue
        ready[i] = times[long_index] < cutoff and times[short_index] < cutoff
    return ready


def run_walk_forward(
    pair: str,
    bars: list[OHLCBar],
    *,
    cfg: DenseConfig | None = None,
) -> DenseResult:
    """Expanding-window walk-forward with a single fixed ridge model."""
    cfg = cfg or DenseConfig()
    frame = build_features(bars, pair, cfg=cfg)
    long_r, short_r, long_exit, short_exit = build_labels(bars, frame, pair, cfg=cfg)
    times = list(frame.times)
    bar_delta = _bar_delta(times)

    long_features, short_features = feature_views(frame.base)

    folds = _fold_bounds(times, cfg)
    trades: list[TradeRecord] = []
    fold_results: list[FoldResult] = []
    all_valid = frame.valid & np.isfinite(long_r) & np.isfinite(short_r)
    test_union: BoolArray = np.zeros(len(times), dtype=np.bool_)
    # Pair-global concurrency: a trade opened in one fold can still be open in
    # the next fold's test window.
    open_exits: list[int] = []

    for fold_index, (train_start, train_end, test_start, test_end) in enumerate(folds):
        # Purge: every training label must resolve strictly before the test window.
        resolved = _labels_resolved_before(times, long_exit, short_exit, train_end)
        train_mask = np.array(
            [train_start <= ts < train_end for ts in times], dtype=np.bool_
        ) & all_valid & resolved
        test_mask = np.array(
            [test_start <= ts < test_end for ts in times], dtype=np.bool_
        ) & all_valid
        train_rows = 2 * int(np.sum(train_mask))
        if train_rows < cfg.min_train_rows or not np.any(test_mask):
            continue
        test_union |= test_mask

        train_features = np.vstack(
            [long_features[train_mask], short_features[train_mask]]
        )
        train_target = np.concatenate([long_r[train_mask], short_r[train_mask]])
        mean, std = _standardiser(train_features)
        weights = _ridge_fit(
            (train_features - mean) / std, train_target, cfg.ridge_shrinkage
        )

        # Calibrate the selection threshold on the tail of the training window.
        calibration_cut = train_end - timedelta(
            days=max(1, int(cfg.test_days * cfg.calibration_fraction))
        )
        calibration_mask = np.array(
            [calibration_cut <= ts < train_end for ts in times], dtype=np.bool_
        ) & all_valid
        if int(np.sum(calibration_mask)) < 200:
            calibration_mask = train_mask
        calibration_long = _ridge_predict(
            weights, (long_features[calibration_mask] - mean) / std
        )
        calibration_short = _ridge_predict(
            weights, (short_features[calibration_mask] - mean) / std
        )
        calibration_best = np.maximum(calibration_long, calibration_short)
        threshold = float(np.quantile(calibration_best, 1.0 - cfg.signal_rate))
        threshold = max(threshold, cfg.min_edge_r)

        test_indices = np.flatnonzero(test_mask)
        scores_long: Array = np.full(len(bars), -np.inf, dtype=np.float64)
        scores_short: Array = np.full(len(bars), -np.inf, dtype=np.float64)
        scores_long[test_indices] = _ridge_predict(
            weights, (long_features[test_indices] - mean) / std
        )
        scores_short[test_indices] = _ridge_predict(
            weights, (short_features[test_indices] - mean) / std
        )

        fold_trades: list[TradeRecord] = []
        for i in test_indices:
            open_exits = [exit_index for exit_index in open_exits if exit_index > i]
            if len(open_exits) >= cfg.max_concurrent:
                continue
            if scores_long[i] >= scores_short[i]:
                side, score = 1, float(scores_long[i])
            else:
                side, score = -1, float(scores_short[i])
            if score < threshold or score < cfg.min_edge_r:
                continue
            net_r = float(long_r[i] if side > 0 else short_r[i])
            exit_index = int(long_exit[i] if side > 0 else short_exit[i])
            entry_bar = bars[i + 1]
            exit_bar = bars[exit_index]
            risk = cfg.stop_atr_mult * float(frame.atr[i])
            total_bps = COSTS.round_trip_bps[pair] + COSTS.slippage_bps
            cost_r = (entry_bar.open * total_bps / 10_000.0) / risk
            fold_trades.append(
                TradeRecord(
                    pair=pair,
                    fold=fold_index,
                    side="long" if side > 0 else "short",
                    decision_index=int(i),
                    decision_at=times[i],
                    entry_at=entry_bar.timestamp - bar_delta,
                    exit_at=exit_bar.timestamp,
                    entry_price=entry_bar.open,
                    risk_price=risk,
                    net_r=net_r,
                    gross_r=net_r + cost_r,
                    cost_r=cost_r,
                    score=score,
                    bars_held=int(exit_index) - int(i),
                    entry_spread_points=entry_bar.spread_points,
                    matched_r=(
                        float(long_r[i]) + float(short_r[i])
                    ) / 2.0,
                )
            )
            open_exits.append(exit_index)

        trades.extend(fold_trades)
        unconditional = float(np.mean(np.concatenate(
            [long_r[test_mask], short_r[test_mask]]
        )))
        coefficients = {
            name: float(weights[k + 1]) for k, name in enumerate(FEATURE_NAMES)
        }
        fold_results.append(
            FoldResult(
                fold=fold_index,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                threshold=threshold,
                train_rows=train_rows,
                test_rows=2 * int(np.sum(test_mask)),
                trades=len(fold_trades),
                net_r=sum(t.net_r for t in fold_trades),
                mean_selected_score=(
                    float(np.mean([t.score for t in fold_trades])) if fold_trades else 0.0
                ),
                mean_actual_r=(
                    float(np.mean([t.net_r for t in fold_trades])) if fold_trades else 0.0
                ),
                unconditional_r=unconditional,
                coefficients=coefficients,
            )
        )

    if np.any(test_union):
        all_valid_r = np.concatenate([long_r[test_union], short_r[test_union]])
        unconditional = float(np.mean(all_valid_r)) if all_valid_r.size else float("nan")
    else:
        # No accepted fold means no out-of-sample evidence. Never fall back to
        # training bars: that would silently mix in-sample and out-of-sample.
        unconditional = float("nan")

    matched_values = [
        (float(long_r[trade.decision_index]) + float(short_r[trade.decision_index]))
        / 2.0
        for trade in trades
    ]
    matched_unconditional = (
        float(np.mean(matched_values)) if matched_values else float("nan")
    )
    return DenseResult(
        pair=pair,
        start=times[0],
        end=times[-1],
        trades=trades,
        folds=fold_results,
        config=cfg,
        unconditional_r=unconditional,
        matched_unconditional_r=matched_unconditional,
        valid_bars=int(np.sum(all_valid)),
    )
