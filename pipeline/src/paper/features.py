"""AD-T09 offline feature core: deterministic calculations from completed bars.

Every function is pure and works on completed OHLC bars whose ``timestamp``
is the bar CLOSE time (a bar is only usable at decisions ``t >= timestamp``).
Definitions are the spec-02 section 2 frozen ones:

- ``atr14``: mean of the last 14 true ranges (needs 15 bars; no Wilder
  smoothing under this name).
- ``ema20_series``: EMA over the fixed last-256-bar window whose v2 seed is
  the SMA of the first 20 closes of THAT window; recursion
  ``EMA_i = (2/21) C_i + (19/21) EMA_{i-1}``. The legacy checklist EMA seeds
  at the first value and must never be mixed with this series.
- ``confirmed_swings``: k=2 unique fractal highs/lows in the ±2-bar window;
  ties are not swings; ``confirmed_at`` is the close of pivot+2 and a swing is
  unusable before that time (never emitted earlier).
- ``structure_state``: last two confirmed highs and lows both rising (long) or
  falling (short); flat/mixed -> neutral, insufficient -> insufficient.
- ``build_pools``: clusters of >=2 same-kind confirmed swings within 0.1*ATR
  whose consecutive constituents are >=3 bars apart; the pool keeps its range
  and constituents, not an invented point level.

Session/gap rules that depend on the broker session calendar stay with the
runtime broker adapter (AD-T07); the offline gap check here is deliberately
research-lenient (weekend-aware) and is not the production bar-gap gate.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.paper.contracts import ContractError

TF_D1_MIN, TF_D1_MAX = 60, 260
TF_H4_MIN, TF_H4_MAX = 40, 120
TF_H1_MIN, TF_H1_MAX = 60, 256
TF_M15_MIN, TF_M15_MAX = 32, 128

_WEEKEND_SPAN = timedelta(days=3, hours=12)


@dataclass(frozen=True)
class OHLCBar:
    """One completed bar; ``timestamp`` is the bar close time in aware UTC."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def __post_init__(self) -> None:
        if (
            type(self.timestamp) is not datetime
            or self.timestamp.tzinfo is None
            or self.timestamp.utcoffset() is None
        ):
            raise ContractError("INVALID_SCHEMA", "OHLCBar.timestamp: aware datetime required")
        if self.timestamp.utcoffset() != timedelta(0):
            raise ContractError("INVALID_SCHEMA", "OHLCBar.timestamp: UTC required")
        values = (self.open, self.high, self.low, self.close)
        if any(type(v) is not float or not math.isfinite(v) or v <= 0.0 for v in values):
            raise ContractError("INVALID_NUMBER", "OHLCBar: positive finite prices required")
        body_low = min(self.open, self.close)
        body_high = max(self.open, self.close)
        if self.low > body_low or self.high < body_high or self.low > self.high:
            raise ContractError("INVALID_SCHEMA", "OHLCBar: low/open/close/high ordering broken")
        if type(self.volume) is not float or self.volume < 0.0 or not math.isfinite(self.volume):
            raise ContractError("INVALID_NUMBER", "OHLCBar.volume: nonnegative finite required")


def validate_bars(bars: Sequence[OHLCBar]) -> None:
    """Ascending unique close times and structurally valid bars only."""
    previous: datetime | None = None
    for bar in bars:
        if previous is not None and bar.timestamp <= previous:
            raise ContractError("BAR_INCOMPLETE", "bars must have strictly ascending close times")
        previous = bar.timestamp


def require_window(bars: Sequence[OHLCBar], *, min_bars: int, max_bars: int, label: str) -> None:
    """Spec-02 bounded decision windows; below minimum means no candidate."""
    if len(bars) < min_bars:
        raise ContractError("INSUFFICIENT_DATA", f"{label}: {len(bars)} bars < minimum {min_bars}")
    if len(bars) > max_bars:
        raise ContractError(
            "INVALID_SCHEMA", f"{label}: {len(bars)} bars > bounded window {max_bars}"
        )


