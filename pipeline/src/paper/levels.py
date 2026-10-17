"""Liquidity & structure map for the desk: swings, round numbers, session extremes.

Pure functions over stored bars (no broker access). Consumed by the checklist
engine (``paper/checklist.py``) for stop-past-pool and room-to-target checks, and
by future stop placement in the management policy. Bars are in broker server
time; no timezone assumptions are made beyond the broker's own clock.

Spec: ``docs/DESK_STRATEGY_FRAMEWORK.md`` §2 (L2) — this module is the machine
form of the liquidity layer.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from src.paper.store import Bar

# Round-number grids per pair: (minor step, major figure), in price terms.
# EURUSD: 50-pip minor / 100-pip figure. USDJPY pips are 0.01 → 0.50 / 1.00.
ROUND_STEPS: dict[str, tuple[float, float]] = {
    "EURUSD": (0.0050, 0.0100),
    "USDJPY": (0.50, 1.00),
}

# Tags significant enough to drive checklist decisions (S6/S7). Minor round
# numbers stay in the map for execution placement but never act as walls by
# themselves — they are 50 pips apart and everywhere.
SIGNIFICANT_TAGS: frozenset[str] = frozenset(
    {"swing_h1", "swing_h4", "session_ext", "round_major"}
)


@dataclass(frozen=True)
class Swing:
    time_srv: int
    kind: Literal["high", "low"]
    price: float


@dataclass(frozen=True)
class Level:
    price: float
    tags: tuple[str, ...]
    time_srv: int | None = None


def find_swings(bars: Sequence[Bar], k: int = 2) -> list[Swing]:
    """Strict fractal swings: bar i's high/low is the unique extreme of its ±k window."""
    swings: list[Swing] = []
    n = len(bars)
    for i in range(k, n - k):
        window = bars[i - k : i + k + 1]
        highs = [b.high for b in window]
        lows = [b.low for b in window]
        if bars[i].high == max(highs) and highs.count(bars[i].high) == 1:
            swings.append(Swing(bars[i].time_srv, "high", bars[i].high))
        if bars[i].low == min(lows) and lows.count(bars[i].low) == 1:
            swings.append(Swing(bars[i].time_srv, "low", bars[i].low))
    return swings


def round_levels(pair: str, ref_price: float, span: int = 3) -> list[Level]:
    """Nearest minor + major round numbers around ``ref_price`` (±span steps).

    Levels on both grids (e.g., 1.1200) carry both tags.
    """
    minor, major = ROUND_STEPS[pair]
    tags: dict[float, set[str]] = {}
    for step, tag in ((minor, "round_minor"), (major, "round_major")):
        base = math.floor(ref_price / step)
        for i in range(base - span, base + span + 1):
            price = round(i * step, 6)
            tags.setdefault(price, set()).add(tag)
    return [Level(price=p, tags=tuple(sorted(t))) for p, t in sorted(tags.items())]


def recent_extremes(bars: Sequence[Bar], n: int) -> tuple[float, float] | None:
    """(high, low) over the last ``n`` bars; None when there are no bars."""
    window = bars[-n:]
    if not window:
        return None
    return max(b.high for b in window), min(b.low for b in window)


def build_liquidity_map(
    bars_by_tf: Mapping[str, Sequence[Bar]],
    pair: str,
    *,
    swing_k: int = 2,
    recent_h1: int = 24,
) -> list[Level]:
    """Sorted level map: H4/H1 swings, recent H1 extremes, round numbers.

    The H1 extreme over ``recent_h1`` bars is the session-extreme proxy
    (timezone-safe: it uses the broker's own bar sequence, not wall-clock UTC).
    """
    levels: list[Level] = []
    for tf, tag in (("H4", "swing_h4"), ("H1", "swing_h1")):
        for swing in find_swings(bars_by_tf.get(tf, []), k=swing_k):
            levels.append(Level(swing.price, (tag, swing.kind), swing.time_srv))
    extremes = recent_extremes(bars_by_tf.get("H1", []), recent_h1)
    if extremes is not None:
        hi, lo = extremes
        levels.append(Level(hi, ("session_ext", "high")))
        levels.append(Level(lo, ("session_ext", "low")))
    h1 = bars_by_tf.get("H1", [])
    if h1:
        levels.extend(round_levels(pair, h1[-1].close))
    return sorted(levels, key=lambda lv: lv.price)


def significant_only(levels: Sequence[Level]) -> list[Level]:
    """Keep levels carrying at least one significant tag (see SIGNIFICANT_TAGS)."""
    return [lv for lv in levels if SIGNIFICANT_TAGS.intersection(lv.tags)]


def nearest_level(
    levels: Sequence[Level], price: float, side: Literal["above", "below"]
) -> Level | None:
    """Nearest level strictly above/below ``price``; None when none exists."""
    best: Level | None = None
    for lv in levels:
        if side == "above" and lv.price > price and (best is None or lv.price < best.price):
            best = lv
        elif side == "below" and lv.price < price and (best is None or lv.price > best.price):
            best = lv
    return best


def distance_to_nearest(
    levels: Sequence[Level], price: float, side: Literal["above", "below"]
) -> float | None:
    """Price distance to the nearest level on ``side``; None when none exists."""
    lv = nearest_level(levels, price, side)
    return None if lv is None else abs(lv.price - price)
