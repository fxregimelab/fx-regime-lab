"""Offline trade simulation for the paper desk strategies (research only).

This is a *measurement* harness, not the executor. It replays completed bars,
applies the frozen detector + geometry gates from :mod:`src.paper.strategies`,
then simulates the deterministic management policy in
``docs/specs/autonomous-desk/03-execution-and-recovery.md`` section 7:

- 50% off at +1 initial price-R, stop to break-even plus a cost buffer, then a
  chandelier trail on completed bars.
- early adverse cut, time stop, hard calendar-day horizon, Friday 19:00 UTC
  flatten.

Honesty rules baked in here:

- Only completed bars are used. A decision may reference bars whose close time
  is ``<= decision time``; the entry fills at the next M15 *open* after the
  decision bar closes, never at a price inside the decision bar.
- Every detector call sees a bounded lookback window (spec-02 limits) ending
  at the trigger bar, so no future bar can leak into a decision.
- When one bar spans both the stop and the target, the STOP is assumed to fill
  first (pessimistic). This cannot manufacture an edge.
- A gap through the protective stop fills at the ADVERSE OPEN, never at the
  stop price: a stop is not a guaranteed fill price. A loss can therefore be
  larger than the nominal 1R and is never clamped back to it.
- The hold horizon is a CALENDAR-DAY research bound. It is NOT broker-session
  T+5: AD execution spec (03) section 7 counts T+5 with verified broker
  trading sessions, which this offline harness does not have. The two are
  bound separately and the mismatch is reported, never relabelled.
- Settlement only ever uses bars at or before the horizon. A trade that is
  still open when the input ends before its horizon is CENSORED: it is
  reported as unresolved, never booked as a settled win or dropped as a loss.
- Costs come from the canonical table in ``src.paper.config`` and are reported
  separately from gross R.
- Every candidate that is not traded is recorded with an explicit reason, so
  the funnel reconciles: H1 opportunities -> candidates -> admitted -> trades.
- EVENT TIME: the equity is derived from SETTLED exits only. A trade's outcome
  is booked when its exit happens, never when it is admitted, so a later
  opportunity can never be funded by a future outcome. An open position holds
  its slot and its stop-risk reservation while it is open.
- A censored position contributes NOTHING to the equity and keeps its slot and
  its reservation until the end of the sample: its outcome is unknown, so it
  frees nothing.
- The entry fill must be a REAL M15 open. A candidate whose planned entry
  price is not the open of the next M15 bar is rejected with
  ``A_ENTRY_FILL_MISMATCH`` and is never booked.
- KNOWN LIMITATION (R1): the detector gates (stop floor, cost share, entry
  band) are evaluated at the planned fill price, which is the NEXT bar's open
  and therefore not known at decision time. This is a mild lookahead in the
  accept/reject decision, not in the fill itself.
- KNOWN LIMITATION (R2): there is NO fill model. The harness assumes a market
  fill at the next open; it models no slippage beyond the canonical cost table,
  no partial fills and no no-fill. The canonical cost table is a COST model,
  not a fill model.
- The settled-only aggregates are the default (``net_r``, ``gross_r``,
  ``costs_r``, ``expectancy_r``). The ``*_all`` variants, ``unresolved_r`` and
  the counts carry the censored tail explicitly instead of hiding it.
- Same-timestamp ambiguity is resolved conservatively: at an equal timestamp
  the exits settle before the entries, and simultaneous entries are ordered by
  ``(entry_at, decision_at, pair, setup_id)``, so the second entry always sees
  the first entry's reservation. The joint driver records those tie-breaks; the
  single-pair ``run_backtest`` applies the same order but does not record them.
- The correlated-USD ticket cap is applied by the joint driver
  (``src.paper.backtest.portfolio``). ``run_backtest`` passes no such gate, so
  the two paths agree only while ``max_per_pair`` equals
  ``max_same_usd_sign_tickets``.

MANAGEMENT IS NOT CERTIFIED BY THIS MODULE. The management rules implemented
here (a ONE-CLOSE early adverse cut and an UNCONDITIONAL Friday flatten) still
diverge from AD execution spec (03) section 7, which requires a two-close
no-reclaim cut and a conditional Friday flatten. The divergence is a known
open item for PD-03. Nothing here certifies the management policy.

The money unit of this module is PRICE-R: one R is the original stop
distance of the parent. The all-in parent-R of the payoff mandate
(``D = G + A``) belongs to ``src.paper.backtest.payoff`` and is never mixed
into these fields.
"""