def has_recent_unexplained_gap(
    bars: Sequence[OHLCBar], *, timeframe_minutes: int, lookback: int
) -> bool:
    """Research-lenient weekend-aware gap check (NOT the production gate).

    A gap is a weekend roll (covers Saturday) or an intra-week hole larger
    than 3 timeframes plus an hour. Holiday precision requires the broker
    session calendar and stays with the runtime adapter.
    """
    if len(bars) < 2:
        return False
    tail = list(bars)[-lookback:]
    for previous, current in zip(tail, tail[1:], strict=False):
        delta = current.timestamp - previous.timestamp
        spans_weekend = _covers_saturday(previous.timestamp, current.timestamp)
        max_gap = timedelta(minutes=3 * timeframe_minutes + 60)
        if not spans_weekend and delta > max_gap:
            return True
        if spans_weekend and delta > _WEEKEND_SPAN:
            return True
    return False


def _covers_saturday(start: datetime, end: datetime) -> bool:
    """True when the [start, end] interval contains any Saturday."""
    day = start.date()
    while day <= end.date():
        if day.weekday() == 5:
            return True
        day += timedelta(days=1)
    return False


def true_range(previous: OHLCBar, current: OHLCBar) -> float:
    return max(
        current.high - current.low,
        abs(current.high - previous.close),
        abs(current.low - previous.close),
    )


def atr14(bars: Sequence[OHLCBar]) -> float:
    """Mean of the last 14 true ranges; needs at least 15 bars."""
    if len(bars) < 15:
        raise ContractError("INSUFFICIENT_DATA", "atr14 requires 15 completed bars")
    ranges = [true_range(bars[i - 1], bars[i]) for i in range(len(bars) - 14, len(bars))]
    return sum(ranges) / 14.0


def ema20_series(
    bars: Sequence[OHLCBar], *, window: int = 256, period: int = 20
) -> list[float]:
    """EMA20 over the fixed last-``window`` bars with the v2 SMA seed.

    Returns values aligned with ``bars[-window:]``; positions before the seed
    are ``nan``. Recursion per spec: seed at index ``period-1`` equals the SMA
    of the first ``period`` closes of the window.
    """
    tail = list(bars[-window:])
    if len(tail) < period:
        raise ContractError("INSUFFICIENT_DATA", f"ema20_series requires {period} bars")
    closes = [bar.close for bar in tail]
    out = [math.nan] * len(tail)
    seed = sum(closes[:period]) / period
    out[period - 1] = seed
    k = 2.0 / (period + 1.0)
    for i in range(period, len(tail)):
        out[i] = k * closes[i] + (1.0 - k) * out[i - 1]
    return out


def ema20_at(bars: Sequence[OHLCBar], index: int) -> float | None:
    """EMA20 value at absolute ``index`` within ``bars`` (None before the seed)."""
    window = min(len(bars), 256)
    start = len(bars) - window
    if index < start:
        return None
    series = ema20_series(bars)
    value = series[index - start]
    return None if math.isnan(value) else value


@dataclass(frozen=True)
class Swing:
    """One confirmed fractal extremum."""

    kind: str  # "high" | "low"
    index: int
    timestamp: datetime  # swing_at: pivot bar close time
    price: float
    confirmed_index: int
    confirmed_at: datetime  # close of pivot+2; unusable before this


def confirmed_swings(bars: Sequence[OHLCBar], *, k: int = 2) -> list[Swing]:
    """k-bar fractal swings; ties are not swings; confirmation at pivot+2."""
    if k < 1:
        raise ContractError("INVALID_SCHEMA", "k must be positive")
    swings: list[Swing] = []
    for i in range(k, len(bars) - k):
        window = bars[i - k : i + k + 1]
        pivot = bars[i]
        highs = [bar.high for bar in window]
        lows = [bar.low for bar in window]
        if highs.count(pivot.high) == 1 and pivot.high == max(highs):
            swings.append(
                Swing(
                    kind="high",
                    index=i,
                    timestamp=pivot.timestamp,
                    price=pivot.high,
                    confirmed_index=i + k,
                    confirmed_at=bars[i + k].timestamp,
                )
            )
        if lows.count(pivot.low) == 1 and pivot.low == min(lows):
            swings.append(
                Swing(
                    kind="low",
                    index=i,
                    timestamp=pivot.timestamp,
                    price=pivot.low,
                    confirmed_index=i + k,
                    confirmed_at=bars[i + k].timestamp,
                )
            )
    return swings


