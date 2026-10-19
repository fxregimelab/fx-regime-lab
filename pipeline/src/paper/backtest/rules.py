"""Interpretable dense rule baselines (research only, never execution).

The walk-forward model can overfit in ways that are hard to see. These three
rules are the honest cross-check: if a multi-feature ridge model cannot beat a
one-line session rule, the model is not adding value.

Every rule is causal and takes the next bar's open. Costs and the pessimistic
same-bar rule are inherited from :mod:`src.paper.backtest.dense`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from src.paper.backtest.dense import (
    DenseConfig,
    FeatureFrame,
    TradeRecord,
    _bar_delta,
    build_features,
    simulate_outcome,
)
from src.paper.config import COSTS
from src.paper.features import OHLCBar


def _bar_open(timestamp: datetime, delta: timedelta) -> datetime:
    """Nominal open time of a bar whose ``timestamp`` is its close time."""
    return timestamp - delta


@dataclass(frozen=True)
class RuleConfig:
    stop_atr_mult: float = 2.5
    target_r: float = 1.5
    max_hold_bars: int = 48
    min_gap_bars: int = 8


def _asian_ranges(
    bars: list[OHLCBar], delta: timedelta | None = None
) -> dict[date, tuple[float, float]]:
    """High/low of the 00:00-07:00 UTC window for each completed day.

    Membership is decided by the bar's *open* time, so the bar covering
    06:45-07:00 (close time 07:00) is included and the 07:00-07:15 bar is not.
    """
    delta = delta or _bar_delta([b.timestamp for b in bars])
    ranges: dict[date, tuple[float, float]] = {}
    for bar in bars:
        open_at = _bar_open(bar.timestamp, delta)
        if open_at.hour >= 7:
            continue
        day = open_at.date()
        high, low = ranges.get(day, (bar.high, bar.low))
        ranges[day] = (max(high, bar.high), min(low, bar.low))
    return ranges


def london_breakout(
    bars: list[OHLCBar], frame: FeatureFrame, *, min_range_atr: float = 0.5
) -> list[tuple[int, int]]:
    """First close beyond the Asian range during the London window.

    ``bars[i].timestamp`` is the close time, so the bar covering 06:45-07:00
    closes at 07:00 and belongs to Asia. The first London decision is the bar
    that opens at 07:00 (close time 07:15).
    """
    delta = _bar_delta([bar.timestamp for bar in bars])
    ranges = _asian_ranges(bars, delta)
    out: list[tuple[int, int]] = []
    for i in range(1, len(bars)):
        open_at = _bar_open(bars[i].timestamp, delta)
        if open_at.weekday() >= 5 or not (7 <= open_at.hour < 16):
            continue
        levels = ranges.get(open_at.date())
        if levels is None:
            continue
        high, low = levels
        atr = float(frame.atr[i])
        if not (atr > 0.0) or (high - low) < min_range_atr * atr:
            continue
        previous_close = bars[i - 1].close
        close = bars[i].close
        if close > high and previous_close <= high:
            out.append((i, 1))
        elif close < low and previous_close >= low:
            out.append((i, -1))
    return out


def mean_reversion(
    bars: list[OHLCBar], frame: FeatureFrame, *, z: float = 2.0, min_gap_bars: int = 8
) -> list[tuple[int, int]]:
    """Fade a two-sigma band excursion when RSI is stretched."""
    out: list[tuple[int, int]] = []
    last_signal = -10_000
    for i in range(len(bars)):
        if i - last_signal < min_gap_bars:
            continue
        ts = bars[i].timestamp
        if ts.weekday() >= 5 or not (7 <= ts.hour < 20):
            continue
        bb_z = float(frame.base[i, 6])
        rsi = float(frame.base[i, 5]) * 50.0 + 50.0
        if bb_z <= -z and rsi <= 30.0:
            out.append((i, 1))
            last_signal = i
        elif bb_z >= z and rsi >= 70.0:
            out.append((i, -1))
            last_signal = i
    return out


def momentum_pullback(
    bars: list[OHLCBar],
    frame: FeatureFrame,
    *,
    trend_min: float = 0.0,
    min_gap_bars: int = 8,
) -> list[tuple[int, int]]:
    """Trade with the EMA20 slope after a short-term pullback resumes."""
    out: list[tuple[int, int]] = []
    last_signal = -10_000
    for i in range(4, len(bars)):
        if i - last_signal < min_gap_bars:
            continue
        ts = bars[i].timestamp
        if ts.weekday() >= 5 or not (7 <= ts.hour < 20):
            continue
        ema_dist = float(frame.base[i, 3])
        slope = float(frame.base[i, 4])
        ret_4 = float(frame.base[i, 1])
        if slope > trend_min and ema_dist > 0.0 and ret_4 > 0.0:
            out.append((i, 1))
            last_signal = i
        elif slope < -trend_min and ema_dist < 0.0 and ret_4 < 0.0:
            out.append((i, -1))
            last_signal = i
    return out


def evaluate_signals(
    pair: str,
    bars: list[OHLCBar],
    frame: FeatureFrame,
    signals: list[tuple[int, int]],
    *,
    cfg: DenseConfig,
) -> list[TradeRecord]:
    """Settle rule signals with one position per pair at a time."""
    trades: list[TradeRecord] = []
    delta = _bar_delta([bar.timestamp for bar in bars])
    block_until = -1
    for index, side in sorted(signals):
        if index < block_until:
            continue
        outcome = simulate_outcome(bars, frame.atr, index, side, pair, cfg=cfg)
        if outcome is None:
            continue
        net_r, exit_index = outcome
        entry_bar = bars[index + 1]
        exit_bar = bars[exit_index]
        risk = cfg.stop_atr_mult * float(frame.atr[index])
        total_bps = COSTS.round_trip_bps[pair] + COSTS.slippage_bps
        cost_r = (entry_bar.open * total_bps / 10_000.0) / risk
        trades.append(
            TradeRecord(
                pair=pair,
                fold=-1,
                side="long" if side > 0 else "short",
                decision_at=bars[index].timestamp,
                entry_at=entry_bar.timestamp - delta,
                exit_at=exit_bar.timestamp,
                entry_price=entry_bar.open,
                risk_price=risk,
                net_r=net_r,
                gross_r=net_r + cost_r,
                cost_r=cost_r,
                score=0.0,
                bars_held=exit_index - index,
                entry_spread_points=entry_bar.spread_points,
            )
        )
        block_until = exit_index
    return trades


def run_rule(
    pair: str,
    bars: list[OHLCBar],
    rule: str,
    *,
    rule_cfg: RuleConfig | None = None,
) -> list[TradeRecord]:
    rule_cfg = rule_cfg or RuleConfig()
    cfg = DenseConfig(
        stop_atr_mult=rule_cfg.stop_atr_mult,
        target_r=rule_cfg.target_r,
        max_hold_bars=rule_cfg.max_hold_bars,
    )
    frame = build_features(bars, pair, cfg=cfg)
    if rule == "london_breakout":
        signals = london_breakout(bars, frame)
    elif rule == "mean_reversion":
        signals = mean_reversion(bars, frame, min_gap_bars=rule_cfg.min_gap_bars)
    elif rule == "momentum_pullback":
        signals = momentum_pullback(bars, frame, min_gap_bars=rule_cfg.min_gap_bars)
    else:
        raise ValueError(f"unknown rule {rule!r}")
    return evaluate_signals(pair, bars, frame, signals, cfg=cfg)