from __future__ import annotations

import bisect
import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
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
# The planned fill is not the open of the next M15 bar: the candidate is
# rejected, never booked at a price that no bar opened at.
A_ENTRY_FILL_MISMATCH = "entry_fill_mismatch"
# Correlated one-way USD load: the joint (cross-pair) ticket cap.
A_USD_SIGN_CAP = "usd_exposure_cap"
# The M15 series holds no bar at or after the planned entry.
A_NO_ENTRY_BAR = "no_entry_bar"
A_INVALID_RISK = "invalid_risk"

# --- Exit reasons ---------------------------------------------------------------

X_STOP = "stop"
X_TRAIL = "trail"
X_PARTIAL_THEN_EXIT = "partial_then_exit"
X_EARLY_CUT = "early_adverse_cut"
X_TIME_STOP = "time_stop"
# The research horizon is a calendar-day bound, NOT broker-session T+5. The
# label says so; it is never relabelled as a trading-session count.
X_HORIZON = "horizon_calendar_day"
X_FRIDAY = "friday_flatten"
# The input ended before the horizon: the outcome is unknown, not settled.
X_CENSORED = "censored_data_end"

# Basis of the hold horizon recorded on every trade. Broker-session T+5 is a
# separate, unbound semantic (AD execution spec 03 section 7).
HORIZON_BASIS = "calendar_day"

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
    """One parent position, gross and net of canonical costs.

    A trade is SETTLED when its outcome is resolved. A censored trade (the
    input ended before its horizon) is not settled: it is never a win, never
    a settled loss, and it never contributes to the settled-only aggregates.
    """

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
    r_multiple: float          # gross, on the initial 1R (PRICE-R)
    cost_r: float              # canonical round-trip cost expressed in R
    net_r: float
    mae_r: float               # worst adverse excursion in R
    mfe_r: float               # best favourable excursion in R
    bars_held: int
    partial_taken: bool
    # True when the input ended before the horizon and the outcome is unknown.
    # A censored trade is neither a settled win nor a dropped loss.
    censored: bool = False
    # Basis of the hold horizon this trade was managed under.
    horizon_basis: str = HORIZON_BASIS

    @property
    def settled(self) -> bool:
        """True when the outcome is resolved; a censored trade is not settled."""
        return not self.censored

    @property
    def win(self) -> bool:
        """A win is a SETTLED trade with a positive net R.

        A censored trade is never a win, whatever its marked R says.
        """
        return self.settled and self.net_r > 0.0


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
    # Detector-emitted candidates (before admission). The funnel needs the
    # emitted / admitted / settled split: ``setup_counts`` counts ADMITTED
    # trades per setup, never the emitted candidates.
    candidates_emitted: int = 0
    emitted_setup_counts: Counter[str] = field(default_factory=Counter)

    @property
    def trade_count(self) -> int:
        """Every booked trade, settled or censored."""
        return len(self.trades)

    @property
    def settled_count(self) -> int:
        """Trades with a resolved outcome."""
        return len(self.settled_trades)

    @property
    def censored_count(self) -> int:
        """Unresolved trades: the input ended before their horizon."""
        return len(self.censored_trades)

    @property
    def admitted_count(self) -> int:
        """Candidates that passed admission and were booked."""
        return len(self.trades)

    @property
    def net_r(self) -> float:
        """SETTLED-ONLY net R (A1). Censored trades are excluded."""
        return sum(t.net_r for t in self.settled_trades)

    @property
    def gross_r(self) -> float:
        """SETTLED-ONLY gross R (A1). Censored trades are excluded."""
        return sum(t.r_multiple for t in self.settled_trades)

    @property
    def costs_r(self) -> float:
        """SETTLED-ONLY costs in R (A1). Censored trades are excluded."""
        return sum(t.cost_r for t in self.settled_trades)

    @property
    def net_r_all(self) -> float:
        """Net R over EVERY booked trade, censored tail included."""
        return sum(t.net_r for t in self.trades)

    @property
    def gross_r_all(self) -> float:
        """Gross R over EVERY booked trade, censored tail included."""
        return sum(t.r_multiple for t in self.trades)

    @property
    def costs_r_all(self) -> float:
        """Costs in R over EVERY booked trade, censored tail included."""
        return sum(t.cost_r for t in self.trades)

    @property
    def unresolved_r(self) -> float:
        """The net R that is NOT settled: the censored tail only.

        ``net_r_all == net_r + unresolved_r`` always holds.
        """
        return sum(t.net_r for t in self.censored_trades)

    @property
    def settled_trades(self) -> list[Trade]:
        """Trades with a resolved outcome; a censored trade is not settled."""
        return [t for t in self.trades if not t.censored]

    @property
    def censored_trades(self) -> list[Trade]:
        """Unresolved trades: the input ended before their horizon."""
        return [t for t in self.trades if t.censored]

    @property
    def wins(self) -> list[Trade]:
        return [t for t in self.settled_trades if t.net_r > 0.0]

    @property
    def losses(self) -> list[Trade]:
        return [t for t in self.settled_trades if t.net_r <= 0.0]

    @property
    def win_rate(self) -> float:
        settled = self.settled_trades
        return len(self.wins) / len(settled) if settled else 0.0

    @property
    def expectancy_r(self) -> float:
        """SETTLED-ONLY expectancy (A1): net R per SETTLED trade."""
        settled = self.settled_trades
        return self.net_r / len(settled) if settled else 0.0

    @property
    def expectancy_r_all(self) -> float:
        """Expectancy over EVERY booked trade, censored tail included."""
        return self.net_r_all / len(self.trades) if self.trades else 0.0

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
        """ADMITTED trades per setup summed; kept for the legacy funnel."""
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


