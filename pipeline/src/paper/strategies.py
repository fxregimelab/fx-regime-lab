"""AD-T10/T11 deterministic setup detectors (SU1/SU2/SU3; SU4 research-capped).

Implements the frozen spec-02 section 4 initial definitions on completed bars
only. Long rules shown; every short path is the exact sign mirror. Detectors
are pure functions over H1 bars, H4 swings (structure), M15 bars (retests),
the D1 macro-context string and the pair's canonical cost table. No model,
broker or DB access ever enters a rule.

Frozen discipline:

- A candidate exists only after its M15 retest bar CLOSES; the entry is the
  next M15 open (proxy for the next available ask) and must sit inside the
  declared entry band, else the opportunity expires with no trade.
- The session window (07:15<=t<16:15 UTC, Friday before 14:00) gates the entry
  DECISION time. Triggers may form outside the window.
- Stop distance >= 1.2*ATR_H1 and round-trip cost share of 1R <= 0.10; neither
  gate may be relaxed by a caller, and stops are never widened to pass them.
- One candidate per M15 opportunity bar; same-decision precedence is
  SU1 > SU2 > SU3 and an opposite-side conflict at the same decision means
  wait (no trade). SU4 stays research-only (B-capped, half risk) and is not
  implemented for execution in v1.
"""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.paper.config import COSTS
from src.paper.contracts import ContractError
from src.paper.features import (
    OHLCBar,
    Pool,
    Swing,
    atr14,
    build_pools,
    confirmed_swings,
    ema20_series,
    session_allows_entry,
    structure_state_at,
)

_SU1_RETEST_BARS = 4
_SU2_RETEST_BARS = 4
_SU3_RETEST_BARS = 8
_MIN_STOP_ATR = 1.2
_MAX_COST_SHARE = 0.10
_ENTRY_BAND_ATR = 0.25
_M15 = timedelta(minutes=15)
_ONE_HOUR = timedelta(hours=1)


@dataclass(frozen=True)
class SetupCandidate:
    """One fully-confirmed setup with entry, stop and registered expiry."""

    setup_id: str
    side: str
    trigger_at: datetime  # H1 trigger-bar close (SU2: sweep M15 close)
    decision_at: datetime  # retest M15-bar close = entry decision time
    entry_at: datetime  # entry M15-bar open (next available ask proxy)
    entry_price: float
    stop_price: float
    target_a_price: float  # entry +/- 1 initial price-R
    atr_h1: float
    expires_at: datetime
    trigger_ids: tuple[str, ...]


def _checked_direction(direction: str) -> str:
    if direction not in ("long", "short"):
        raise ContractError("INVALID_SCHEMA", "direction must be long or short")
    return direction


def _cost_share(pair: str, entry: float, stop: float) -> float:
    """Round-trip cost as a fraction of the 1R distance (spec 02 section 2)."""
    distance = abs(entry - stop)
    if distance <= 0.0:
        return float("inf")
    total_bps = COSTS.round_trip_bps[pair] + COSTS.slippage_bps
    return (entry * total_bps / 10_000.0) / distance


def _entry_ok(pair: str, entry: float, stop: float, atr: float) -> bool:
    """Stop-distance and cost gates; callers cannot relax either."""
    if abs(entry - stop) < _MIN_STOP_ATR * atr:
        return False
    return _cost_share(pair, entry, stop) <= _MAX_COST_SHARE


def _m15_after(
    m15: Sequence[OHLCBar], start: datetime, limit_bars: int, *, within: timedelta | None = None
) -> list[OHLCBar]:
    """The next ``limit_bars`` M15 bars whose close time is after ``start``.

    ``within`` optionally bounds the search to bars closing no later than
    ``start + within``; used so a single H1 anchor owns exactly one sweep
    window instead of every later anchor re-testing the same M15 bars.
    """
    out: list[OHLCBar] = []
    for bar in m15:
        if bar.timestamp <= start:
            continue
        if within is not None and bar.timestamp > start + within:
            break
        out.append(bar)
        if len(out) >= limit_bars:
            break
    return out


def _next_m15_open(
    m15: Sequence[OHLCBar], after: datetime
) -> tuple[datetime, float] | None:
    for bar in m15:
        if bar.timestamp > after:
            return bar.timestamp - _M15, bar.open
    return None