def structure_state(
    swings: Sequence[Swing], *, direction: str, as_of_index: int
) -> str:
    """aligned | opposed | neutral | insufficient from confirmed swings only."""
    if direction not in ("long", "short"):
        raise ContractError("INVALID_SCHEMA", "direction must be long or short")
    usable = [s for s in swings if s.confirmed_index < as_of_index]
    highs = [s for s in usable if s.kind == "high"][-2:]
    lows = [s for s in usable if s.kind == "low"][-2:]
    if len(highs) < 2 or len(lows) < 2:
        return "insufficient"
    highs_rising = highs[1].price > highs[0].price
    lows_rising = lows[1].price > lows[0].price
    highs_falling = highs[1].price < highs[0].price
    lows_falling = lows[1].price < lows[0].price
    if direction == "long":
        if highs_rising and lows_rising:
            return "aligned"
        if highs_falling and lows_falling:
            return "opposed"
        return "neutral"
    if highs_falling and lows_falling:
        return "aligned"
    if highs_rising and lows_rising:
        return "opposed"
    return "neutral"


def structure_state_at(
    swings: Sequence[Swing], *, direction: str, as_of: datetime
) -> str:
    """Time-based variant of :func:`structure_state` (swings confirmed by ``as_of``)."""
    if direction not in ("long", "short"):
        raise ContractError("INVALID_SCHEMA", "direction must be long or short")
    usable = [s for s in swings if s.confirmed_at <= as_of]
    highs = [s for s in usable if s.kind == "high"][-2:]
    lows = [s for s in usable if s.kind == "low"][-2:]
    if len(highs) < 2 or len(lows) < 2:
        return "insufficient"
    rising = highs[1].price > highs[0].price and lows[1].price > lows[0].price
    falling = highs[1].price < highs[0].price and lows[1].price < lows[0].price
    if direction == "long":
        if rising:
            return "aligned"
        return "opposed" if falling else "neutral"
    if falling:
        return "aligned"
    return "opposed" if rising else "neutral"


@dataclass(frozen=True)
class Pool:
    """Cluster of >=2 confirmed same-kind swings within tolerance*ATR."""

    kind: str
    lower: float
    upper: float
    swing_indices: tuple[int, ...]
    confirmed_at: datetime  # latest constituent confirmation


def build_pools(
    swings: Sequence[Swing], *, atr_value: float, tolerance: float = 0.1
) -> list[Pool]:
    """Cluster confirmed swings of one kind into pools (>=2 constituents).

    Consecutive constituents must be >=3 bars apart and within
    ``tolerance * atr_value`` of the cluster's current extreme.
    """
    if atr_value <= 0.0 or not math.isfinite(atr_value):
        raise ContractError("INVALID_NUMBER", "build_pools requires a positive ATR")
    pools: list[Pool] = []
    for kind in ("high", "low"):
        same_kind = [s for s in swings if s.kind == kind]
        cluster: list[Swing] = []
        for swing in same_kind:
            if not cluster:
                cluster = [swing]
                continue
            if swing.index - cluster[-1].index < 3:
                cluster = [swing]
                continue
            extreme = max(s.price for s in cluster) if kind == "high" else min(
                s.price for s in cluster
            )
            within = abs(swing.price - extreme) <= tolerance * atr_value
            if within:
                cluster.append(swing)
            else:
                if len(cluster) >= 2:
                    pools.append(_pool_from(cluster, kind))
                cluster = [swing]
        if len(cluster) >= 2:
            pools.append(_pool_from(cluster, kind))
    return pools


def _pool_from(cluster: list[Swing], kind: str) -> Pool:
    prices = [s.price for s in cluster]
    return Pool(
        kind=kind,
        lower=min(prices),
        upper=max(prices),
        swing_indices=tuple(s.index for s in cluster),
        confirmed_at=max(s.confirmed_at for s in cluster),
    )


def session_allows_entry(timestamp: datetime, *, friday_cutoff_hours: float = 14.0) -> bool:
    """Entry window 07:15 <= t < 16:15 UTC; Friday before 14:00 UTC."""
    weekday = timestamp.weekday()
    if weekday >= 5:
        return False
    minutes = timestamp.hour * 60 + timestamp.minute
    if not (7 * 60 + 15 <= minutes < 16 * 60 + 15):
        return False
    if weekday == 4 and timestamp.hour >= friday_cutoff_hours:
        return False
    return True