@dataclass(frozen=True)
class DetectionResult:
    """The detector phase only: emitted candidates, rejections and coverage.

    No admission, no portfolio state and no settlement happen here, so the
    same detection can be replayed against a SHARED joint portfolio.
    """

    pair: str
    candidates: tuple[SetupCandidate, ...]
    rejections: Counter[str]
    opportunities: int
    emitted_by_setup: Counter[str]


def detect_candidates(
    pair: str,
    *,
    d1: list[OHLCBar],
    h4: list[OHLCBar],
    h1: list[OHLCBar],
    m15: list[OHLCBar],
    cfg: BacktestConfig | None = None,
) -> DetectionResult:
    """Evaluate every H1 bar and emit the candidates that pass the detectors.

    This is the DETECTION half of :func:`run_backtest`, split out so the
    joint (cross-pair) driver can admit the candidates of several pairs
    against one shared portfolio. It never admits, sizes or settles anything.
    """
    cfg = cfg or BacktestConfig()
    d1_series = d1_context_series(
        d1, period=cfg.d1_ema_period, slope_bars=cfg.d1_slope_bars
    )
    rejections: Counter[str] = Counter()
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

    candidates.sort(key=lambda c: (c.entry_at, c.decision_at, c.setup_id, c.side))
    emitted_by_setup: Counter[str] = Counter()
    for cand in candidates:
        emitted_by_setup[cand.setup_id] += 1
    return DetectionResult(
        pair=pair,
        candidates=tuple(candidates),
        rejections=rejections,
        opportunities=opportunities,
        emitted_by_setup=emitted_by_setup,
    )


# --- Trade management -----------------------------------------------------------


def round_trip_cost_r(pair: str, entry: float, risk: float) -> float:
    """Canonical round-trip cost (spread + slippage) expressed in PRICE-R.

    The cost is charged once per parent, on the original risk distance. It is
    never re-derived from an exit price and never charged twice for the two
    exit legs.
    """
    total_bps = COSTS.round_trip_bps[pair] + COSTS.slippage_bps
    return (entry * total_bps / 10_000.0) / risk


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


def entry_fill_bar(m15: Sequence[OHLCBar], entry_at: datetime) -> OHLCBar | None:
    """The M15 bar whose OPEN is the planned fill.

    ``OHLCBar.timestamp`` is the CLOSE time, so the bar that OPENS at
    ``entry_at`` closes at ``entry_at + 15 minutes``. The fill bar is the
    first bar that opens at or after the planned entry; ``None`` means the
    series holds no such bar.
    """
    for bar in m15:
        if bar.timestamp - timedelta(minutes=15) >= entry_at:
            return bar
    return None