def _last_before(swings: Sequence[Swing], times: list[datetime], t: datetime) -> Swing | None:
    idx = bisect.bisect_right(times, t)
    return swings[idx - 1] if idx else None


def _split_swings(h1: Sequence[OHLCBar]) -> tuple[list[Swing], list[Swing]]:
    swings = confirmed_swings(list(h1))
    return (
        [s for s in swings if s.kind == "low"],
        [s for s in swings if s.kind == "high"],
    )


def detect_su1(
    h1: Sequence[OHLCBar],
    h4_swings: Sequence[Swing],
    m15: Sequence[OHLCBar],
    *,
    pair: str,
    d1_context: str,
    direction: str,
) -> list[SetupCandidate]:
    """SU1-v1 regime-aligned pullback/reclaim (spec 02 section 4)."""
    _checked_direction(direction)
    candidates: list[SetupCandidate] = []
    if d1_context != direction or len(h1) < 30 or len(m15) < 2:
        return candidates
    low_swings, high_swings = _split_swings(h1)
    low_times = [s.confirmed_at for s in low_swings]
    high_times = [s.confirmed_at for s in high_swings]

    for i in range(26, len(h1)):
        trigger = h1[i]
        atr = atr14(h1[max(0, i - 14) : i + 1])
        if structure_state_at(h4_swings, direction=direction, as_of=trigger.timestamp) != (
            "aligned"
        ):
            continue
        window = list(h1[max(0, i - 255) : i + 1])
        start = i - len(window) + 1
        ema = ema20_series(window)
        prev = h1[i - 1]
        ema_prev = ema[(i - 1) - start]
        if direction == "long" and not prev.close > ema_prev:
            continue
        if direction == "short" and not prev.close < ema_prev:
            continue

        touched = False
        broke = False
        for j in range(i - 6, i):
            bar = h1[j]
            ema_j = ema[j - start]
            probe = bar.low if direction == "long" else bar.high
            if abs(probe - ema_j) <= 0.25 * atr:
                touched = True
            ref_times = low_times if direction == "long" else high_times
            ref = low_swings if direction == "long" else high_swings
            swing = _last_before(ref, ref_times, bar.timestamp)
            if swing is not None:
                if direction == "long" and bar.close < swing.price:
                    broke = True
                if direction == "short" and bar.close > swing.price:
                    broke = True
        if not touched or broke:
            continue

        if direction == "long":
            if not (trigger.close > prev.high and trigger.close > trigger.open):
                continue
        else:
            if not (trigger.close < prev.low and trigger.close < trigger.open):
                continue
        if (trigger.high - trigger.low) > 2.0 * atr:
            continue

        level = trigger.high if direction == "long" else trigger.low
        retest = None
        for bar in _m15_after(m15, trigger.timestamp, _SU1_RETEST_BARS):
            probe = bar.low if direction == "long" else bar.high
            near = abs(probe - level) <= 0.15 * atr
            closed_back = bar.close > level if direction == "long" else bar.close < level
            if near and closed_back:
                retest = bar
                break
        if retest is None:
            continue
        entry = _next_m15_open(m15, retest.timestamp)
        if entry is None:
            continue
        entry_at, entry_price = entry
        if abs(entry_price - level) > _ENTRY_BAND_ATR * atr:
            continue
        if not session_allows_entry(retest.timestamp):
            continue

        pullback_low = min(h1[j].low for j in range(i - 6, i))
        pullback_high = max(h1[j].high for j in range(i - 6, i))
        if direction == "long":
            stop = min(pullback_low, retest.low) - 0.25 * atr
        else:
            stop = max(pullback_high, retest.high) + 0.25 * atr
        if not _entry_ok(pair, entry_price, stop, atr):
            continue
        risk = abs(entry_price - stop)
        target = entry_price + risk if direction == "long" else entry_price - risk
        candidates.append(
            SetupCandidate(
                setup_id="SU1-v1",
                side=direction,
                trigger_at=trigger.timestamp,
                decision_at=retest.timestamp,
                entry_at=entry_at,
                entry_price=entry_price,
                stop_price=stop,
                target_a_price=target,
                atr_h1=atr,
                expires_at=trigger.timestamp + _SU1_RETEST_BARS * _M15,
                trigger_ids=("su1-pullback-ema-touch", "su1-trigger-close", "su1-m15-retest"),
            )
        )
    return candidates


