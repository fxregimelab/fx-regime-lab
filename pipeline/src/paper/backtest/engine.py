"""Offline trade simulation for the paper desk strategies (research only).

This is a *measurement* harness, not the executor. It replays completed bars,
applies the frozen detector + geometry gates from :mod:`src.paper.strategies`,
then simulates the deterministic management policy in
``docs/specs/autonomous-desk/03-execution-and-recovery.md`` section 7:

- 50% off at +1 initial price-R, stop to break-even plus a cost buffer, then a
  chandelier trail on completed bars.
- early adverse cut, time stop, hard T+5 horizon, Friday 19:00 UTC flatten.

Honesty rules baked in here:

- Only completed bars are used. A decision may reference bars whose close time
  is ``<= decision time``; the entry fills at the next M15 *open* after the
  decision bar closes, never at a price inside the decision bar.
- Every detector call sees a bounded lookback window (spec-02 limits) ending
  at the trigger bar, so no future bar can leak into a decision.
- When one bar spans both the stop and the target, the STOP is assumed to fill
  first (pessimistic). This cannot manufacture an edge.
- Costs come from the canonical table in ``src.paper.config`` and are reported
  separately from gross R.
- Every candidate that is not traded is recorded with an explicit reason, so
  the funnel reconciles: H1 opportunities -> candidates -> admitted -> trades.
"""

from __future__ import annotations

import bisect
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.paper.config import COSTS, LIMITS
from src.paper.features import OHLCBar, Swing, atr14, confirmed_swings
from src.paper.strategies import (
    Rejection,
    SetupCandidate,
    detect_su1,
    detect_su2,
    detect_su3,
    resolve_conflicts,
)

# --- Admission reasons (mirror the spec's portfolio gate order) ------------------

A_PAIR_SLOTS = "pair_slots_full"
A_MAX_SLOTS = "max_concurrent_positions"
A_OPEN_RISK = "max_open_risk"
A_DAILY_STOP = "daily_stop"
A_WEEKLY_STOP = "weekly_stop"
A_NEW_TRADES_DAY = "max_new_trades_per_day"
A_COOLDOWN = "cooldown_after_stop"
A_DUPLICATE = "duplicate_decision"

# --- Exit reasons ---------------------------------------------------------------

X_STOP = "stop"
X_TRAIL = "trail"
X_PARTIAL_THEN_EXIT = "partial_then_exit"
X_EARLY_CUT = "early_adverse_cut"
X_TIME_STOP = "time_stop"
X_HORIZON = "t_plus_5"
X_FRIDAY = "friday_flatten"

_H1_WINDOW = 256   # spec-02 bounded decision window
_M15_LOOKBACK = timedelta(hours=10)  # >= 32 bars so the spec minimum is met
_M15_LOOKAHEAD = timedelta(hours=3)  # SU3 needs at most 8 forward M15 bars


@dataclass(frozen=True)
class BacktestConfig:
    """Knobs that are measurement choices, not strategy changes."""

    starting_equity: float = 10_000.0
    risk_per_trade: float = 0.01          # 1% of equity at risk per trade (1R)
    partial_at_r: float = LIMITS.partial_at_r
    partial_fraction: float = LIMITS.partial_fraction
    breakeven_buffer_pips: float = LIMITS.breakeven_buffer_pips
    trail_atr_mult: float = LIMITS.trail_atr_mult
    early_cut_adverse_r: float = LIMITS.early_cut_adverse_r
    early_cut_hours: int = LIMITS.early_cut_hours
    time_stop_hours: int = LIMITS.time_stop_hours
    time_stop_min_r: float = LIMITS.time_stop_min_r
    horizon_days: int = 5
    cooldown_hours: int = LIMITS.cooldown_after_stop_hours
    friday_flatten_hour: int = 19
    max_new_trades_per_day: int = LIMITS.max_new_trades_per_day
    max_concurrent: int = LIMITS.max_concurrent_positions
    max_per_pair: int = LIMITS.max_positions_per_pair
    max_open_risk_pct: float = LIMITS.max_open_risk_pct
    daily_stop_pct: float = LIMITS.daily_stop_pct
    weekly_stop_pct: float = LIMITS.weekly_stop_pct
    pip_size: dict[str, float] = field(
        default_factory=lambda: {"EURUSD": 0.0001, "USDJPY": 0.01}
    )
    enabled_setups: tuple[str, ...] = ("SU1-v1", "SU2-v1", "SU3-v1")
    # D1 context rule: "ema_slope" = close above/below EMA20_D1 with a rising/
    # falling slope; anything ambiguous is neutral (never silently long).
    d1_ema_period: int = 20
    d1_slope_bars: int = 3