def entry_fill_mismatch(
    cand: SetupCandidate,
    m15: Sequence[OHLCBar],
    *,
    rel_tol: float = 1e-9,
    abs_tol: float = 1e-12,
) -> str | None:
    """``A_ENTRY_FILL_MISMATCH`` when the planned fill is not a real M15 open.

    The fill invariant is "fill = next M15 open". A candidate whose planned
    entry price is not the open of the fill bar (or whose planned entry time
    is not a bar open at all) is NOT booked: the engine fails closed with
    this reason instead of silently booking a price no bar opened at.

    ``None`` means the invariant holds, or that the series holds no fill bar
    at all (that case is reported separately as ``A_NO_ENTRY_BAR``).
    """
    bar = entry_fill_bar(m15, cand.entry_at)
    if bar is None:
        return None
    if bar.timestamp - timedelta(minutes=15) != cand.entry_at:
        return A_ENTRY_FILL_MISMATCH
    if not math.isclose(bar.open, cand.entry_price, rel_tol=rel_tol, abs_tol=abs_tol):
        return A_ENTRY_FILL_MISMATCH
    return None


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
    the stop (pessimistic). A gap through the stop fills at the adverse open.
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

    cost_r = round_trip_cost_r(pair, entry, risk)

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
    censored = False
    last_in_horizon: OHLCBar | None = None

    # Calendar-day research horizon. NOT broker-session T+5 (AD execution spec
    # 03 section 7): that count needs verified broker trading sessions, which
    # this offline harness does not have. The basis is recorded on the trade.
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
        last_in_horizon = bar

        favourable = (bar.high - entry) if side == "long" else (entry - bar.low)
        adverse = (entry - bar.low) if side == "long" else (bar.high - entry)
        mfe_r = max(mfe_r, favourable / risk)
        mae_r = max(mae_r, adverse / risk)
        best_price = max(best_price, bar.high) if side == "long" else min(best_price, bar.low)

        # 1. protective stop first: pessimistic when a bar spans stop and target
        stop_hit = bar.low <= current_stop if side == "long" else bar.high >= current_stop
        if stop_hit:
            # A gap through the stop fills at the ADVERSE OPEN, never at the
            # stop price: a stop is not a guaranteed fill price, so the loss
            # can exceed the nominal 1R and is never clamped back to it.
            fill_price = (
                min(current_stop, bar.open) if side == "long" else max(current_stop, bar.open)
            )
            realised_r += remaining * close_r(fill_price)
            exit_price, exit_at = fill_price, bar.timestamp
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
        last = last_in_horizon
        if last is not None and last.timestamp >= horizon:
            # The calendar-day horizon is reached inside the data: close the
            # remainder at the close of the last completed bar that opened at
            # or before the horizon. No later bar can change this settlement.
            realised_r += remaining * close_r(last.close)
            exit_price = last.close
            exit_at = last.timestamp
            exit_reason = X_HORIZON
        else:
            # The input ended before the horizon: the outcome is UNKNOWN. The
            # remainder is marked at the last observed close and the trade is
            # reported as censored, never booked as a settled win or dropped
            # as a loss.
            censored = True
            exit_reason = X_CENSORED
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
        censored=censored,
        horizon_basis=HORIZON_BASIS,
    )


# --- Event-time portfolio replay -------------------------------------------------


@dataclass(frozen=True)
class PairCandidate:
    """One candidate together with the pair it belongs to."""

    pair: str
    candidate: SetupCandidate


@dataclass(frozen=True)
class OpenPosition:
    """An admitted parent position that still holds a slot and its reservation.

    A censored position keeps BOTH until the end of the sample: its outcome
    is unknown, so it frees neither the slot nor the stop-risk reservation.
    """

    pair: str
    setup_id: str
    side: str
    entry_at: datetime
    exit_at: datetime
    net_r: float
    cost_r: float
    exit_reason: str
    censored: bool