def detect_su2(
    h1: Sequence[OHLCBar],
    h4_swings: Sequence[Swing],
    m15: Sequence[OHLCBar],
    *,
    pair: str,
    d1_context: str,
    direction: str,
) -> list[SetupCandidate]:
    """SU2-v1 sweep, reclaim and held retest (spec 02 section 4)."""
    _checked_direction(direction)
    candidates: list[SetupCandidate] = []
    if d1_context != direction or len(h1) < 40 or len(m15) < 10:
        return candidates
    wanted = "low" if direction == "long" else "high"
    pools: list[Pool] = []
    pools_valid_until = h1[0].timestamp

    for i in range(21, len(h1)):
        anchor = h1[i]
        if anchor.timestamp >= pools_valid_until:
            window = list(h1[max(0, i - 255) : i + 1])
            pools = build_pools(confirmed_swings(window), atr_value=atr14(window))
            pools_valid_until = anchor.timestamp + _ONE_HOUR
        atr = atr14(h1[max(0, i - 14) : i + 1])
        if structure_state_at(h4_swings, direction=direction, as_of=anchor.timestamp) != (
            "aligned"
        ):
            continue
        for sweep in _m15_after(m15, anchor.timestamp, 4, within=_ONE_HOUR):
            sweep_open = sweep.timestamp - _M15
            active = [p for p in pools if p.kind == wanted and p.confirmed_at <= sweep_open]
            active.sort(key=lambda p: p.upper, reverse=True)
            for pool in active:
                if (sweep.high - sweep.low) > 2.0 * atr:
                    continue
                if direction == "long":
                    beyond = pool.lower - sweep.low
                    reclaimed = sweep.close > pool.upper
                else:
                    beyond = sweep.high - pool.upper
                    reclaimed = sweep.close < pool.lower
                if not (0.05 * atr <= beyond <= 0.5 * atr and reclaimed):
                    continue
                retest = None
                failed = False
                for bar in _m15_after(m15, sweep.timestamp, _SU2_RETEST_BARS):
                    if direction == "long" and bar.low < sweep.low:
                        failed = True
                        break
                    if direction == "short" and bar.high > sweep.high:
                        failed = True
                        break
                    if direction == "long":
                        reaches = (
                            pool.lower - 0.15 * atr <= bar.low <= pool.upper + 0.15 * atr
                        )
                        holds = bar.close > pool.upper
                    else:
                        reaches = (
                            pool.lower - 0.15 * atr <= bar.high <= pool.upper + 0.15 * atr
                        )
                        holds = bar.close < pool.lower
                    if reaches and holds:
                        retest = bar
                        break
                if failed or retest is None:
                    continue
                entry = _next_m15_open(m15, retest.timestamp)
                if entry is None:
                    continue
                entry_at, entry_price = entry
                in_band = (
                    pool.lower - _ENTRY_BAND_ATR * atr
                    <= entry_price
                    <= pool.upper + _ENTRY_BAND_ATR * atr
                )
                if not in_band or not session_allows_entry(retest.timestamp):
                    continue
                if direction == "long":
                    stop = sweep.low - 0.25 * atr
                else:
                    stop = sweep.high + 0.25 * atr
                if not _entry_ok(pair, entry_price, stop, atr):
                    continue
                risk = abs(entry_price - stop)
                target = entry_price + risk if direction == "long" else entry_price - risk
                candidates.append(
                    SetupCandidate(
                        setup_id="SU2-v1",
                        side=direction,
                        trigger_at=sweep.timestamp,
                        decision_at=retest.timestamp,
                        entry_at=entry_at,
                        entry_price=entry_price,
                        stop_price=stop,
                        target_a_price=target,
                        atr_h1=atr,
                        expires_at=sweep.timestamp + _SU2_RETEST_BARS * _M15,
                        trigger_ids=("su2-pool", "su2-sweep-reclaim", "su2-held-retest"),
                    )
                )
                break  # one pool per sweep bar: the nearest level wins
    return candidates