@dataclass
class Trade:
    """One settled parent position, gross and net of canonical costs."""

    pair: str
    setup_id: str
    side: str
    entry_at: datetime
    exit_at: datetime
    entry_price: float
    stop_price: float
    exit_price: float
    atr_h1: float
    risk_price: float
    exit_reason: str
    r_multiple: float          # gross, on the initial 1R
    cost_r: float              # canonical round-trip cost expressed in R
    net_r: float
    mae_r: float               # worst adverse excursion in R
    mfe_r: float               # best favourable excursion in R
    bars_held: int
    partial_taken: bool

    @property
    def win(self) -> bool:
        return self.net_r > 0.0


@dataclass
class BacktestResult:
    pair: str
    start: datetime
    end: datetime
    trades: list[Trade]
    rejections: Counter[str]
    setup_counts: Counter[str]
    opportunities: int
    config: BacktestConfig

    @property
    def net_r(self) -> float:
        return sum(t.net_r for t in self.trades)

    @property
    def gross_r(self) -> float:
        return sum(t.r_multiple for t in self.trades)

    @property
    def costs_r(self) -> float:
        return sum(t.cost_r for t in self.trades)

    @property
    def wins(self) -> list[Trade]:
        return [t for t in self.trades if t.net_r > 0.0]

    @property
    def losses(self) -> list[Trade]:
        return [t for t in self.trades if t.net_r <= 0.0]

    @property
    def win_rate(self) -> float:
        return len(self.wins) / len(self.trades) if self.trades else 0.0

    @property
    def expectancy_r(self) -> float:
        return self.net_r / len(self.trades) if self.trades else 0.0

    @property
    def avg_win_r(self) -> float:
        return sum(t.net_r for t in self.wins) / len(self.wins) if self.wins else 0.0

    @property
    def avg_loss_r(self) -> float:
        return sum(t.net_r for t in self.losses) / len(self.losses) if self.losses else 0.0

    @property
    def profit_factor(self) -> float:
        gross_win = sum(t.net_r for t in self.wins)
        gross_loss = -sum(t.net_r for t in self.losses)
        if gross_loss <= 0.0:
            return float("inf") if gross_win > 0 else 0.0
        return gross_win / gross_loss

    @property
    def total_candidates(self) -> int:
        return sum(self.setup_counts.values())


# --- D1 context -----------------------------------------------------------------


def _ema_full(closes: list[float], period: int) -> list[float]:
    """EMA over the whole series with the spec v2 SMA seed (NaN before the seed)."""
    out = [float("nan")] * len(closes)
    if len(closes) < period:
        return out
    seed = sum(closes[:period]) / period
    out[period - 1] = seed
    k = 2.0 / (period + 1.0)
    for i in range(period, len(closes)):
        out[i] = k * closes[i] + (1.0 - k) * out[i - 1]
    return out


def d1_context_series(
    d1: list[OHLCBar], *, period: int = 20, slope_bars: int = 3
) -> list[tuple[datetime, str]]:
    """Time-varying D1 macro direction from price vs EMA20 and the EMA slope.

    ``long`` requires close above EMA20 and the EMA rising over ``slope_bars``;
    ``short`` the mirror; everything else is ``neutral`` (never assumed long).
    """
    closes = [b.close for b in d1]
    if len(closes) < period + slope_bars:
        return []
    ema = _ema_full(closes, period)
    out: list[tuple[datetime, str]] = []
    for i in range(period + slope_bars, len(d1)):
        here = ema[i]
        back = ema[i - slope_bars]
        if here != here or back != back:  # NaN guard
            continue
        if closes[i] > here and here > back:
            label = "long"
        elif closes[i] < here and here < back:
            label = "short"
        else:
            label = "neutral"
        out.append((d1[i].timestamp, label))
    return out


def context_at(series: list[tuple[datetime, str]], when: datetime) -> str:
    """Latest D1 label known at ``when`` (never a future label)."""
    label = "neutral"
    for ts, value in series:
        if ts > when:
            break
        label = value
    return label


# --- Detection over bounded windows ---------------------------------------------