@dataclass
class ReplayState:
    """Event-time portfolio state. Only SETTLED exits move the equity."""

    equity: float
    starting_equity: float
    open_positions: list[OpenPosition] = field(default_factory=list)
    day_counts: Counter[str] = field(default_factory=Counter)
    last_stop: dict[tuple[str, str], datetime] = field(default_factory=dict)
    day_start_equity: float = 0.0
    week_start_equity: float = 0.0
    current_day: str | None = None
    current_week: str | None = None


@dataclass(frozen=True)
class ReplayEvent:
    """One chronological portfolio event: an entry, an exit or a rejection.

    ``net_r`` is the REALISED net R of the position. On an EXIT event it is the
    outcome that was just booked. On an ENTRY event it is the position's FINAL
    net R, carried for convenience -- it is a FUTURE value and was NOT known at
    the entry timestamp. ``equity`` on an entry event is the pre-outcome
    equity, which is the number that must never see a future result.
    """

    at: datetime
    kind: str
    pair: str
    setup_id: str
    side: str
    reason: str
    net_r: float
    equity: float


@dataclass(frozen=True)
class ReplayOutcome:
    """The result of one event-time replay."""

    trades: tuple[Trade, ...]
    rejections: Counter[str]
    events: tuple[ReplayEvent, ...]
    equity: float
    open_positions: tuple[OpenPosition, ...]


# An optional extra portfolio gate. It receives the live state, the candidate
# and the planned cost in R, and returns a rejection reason or None.
PortfolioGate = Callable[[ReplayState, PairCandidate, float], str | None]


def order_candidates(candidates: Sequence[PairCandidate]) -> list[PairCandidate]:
    """The A4 order: ``(entry_at, decision_at, pair, setup_id)``.

    ``side`` is the final, deterministic tie-break so that two candidates that
    share every other key still have one reproducible order.
    """
    return sorted(
        candidates,
        key=lambda pc: (
            pc.candidate.entry_at,
            pc.candidate.decision_at,
            pc.pair,
            pc.candidate.setup_id,
            pc.candidate.side,
        ),
    )


def _settle(
    state: ReplayState,
    events: list[ReplayEvent],
    positions: Sequence[OpenPosition],
    *,
    cfg: BacktestConfig,
) -> None:
    """Book the given settled exits: equity, cooldown and the event log."""
    for position in sorted(
        positions, key=lambda p: (p.exit_at, p.pair, p.setup_id, p.side)
    ):
        state.equity += position.net_r * cfg.risk_per_trade * cfg.starting_equity
        state.open_positions = [p for p in state.open_positions if p is not position]
        if position.exit_reason in (X_STOP, X_EARLY_CUT, X_TIME_STOP):
            state.last_stop[(position.pair, position.side)] = position.exit_at
        events.append(
            ReplayEvent(
                at=position.exit_at,
                kind="exit",
                pair=position.pair,
                setup_id=position.setup_id,
                side=position.side,
                reason=position.exit_reason,
                net_r=position.net_r,
                equity=state.equity,
            )
        )


def _settle_due(
    state: ReplayState,
    events: list[ReplayEvent],
    *,
    now: datetime,
    cfg: BacktestConfig,
) -> None:
    """Settle every exit that happened at or before ``now``.

    A censored position is NEVER settled: it keeps its slot and its
    reservation until the end of the sample.
    """
    due = [p for p in state.open_positions if not p.censored and p.exit_at <= now]
    _settle(state, events, due, cfg=cfg)