def detect_su3(
    h1: Sequence[OHLCBar],
    h4_swings: Sequence[Swing],
    m15: Sequence[OHLCBar],
    *,
    pair: str,
    d1_context: str,
    direction: str,
) -> list[SetupCandidate]:
    """SU3-v1 confirmed breakout/retest (spec 02 section 4)."""
    _checked_direction(direction)
    candidates: list[SetupCandidate] = []
    if d1_context != direction or len(h1) < 30 or len(m15) < 2:
        return candidates
    for i in range(26, len(h1)):
        trigger = h1[i]
        atr = atr14(h1[max(0, i - 14) : i + 1])
        if structure_state_at(h4_swings, direction=direction, as_of=trigger.timestamp) != (
            "aligned"
        ):
            continue
        prior = list(h1[i - 20 : i])
        if direction == "long":
            level = max(b.high for b in prior)
        else:
            level = min(b.low for b in prior)
        zone_lower = level - 0.1 * atr
        zone_upper = level + 0.1 * atr
        if direction == "long":
            body = trigger.close - trigger.open
            exceeds = trigger.close >= zone_upper
        else:
            body = trigger.open - trigger.close
            exceeds = trigger.close <= zone_lower
        if not (exceeds and body >= 0.5 * atr and (trigger.high - trigger.low) <= 2.0 * atr):
            continue

        h1_cursor = i + 1
        retest = None
        for bar in _m15_after(m15, trigger.timestamp, _SU3_RETEST_BARS):
            while h1_cursor < len(h1) and h1[h1_cursor].timestamp <= bar.timestamp:
                closed_bar = h1[h1_cursor]
                zone_failed = (
                    closed_bar.close < zone_lower
                    if direction == "long"
                    else closed_bar.close > zone_upper
                )
                if zone_failed:
                    break
                h1_cursor += 1
            if h1_cursor < len(h1) and h1[h1_cursor].timestamp <= bar.timestamp:
                break  # a zone-failing H1 close invalidates the retest window
            dips = bar.low <= zone_upper if direction == "long" else bar.high >= zone_lower
            holds = bar.close > level if direction == "long" else bar.close < level
            if dips and holds:
                retest = bar
                break
        if retest is None:
            continue
        entry = _next_m15_open(m15, retest.timestamp)
        if entry is None:
            continue
        entry_at, entry_price = entry
        in_band = (
            zone_lower - _ENTRY_BAND_ATR * atr <= entry_price <= zone_upper + _ENTRY_BAND_ATR * atr
        )
        if not in_band or not session_allows_entry(retest.timestamp):
            continue
        retest_extreme = retest.low if direction == "long" else retest.high
        if direction == "long":
            stop = min(retest_extreme, zone_lower) - 0.25 * atr
        else:
            stop = max(retest_extreme, zone_upper) + 0.25 * atr
        if not _entry_ok(pair, entry_price, stop, atr):
            continue
        risk = abs(entry_price - stop)
        target = entry_price + risk if direction == "long" else entry_price - risk
        candidates.append(
            SetupCandidate(
                setup_id="SU3-v1",
                side=direction,
                trigger_at=trigger.timestamp,
                decision_at=retest.timestamp,
                entry_at=entry_at,
                entry_price=entry_price,
                stop_price=stop,
                target_a_price=target,
                atr_h1=atr,
                expires_at=trigger.timestamp + _SU3_RETEST_BARS * _M15,
                trigger_ids=("su3-resistance", "su3-breakout-close", "su3-m15-retest"),
            )
        )
    return candidates


def resolve_conflicts(candidates: Sequence[SetupCandidate]) -> list[SetupCandidate]:
    """One candidate per decision: precedence SU1>SU2>SU3; opposite sides wait."""
    by_decision: dict[datetime, list[SetupCandidate]] = {}
    for candidate in candidates:
        by_decision.setdefault(candidate.decision_at, []).append(candidate)
    precedence = {"SU1-v1": 0, "SU2-v1": 1, "SU3-v1": 2}
    resolved: list[SetupCandidate] = []
    for group in by_decision.values():
        if len({c.side for c in group}) > 1:
            continue  # opposite-side conflict: no trade at this decision
        resolved.append(min(group, key=lambda c: precedence[c.setup_id]))
    return sorted(resolved, key=lambda c: c.decision_at)