def _h4_swings_at(
    h4: list[OHLCBar], h4_times: list[datetime], when: datetime, cache: dict[int, list[Swing]]
) -> list[Swing]:
    """Confirmed H4 swings known at ``when``, computed once per H4 close.

    ``structure_state_at`` filters on ``confirmed_at`` anyway; slicing keeps the
    per-call cost bounded and the cache avoids re-running fractal detection for
    every H1 bar inside the same H4 period.
    """
    import bisect as _bisect

    idx = _bisect.bisect_right(h4_times, when)
    if idx <= 0:
        return []
    key: int = idx
    if key not in cache:
        cache[key] = confirmed_swings(h4[:idx])
    return cache[key]


def evaluate_h1_bar(
    index: int,
    *,
    pair: str,
    h1: list[OHLCBar],
    swings: list[Swing],
    m15_window: list[OHLCBar],
    d1_series: list[tuple[datetime, str]],
    cfg: BacktestConfig,
    rejections: Counter[str],
) -> list[SetupCandidate]:
    """Run every enabled detector at one completed H1 bar, using only its past."""
    trigger = h1[index]
    window = h1[max(0, index - _H1_WINDOW + 1) : index + 1]
    if len(window) < 60 or len(m15_window) < 32:
        return []
    last_in_window = len(window) - 1

    found: list[SetupCandidate] = []
    for setup_id, detector in (
        ("SU1-v1", detect_su1),
        ("SU2-v1", detect_su2),
        ("SU3-v1", detect_su3),
    ):
        if setup_id not in cfg.enabled_setups:
            continue
        for direction in ("long", "short"):
            label = context_at(d1_series, trigger.timestamp)
            if label != direction:
                rejections[f"{setup_id}:d1_context_mismatch"] += 1
                continue
            sink: list[Rejection] = []
            found += detector(
                window,
                swings,
                m15_window,
                pair=pair,
                d1_context=label,
                direction=direction,
                only_index=last_in_window,
                rejections=sink,
            )
            for rejection in sink:
                rejections[f"{rejection.setup_id}:{rejection.reason}"] += 1
    return resolve_conflicts(found)


# --- Trade management -----------------------------------------------------------


def _h1_atr_until(h1: list[OHLCBar], when: datetime) -> float | None:
    bars = [b for b in h1 if b.timestamp <= when]
    if len(bars) < 15:
        return None
    return atr14(bars[-15:])


def _last_h1_close_at(h1: list[OHLCBar], when: datetime) -> datetime | None:
    """Close time of the newest completed H1 bar at ``when`` (trail cadence)."""
    latest = None
    for b in h1:
        if b.timestamp > when:
            break
        latest = b.timestamp
    return latest