def _admission_reason(
    state: ReplayState,
    pc: PairCandidate,
    *,
    cfg: BacktestConfig,
) -> str | None:
    """The first failing portfolio gate, or None when the candidate is admitted.

    The gates are the same ones the single-pair replay always applied, in the
    same order. The loss-capacity breaches are ENTRY LATCHES: they block new
    entries and never liquidate an open position (that would need a
    bar-driven engine, which is a separate packet).
    """
    cand = pc.candidate
    pair = pc.pair
    day_key = cand.entry_at.date().isoformat()

    if state.day_start_equity > 0.0 and (
        (state.equity - state.day_start_equity) / state.day_start_equity
        <= -cfg.daily_stop_pct
    ):
        return A_DAILY_STOP
    if state.week_start_equity > 0.0 and (
        (state.equity - state.week_start_equity) / state.week_start_equity
        <= -cfg.weekly_stop_pct
    ):
        return A_WEEKLY_STOP
    if state.day_counts[day_key] >= cfg.max_new_trades_per_day:
        return A_NEW_TRADES_DAY
    if len(state.open_positions) >= cfg.max_concurrent:
        return A_MAX_SLOTS
    if sum(1 for p in state.open_positions if p.pair == pair) >= cfg.max_per_pair:
        return A_PAIR_SLOTS
    stopped_at = state.last_stop.get((pair, cand.side))
    if stopped_at is not None and cand.entry_at - stopped_at < timedelta(
        hours=cfg.cooldown_hours
    ):
        return A_COOLDOWN
    # Open-risk reservation (A3): O is the flat 1R-per-open-position PROXY
    # (the open positions plus the one being planned) and C is the planned
    # trade's cost_r converted to an equity fraction. Both are fractions of
    # the starting equity, so they are compared with max_open_risk_pct.
    risk = abs(cand.entry_price - cand.stop_price)
    planned_cost_r = round_trip_cost_r(pair, cand.entry_price, risk) if risk > 0.0 else 0.0
    open_risk_proxy = (len(state.open_positions) + 1) * cfg.risk_per_trade
    cost_reserve_fraction = planned_cost_r * cfg.risk_per_trade
    if open_risk_proxy + cost_reserve_fraction > cfg.max_open_risk_pct:
        return A_OPEN_RISK
    return None


def _reject_event(state: ReplayState, pc: PairCandidate, reason: str) -> ReplayEvent:
    return ReplayEvent(
        at=pc.candidate.entry_at,
        kind="reject",
        pair=pc.pair,
        setup_id=pc.candidate.setup_id,
        side=pc.candidate.side,
        reason=reason,
        net_r=0.0,
        equity=state.equity,
    )