def simulate_trade(
    cand: SetupCandidate,
    pair: str,
    m15: list[OHLCBar],
    h1: list[OHLCBar],
    *,
    cfg: BacktestConfig,
) -> Trade | None:
    """Walk forward from the entry bar and apply the deterministic management.

    Bars are consumed in order; each bar's high/low decides whether the stop,
    the 1R partial or the trail was touched. Same-bar stop+target resolves to
    the stop (pessimistic).
    """
    entry_index = None
    for k, bar in enumerate(m15):
        if bar.timestamp - timedelta(minutes=15) >= cand.entry_at:
            entry_index = k
            break
    if entry_index is None:
        return None

    side = cand.side
    entry = cand.entry_price
    stop = cand.stop_price
    risk = abs(entry - stop)
    if risk <= 0.0:
        return None
    pip = cfg.pip_size[pair]
    be_buffer = cfg.breakeven_buffer_pips * pip

    total_bps = COSTS.round_trip_bps[pair] + COSTS.slippage_bps
    cost_r = (entry * total_bps / 10_000.0) / risk

    partial_done = False
    remaining = 1.0
    realised_r = 0.0
    current_stop = stop
    mae_r = 0.0
    mfe_r = 0.0
    entry_at = cand.entry_at
    exit_at = entry_at
    exit_price = entry
    exit_reason = X_HORIZON
    bars_held = 0
    time_stop_done = False
    last_trail_h1: datetime | None = None
    best_price = entry

    horizon = entry_at + timedelta(days=cfg.horizon_days)

    def close_r(price: float) -> float:
        return (price - entry) / risk if side == "long" else (entry - price) / risk

    for bar in m15[entry_index:]:
        bar_open_at = bar.timestamp - timedelta(minutes=15)
        if bar_open_at < entry_at:
            continue
        if bar_open_at > horizon:
            break
        bars_held += 1

        favourable = (bar.high - entry) if side == "long" else (entry - bar.low)
        adverse = (entry - bar.low) if side == "long" else (bar.high - entry)
        mfe_r = max(mfe_r, favourable / risk)
        mae_r = max(mae_r, adverse / risk)
        best_price = max(best_price, bar.high) if side == "long" else min(best_price, bar.low)

        # 1. protective stop first: pessimistic when a bar spans stop and target
        stop_hit = bar.low <= current_stop if side == "long" else bar.high >= current_stop
        if stop_hit:
            realised_r += remaining * close_r(current_stop)
            exit_price, exit_at = current_stop, bar.timestamp
            exit_reason = X_TRAIL if current_stop != stop else (
                X_PARTIAL_THEN_EXIT if partial_done else X_STOP
            )
            remaining = 0.0
            break

        # 2. partial at +1R, then stop to break-even + cost buffer
        if not partial_done:
            target = entry + risk if side == "long" else entry - risk
            target_hit = bar.high >= target if side == "long" else bar.low <= target
            if target_hit:
                realised_r += cfg.partial_fraction * cfg.partial_at_r
                remaining -= cfg.partial_fraction
                partial_done = True
                current_stop = entry + be_buffer if side == "long" else entry - be_buffer

        age = bar.timestamp - entry_at

        # 3. early adverse cut: before age 2h, a completed close at/beyond -0.5R
        if age <= timedelta(hours=cfg.early_cut_hours) and mae_r >= cfg.early_cut_adverse_r:
            if close_r(bar.close) <= -cfg.early_cut_adverse_r:
                realised_r += remaining * close_r(bar.close)
                exit_price, exit_at, exit_reason = bar.close, bar.timestamp, X_EARLY_CUT
                remaining = 0.0
                break

        # 4. time stop: one-shot check once the trade reaches age 4h
        if not time_stop_done and age >= timedelta(hours=cfg.time_stop_hours):
            time_stop_done = True
            if close_r(bar.close) < cfg.time_stop_min_r:
                realised_r += remaining * close_r(bar.close)
                exit_price, exit_at, exit_reason = bar.close, bar.timestamp, X_TIME_STOP
                remaining = 0.0
                break

        # 5. Friday 19:00 UTC flatten
        if bar.timestamp.weekday() == 4 and bar.timestamp.hour >= cfg.friday_flatten_hour:
            realised_r += remaining * close_r(bar.close)
            exit_price, exit_at, exit_reason = bar.close, bar.timestamp, X_FRIDAY
            remaining = 0.0
            break

        # 6. chandelier trail, recomputed only when a new H1 bar has closed
        if partial_done:
            last_h1 = _last_h1_close_at(h1, bar.timestamp)
            if last_h1 is not None and last_h1 != last_trail_h1:
                last_trail_h1 = last_h1
                atr = _h1_atr_until(h1, bar.timestamp)
                if atr is not None:
                    if side == "long":
                        current_stop = max(current_stop, best_price - cfg.trail_atr_mult * atr)
                    else:
                        current_stop = min(current_stop, best_price + cfg.trail_atr_mult * atr)

    if remaining > 0.0:
        last = m15[-1] if m15 else None
        if last is not None:
            realised_r += remaining * close_r(last.close)
            exit_price = last.close
            exit_at = last.timestamp

    return Trade(
        pair=pair,
        setup_id=cand.setup_id,
        side=side,
        entry_at=entry_at,
        exit_at=exit_at,
        entry_price=entry,
        stop_price=stop,
        exit_price=exit_price,
        atr_h1=cand.atr_h1,
        risk_price=risk,
        exit_reason=exit_reason,
        r_multiple=realised_r,
        cost_r=cost_r,
        net_r=realised_r - cost_r,
        mae_r=mae_r,
        mfe_r=mfe_r,
        bars_held=bars_held,
        partial_taken=partial_done,
    )


# --- Driver ---------------------------------------------------------------------