def replay_candidates(
    candidates: Sequence[PairCandidate],
    m15_bars: Mapping[str, list[OHLCBar]],
    h1_bars: Mapping[str, list[OHLCBar]],
    *,
    cfg: BacktestConfig,
    gate: PortfolioGate | None = None,
) -> ReplayOutcome:
    """Admit and settle candidates in EVENT TIME against one shared portfolio.

    The equity is derived from SETTLED exits only: a trade's outcome is
    booked when its exit happens, never when it is admitted, so a later
    opportunity can never be funded by a future outcome. A position that is
    still open holds its slot and its stop-risk reservation.

    At an equal timestamp the exits settle before the entries; simultaneous
    entries are ordered by ``(entry_at, decision_at, pair, setup_id)`` and the
    second entry sees the first entry's reservation.

    ``gate`` is an optional extra portfolio check (the joint USD-sign ticket
    cap) evaluated after the built-in gates.
    """
    state = ReplayState(
        equity=cfg.starting_equity,
        starting_equity=cfg.starting_equity,
        day_start_equity=cfg.starting_equity,
        week_start_equity=cfg.starting_equity,
    )
    events: list[ReplayEvent] = []
    rejections: Counter[str] = Counter()
    trades: list[Trade] = []
    seen: set[tuple[str, datetime, str]] = set()

    for pc in order_candidates(candidates):
        cand = pc.candidate
        pair = pc.pair
        m15 = m15_bars.get(pair, [])

        # 1. every exit that already happened settles before this entry
        _settle_due(state, events, now=cand.entry_at, cfg=cfg)

        # 2. one parent per decision and side, PER PAIR: two pairs may each
        #    have a candidate at the same decision time. The key is consumed by
        #    the CANDIDATE, not only by a booked parent: a candidate that is
        #    then rejected for a fill mismatch or a cap still blocks a later
        #    candidate with the same key. That is deliberately conservative --
        #    one decision yields at most one parent attempt.
        key_seen = (pair, cand.decision_at, cand.side)
        if key_seen in seen:
            rejections[A_DUPLICATE] += 1
            events.append(_reject_event(state, pc, A_DUPLICATE))
            continue
        seen.add(key_seen)

        # 3. the day and week anchors move with the SETTLED equity
        day_key = cand.entry_at.date().isoformat()
        iso = cand.entry_at.isocalendar()
        week_key = f"{iso.year}-W{iso.week}"
        if day_key != state.current_day:
            state.current_day = day_key
            state.day_start_equity = state.equity
            state.day_counts.clear()
        if week_key != state.current_week:
            state.current_week = week_key
            state.week_start_equity = state.equity

        # 4. the fill invariant: the planned fill must be a real M15 open
        mismatch = entry_fill_mismatch(cand, m15)
        if mismatch is not None:
            rejections[mismatch] += 1
            events.append(_reject_event(state, pc, mismatch))
            continue
        if entry_fill_bar(m15, cand.entry_at) is None:
            rejections[A_NO_ENTRY_BAR] += 1
            events.append(_reject_event(state, pc, A_NO_ENTRY_BAR))
            continue

        # 5. the portfolio gates, then the optional joint gate
        reason = _admission_reason(state, pc, cfg=cfg)
        if reason is None and gate is not None:
            risk = abs(cand.entry_price - cand.stop_price)
            planned_cost_r = (
                round_trip_cost_r(pair, cand.entry_price, risk) if risk > 0.0 else 0.0
            )
            reason = gate(state, pc, planned_cost_r)
        if reason is not None:
            rejections[reason] += 1
            events.append(_reject_event(state, pc, reason))
            continue

        # 6. simulate the management of the admitted parent
        trade = simulate_trade(cand, pair, m15, h1_bars.get(pair, []), cfg=cfg)
        if trade is None:
            # A degenerate candidate (entry == stop, so no risk to size) is a
            # DIFFERENT failure from "the series has no fill bar". Name it.
            reason = (
                A_INVALID_RISK
                if abs(cand.entry_price - cand.stop_price) <= 0.0
                else A_NO_ENTRY_BAR
            )
            rejections[reason] += 1
            events.append(_reject_event(state, pc, reason))
            continue

        trades.append(trade)
        state.day_counts[day_key] += 1
        state.open_positions.append(
            OpenPosition(
                pair=pair,
                setup_id=cand.setup_id,
                side=cand.side,
                entry_at=trade.entry_at,
                exit_at=trade.exit_at,
                net_r=trade.net_r,
                cost_r=trade.cost_r,
                exit_reason=trade.exit_reason,
                censored=trade.censored,
            )
        )
        events.append(
            ReplayEvent(
                at=trade.entry_at,
                kind="entry",
                pair=pair,
                setup_id=cand.setup_id,
                side=cand.side,
                reason="admitted",
                net_r=trade.net_r,
                equity=state.equity,
            )
        )

    # The sample can end with positions still open: the exits that happened
    # after the last entry are settled now, in time order, so the final
    # equity is complete. Censored positions are never settled.
    remaining = [p for p in state.open_positions if not p.censored]
    _settle(state, events, remaining, cfg=cfg)

    return ReplayOutcome(
        trades=tuple(trades),
        rejections=rejections,
        events=tuple(events),
        equity=state.equity,
        open_positions=tuple(state.open_positions),
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
    """Evaluate every H1 bar, admit candidates, and settle the survivors.

    The signature is unchanged. The replay is event time: the equity only
    moves when a trade SETTLES, so a later candidate can never be funded by a
    future outcome.
    """
    cfg = cfg or BacktestConfig()
    detection = detect_candidates(pair, d1=d1, h4=h4, h1=h1, m15=m15, cfg=cfg)
    outcome = replay_candidates(
        [PairCandidate(pair=pair, candidate=cand) for cand in detection.candidates],
        {pair: m15},
        {pair: h1},
        cfg=cfg,
    )
    rejections: Counter[str] = Counter()
    rejections.update(detection.rejections)
    rejections.update(outcome.rejections)
    setup_counts: Counter[str] = Counter()
    for trade in outcome.trades:
        setup_counts[trade.setup_id] += 1

    return BacktestResult(
        pair=pair,
        # Detection needs M15 retests, so the tradeable sample starts when the
        # M15 series starts, not when the (longer) H1 series starts.
        start=m15[0].timestamp if m15 else (h1[0].timestamp if h1 else datetime.min),
        end=h1[-1].timestamp if h1 else datetime.min,
        trades=list(outcome.trades),
        rejections=rejections,
        setup_counts=setup_counts,
        opportunities=detection.opportunities,
        config=cfg,
        candidates_emitted=len(detection.candidates),
        emitted_setup_counts=detection.emitted_by_setup,
    )