def run_backtest(
    pair: str,
    *,
    d1: list[OHLCBar],
    h4: list[OHLCBar],
    h1: list[OHLCBar],
    m15: list[OHLCBar],
    cfg: BacktestConfig | None = None,
) -> BacktestResult:
    """Evaluate every H1 bar, admit candidates, and settle the survivors."""
    cfg = cfg or BacktestConfig()
    d1_series = d1_context_series(
        d1, period=cfg.d1_ema_period, slope_bars=cfg.d1_slope_bars
    )
    rejections: Counter[str] = Counter()
    setup_counts: Counter[str] = Counter()
    candidates: list[SetupCandidate] = []
    opportunities = 0

    m15_start = m15[0].timestamp if m15 else datetime.min
    m15_times = [b.timestamp for b in m15]
    h4_times = [b.timestamp for b in h4]
    swing_cache: dict[int, list[Swing]] = {}
    for i in range(len(h1)):
        trigger = h1[i]
        if trigger.timestamp < m15_start:
            continue
        opportunities += 1
        swings = _h4_swings_at(h4, h4_times, trigger.timestamp, swing_cache)
        lo = bisect.bisect_right(m15_times, trigger.timestamp - _M15_LOOKBACK)
        hi = bisect.bisect_right(m15_times, trigger.timestamp + _M15_LOOKAHEAD)
        m15_window = m15[lo:hi]
        for cand in evaluate_h1_bar(
            i, pair=pair, h1=h1, swings=swings, m15_window=m15_window,
            d1_series=d1_series, cfg=cfg, rejections=rejections,
        ):
            candidates.append(cand)

    candidates.sort(key=lambda c: (c.entry_at, c.decision_at))
    trades: list[Trade] = []
    open_trades: list[Trade] = []
    last_stop: dict[tuple[str, str], datetime] = {}
    day_counts: Counter[str] = Counter()
    equity = cfg.starting_equity
    day_start_equity = equity
    current_day: str | None = None
    week_start_equity = equity
    current_week: str | None = None
    seen: set[tuple[datetime, str]] = set()

    for cand in candidates:
        key_seen = (cand.decision_at, cand.side)
        if key_seen in seen:
            rejections[A_DUPLICATE] += 1
            continue
        seen.add(key_seen)

        day_key = cand.entry_at.date().isoformat()
        iso = cand.entry_at.isocalendar()
        week_key = f"{iso.year}-W{iso.week}"
        if day_key != current_day:
            current_day = day_key
            day_start_equity = equity
            day_counts.clear()
        if week_key != current_week:
            current_week = week_key
            week_start_equity = equity

        open_trades = [t for t in open_trades if t.exit_at > cand.entry_at]

        if (equity - day_start_equity) / day_start_equity <= -cfg.daily_stop_pct:
            rejections[A_DAILY_STOP] += 1
            continue
        if (equity - week_start_equity) / week_start_equity <= -cfg.weekly_stop_pct:
            rejections[A_WEEKLY_STOP] += 1
            continue
        if day_counts[day_key] >= cfg.max_new_trades_per_day:
            rejections[A_NEW_TRADES_DAY] += 1
            continue
        if len(open_trades) >= cfg.max_concurrent:
            rejections[A_MAX_SLOTS] += 1
            continue
        if sum(1 for t in open_trades if t.pair == pair) >= cfg.max_per_pair:
            rejections[A_PAIR_SLOTS] += 1
            continue
        stop_key = (pair, cand.side)
        stopped_at = last_stop.get(stop_key)
        if stopped_at is not None and cand.entry_at - stopped_at < timedelta(
            hours=cfg.cooldown_hours
        ):
            rejections[A_COOLDOWN] += 1
            continue
        if len(open_trades) * cfg.risk_per_trade + cfg.risk_per_trade > cfg.max_open_risk_pct:
            rejections[A_OPEN_RISK] += 1
            continue

        trade = simulate_trade(cand, pair, m15, h1, cfg=cfg)
        if trade is None:
            rejections["no_entry_bar"] += 1
            continue
        setup_counts[cand.setup_id] += 1
        trades.append(trade)
        day_counts[day_key] += 1
        equity += trade.net_r * cfg.risk_per_trade * cfg.starting_equity
        if trade.exit_reason in (X_STOP, X_EARLY_CUT, X_TIME_STOP):
            last_stop[stop_key] = trade.exit_at
        if trade.exit_at > cand.entry_at:
            open_trades.append(trade)

    return BacktestResult(
        pair=pair,
        # Detection needs M15 retests, so the tradeable sample starts when the
        # M15 series starts, not when the (longer) H1 series starts.
        start=m15[0].timestamp if m15 else (h1[0].timestamp if h1 else datetime.min),
        end=h1[-1].timestamp if h1 else datetime.min,
        trades=trades,
        rejections=rejections,
        setup_counts=setup_counts,
        opportunities=opportunities,
        config=cfg,
    )
