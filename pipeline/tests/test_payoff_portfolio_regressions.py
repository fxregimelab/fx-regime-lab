"""PD-00C1 regression oracles: event-time engine and joint portfolio replay.

The payoff-desk study may only reuse this simulator's portfolio numbers after
the event-time properties hold. These are the PD-00C oracles from
``docs/specs/payoff-desk/05-delivery.md`` (decisions A1-A10) and the hand
oracles of ``docs/specs/payoff-desk/04-payoff-study.md`` that apply to the
engine and the joint driver:

- a pending exit moves neither the equity nor the cooldown clock;
- no future outcome funds an earlier opportunity;
- the event order is chronological and stable, and at an equal timestamp the
  exits settle before the entries;
- overlapping pair entries share the global slots, the correlated USD load
  and the loss capacity;
- a censored position contributes nothing and keeps its slot and reservation;
- the same timeline always reproduces the same fingerprint;
- the planned fill must be a real M15 open (``A_ENTRY_FILL_MISMATCH``);
- the settled-only aggregates never hide the censored tail;
- the loss-capacity breach latches entries and never liquidates a position;
- the engine's R stays in PRICE-R (never the all-in parent-R of the mandate).

The fixtures are hand-computed bars. No broker, no model, no database, no
network: nothing here can reach a live account or a production ledger.
"""

from __future__ import annotations

import inspect
from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest

from src.paper.backtest.engine import (
    A_COOLDOWN,
    A_DAILY_STOP,
    A_DUPLICATE,
    A_ENTRY_FILL_MISMATCH,
    A_MAX_SLOTS,
    A_NO_ENTRY_BAR,
    A_OPEN_RISK,
    A_PAIR_SLOTS,
    A_USD_SIGN_CAP,
    X_STOP,
    BacktestConfig,
    BacktestResult,
    PairCandidate,
    ReplayEvent,
    Trade,
    detect_candidates,
    entry_fill_mismatch,
    run_backtest,
)
from src.paper.backtest.portfolio import (
    JointConfig,
    JointResult,
    PairBars,
    replay_joint,
    run_joint_backtest,
    usd_sign,
)
from src.paper.features import OHLCBar
from src.paper.strategies import SetupCandidate, _next_m15_open

MONDAY = datetime(2026, 10, 19, 0, tzinfo=UTC)
BAR = timedelta(minutes=15)
T0 = MONDAY + timedelta(hours=8)  # first fill bar opens here


# --- Fixtures -------------------------------------------------------------------


def bar(open_at: datetime, o: float, h: float, low: float, c: float) -> OHLCBar:
    """A completed M15 bar. The engine reads ``timestamp`` as the CLOSE time."""
    return OHLCBar(open_at + BAR, o, h, low, c, 100.0)


def flat_bars(count: int, *, start: datetime = T0, price: float = 100.0) -> list[OHLCBar]:
    """``count`` flat M15 bars opening every 15 minutes from ``start``."""
    return [bar(start + i * BAR, price, price, price, price) for i in range(count)]


def candidate(
    *,
    pair: str = "EURUSD",
    entry_at: datetime = T0,
    side: str = "long",
    entry: float = 100.0,
    stop: float | None = None,
    setup_id: str = "SU1-v1",
    decision_at: datetime | None = None,
) -> SetupCandidate:
    """One candidate whose planned fill is the open of the bar at ``entry_at``.

    The default stop is side-aware: 1.0 price unit against the trade direction.
    A long never inherits a short's stop (and vice versa), which once let a
    short settle instantly and silently void a cap oracle.
    """
    if stop is None:
        stop = entry - 1.0 if side == "long" else entry + 1.0
    risk = abs(entry - stop)
    target = entry + risk if side == "long" else entry - risk
    return SetupCandidate(
        setup_id=setup_id,
        side=side,
        trigger_at=entry_at - timedelta(hours=1),
        decision_at=decision_at if decision_at is not None else entry_at - BAR,
        entry_at=entry_at,
        entry_price=entry,
        stop_price=stop,
        target_a_price=target,
        atr_h1=1.0,
        expires_at=entry_at + timedelta(hours=1),
        trigger_ids=(),
    )


def cfg(**overrides: object) -> BacktestConfig:
    """A zero break-even buffer and a long enough horizon unless overridden."""
    base = BacktestConfig(breakeven_buffer_pips=0.0)
    return BacktestConfig(**{**vars(base), **overrides})


def joint(
    candidates: list[SetupCandidate],
    bars: dict[str, list[OHLCBar]],
    *,
    settings: BacktestConfig | None = None,
    joint_cfg: JointConfig | None = None,
    pair_of: dict[int, str] | None = None,
) -> JointResult:
    """Replay hand-built candidates against one shared portfolio."""
    pairs = pair_of or {}
    wrapped = [
        PairCandidate(pair=pairs.get(index, "EURUSD"), candidate=cand)
        for index, cand in enumerate(candidates)
    ]
    return replay_joint(
        wrapped,
        bars,
        {pair: [] for pair in bars},
        cfg=settings or cfg(),
        joint=joint_cfg,
    )


def events_of(result: JointResult, kind: str | None = None) -> list[ReplayEvent]:
    """The chronological events, optionally filtered by kind."""
    if kind is None:
        return list(result.events)
    return [event for event in result.events if event.kind == kind]


# --- 1. Event-time settlement ----------------------------------------------------


def test_a_pending_exit_moves_neither_the_equity_nor_the_cooldown_clock() -> None:
    """A trade that has not exited yet cannot have funded or blocked anything."""
    # bar0 opens T0 (A fills), bar1 opens T0+15m (C fills),
    # bar2 opens T0+30m, bar3 opens T0+45m and gaps down through the stop.
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 2 * BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 3 * BAR, 98.0, 98.20, 97.50, 97.60),
            bar(T0 + 4 * BAR, 100.0, 100.05, 99.95, 100.0),
        ]
    }
    first = candidate(entry_at=T0)
    earlier = candidate(entry_at=T0 + BAR)
    later = candidate(entry_at=T0 + 4 * BAR)

    result = joint(
        [first, earlier, later],
        bars,
        settings=cfg(daily_stop_pct=0.01, cooldown_hours=4),
    )

    # the second entry happens BEFORE the first trade exits: the equity it
    # sees is the untouched starting equity, so the loss capacity is intact.
    entries = events_of(result, "entry")
    assert [event.pair for event in entries] == ["EURUSD", "EURUSD"]
    assert all(event.equity == pytest.approx(10_000.0) for event in entries)

    # the first trade exits later, and only then does the equity move
    exits = events_of(result, "exit")
    assert exits and exits[0].at == T0 + 4 * BAR  # the close of the gap bar
    assert exits[0].equity < 10_000.0

    # the entry after the exit sees the settled loss and the daily latch
    rejections = events_of(result, "reject")
    assert [event.reason for event in rejections] == [A_DAILY_STOP]
    assert rejections[0].at == T0 + 4 * BAR


def test_a_future_outcome_never_funds_an_earlier_opportunity() -> None:
    """The equity at an entry is the equity settled SO FAR, never the final one."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 2 * BAR, 100.0, 100.05, 98.00, 98.50),
        ]
    }
    winner = candidate(entry_at=T0, stop=99.0)
    # a second candidate inside the winner's life, entered before the exit
    later = candidate(entry_at=T0 + BAR, decision_at=T0 + BAR - timedelta(minutes=5))

    result = joint([winner, later], bars, settings=cfg())

    entries = events_of(result, "entry")
    assert len(entries) == 2
    # the first entry is booked before the exit: the equity is still the start
    assert entries[0].equity == pytest.approx(10_000.0)
    # the second entry happens while the first trade is still open
    assert entries[1].equity == pytest.approx(10_000.0)
    # the loss is only booked at the exit
    exits = events_of(result, "exit")
    assert exits and exits[0].at == T0 + 3 * BAR
    assert exits[0].equity < 10_000.0


def test_an_exit_settles_before_an_entry_at_the_same_timestamp() -> None:
    """A4: at an equal timestamp the exits settle first, so the entry sees them."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 2 * BAR, 100.0, 100.05, 98.00, 98.50),  # the stop is hit
            bar(T0 + 3 * BAR, 100.0, 100.05, 99.95, 100.0),  # the same-moment fill
        ]
    }
    first = candidate(entry_at=T0)
    same_moment = candidate(entry_at=T0 + 3 * BAR)  # opens exactly at the exit

    result = joint([first, same_moment], bars, settings=cfg(daily_stop_pct=0.01))

    kinds = [(event.kind, event.at) for event in result.events]
    # the exit of the first trade (the close of the bar opening at T0+2*BAR)
    # happens at T0+3*BAR, the very moment the second entry is considered
    assert kinds.index(("exit", T0 + 3 * BAR)) < kinds.index(("reject", T0 + 3 * BAR))
    # the settled loss latches the day, so the same-moment entry is refused
    assert [event.reason for event in events_of(result, "reject")] == [A_DAILY_STOP]


def test_a_stop_only_starts_the_cooldown_once_the_trade_has_exited() -> None:
    """The cooldown clock starts at the EXIT, never at the entry."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 2 * BAR, 100.0, 100.05, 98.00, 98.50),
            bar(T0 + 3 * BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 4 * BAR, 100.0, 100.05, 99.95, 100.0),
        ]
    }
    stopped = candidate(entry_at=T0)
    before_exit = candidate(entry_at=T0 + BAR, decision_at=T0 + BAR - timedelta(minutes=5))
    after_exit = candidate(entry_at=T0 + 4 * BAR, decision_at=T0 + 4 * BAR - timedelta(minutes=5))

    result = joint(
        [stopped, before_exit, after_exit],
        bars,
        settings=cfg(cooldown_hours=4, daily_stop_pct=0.5),
    )

    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_COOLDOWN]
    # the entry before the exit was admitted: no cooldown existed yet
    assert len(events_of(result, "entry")) == 2
    stops = [event for event in events_of(result, "exit") if event.reason == X_STOP]
    assert stops and stops[0].at == T0 + 3 * BAR


def test_the_equity_uses_the_immutable_r_and_never_compounds() -> None:
    """The booked R is frozen: the cash impact is R x risk x STARTING equity."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 2 * BAR, 100.0, 100.05, 98.00, 98.50),
        ]
    }
    result = joint([candidate(entry_at=T0)], bars, settings=cfg())

    trade = result.trades[0]
    exit_event = events_of(result, "exit")[0]
    assert exit_event.net_r == pytest.approx(trade.net_r)
    assert exit_event.equity == pytest.approx(
        10_000.0 + trade.net_r * 0.01 * 10_000.0
    )


# --- 2. Censored positions -------------------------------------------------------


def test_a_censored_position_contributes_nothing_and_keeps_its_slot() -> None:
    """The input ended before the horizon: unknown outcome, no cash, no release."""
    bars = {"EURUSD": flat_bars(2)}  # the sample ends long before the horizon
    result = joint([candidate(entry_at=T0)], bars, settings=cfg(horizon_days=1))

    assert len(result.trades) == 1
    assert result.trades[0].censored is True
    assert result.trades[0].settled is False
    assert result.equity == pytest.approx(10_000.0)
    assert result.net_r == pytest.approx(0.0)
    assert result.unresolved_r == pytest.approx(result.trades[0].net_r)
    assert result.censored_count == 1
    assert result.settled_count == 0
    # a censored position is never settled, so it books no exit event
    assert events_of(result, "exit") == []


def test_a_censored_position_keeps_its_slot_until_the_sample_ends() -> None:
    """The slot is not released: the next entry of the same pair is refused."""
    bars = {"EURUSD": flat_bars(2)}
    result = joint(
        [candidate(entry_at=T0), candidate(entry_at=T0 + BAR, decision_at=T0)],
        bars,
        settings=cfg(horizon_days=1, max_concurrent=1),
    )
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_MAX_SLOTS]
    assert len(result.trades) == 1


def test_a_censored_position_keeps_its_stop_risk_reservation() -> None:
    """The unknown position still reserves its risk: the open-risk cap holds."""
    bars = {"EURUSD": flat_bars(2)}
    # one flat 1R position plus its cost reserve is 1.015% of the equity
    result = joint(
        [candidate(entry_at=T0), candidate(entry_at=T0 + BAR, decision_at=T0)],
        bars,
        settings=cfg(
            horizon_days=1,
            max_concurrent=4,
            max_open_risk_pct=0.015,
        ),
    )
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_OPEN_RISK]


# --- 3. Shared caps across pairs -------------------------------------------------


def test_overlapping_pair_entries_share_the_global_slot_cap() -> None:
    """One slot cap for the whole portfolio, not one per pair."""
    bars = {
        "EURUSD": flat_bars(4),
        "USDJPY": flat_bars(4),
    }
    result = joint(
        [
            candidate(entry_at=T0),
            candidate(entry_at=T0 + BAR, side="long", entry=100.0, stop=99.0),
        ],
        bars,
        settings=cfg(max_concurrent=1, horizon_days=1),
        pair_of={0: "EURUSD", 1: "USDJPY"},
    )
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_MAX_SLOTS]
    assert len(result.trades) == 1
    assert result.trades[0].pair == "EURUSD"


def test_the_usd_sign_cap_counts_tickets_across_pairs() -> None:
    """A6: the correlated USD load is a TICKET COUNT over the open positions."""
    bars = {
        "EURUSD": flat_bars(4),
        "USDJPY": flat_bars(4),
    }
    # EURUSD long is SHORT USD; USDJPY short is SHORT USD: the same sign.
    result = joint(
        [
            candidate(entry_at=T0),                                   # EURUSD long
            candidate(entry_at=T0 + BAR, side="short"),               # USDJPY short
            candidate(entry_at=T0 + 2 * BAR, decision_at=T0 + BAR),   # EURUSD long again
        ],
        bars,
        settings=cfg(max_concurrent=4, horizon_days=1),
        pair_of={0: "EURUSD", 1: "USDJPY", 2: "EURUSD"},
    )
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_USD_SIGN_CAP]
    assert len(result.trades) == 2


def test_opposite_usd_signs_do_not_share_the_usd_ticket_cap() -> None:
    """EURUSD long (short USD) and USDJPY long (long USD) are not correlated."""
    bars = {
        "EURUSD": flat_bars(4),
        "USDJPY": flat_bars(4),
    }
    result = joint(
        [
            candidate(entry_at=T0),
            candidate(entry_at=T0 + BAR),
        ],
        bars,
        settings=cfg(max_concurrent=4, horizon_days=1),
        pair_of={0: "EURUSD", 1: "USDJPY"},
    )
    assert events_of(result, "reject") == []
    assert len(result.trades) == 2


def test_the_loss_capacity_is_shared_across_pairs() -> None:
    """A settled loss on one pair latches the entries of the other pair."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 2 * BAR, 100.0, 100.05, 98.00, 98.50),
            bar(T0 + 3 * BAR, 100.0, 100.05, 99.95, 100.0),
        ],
        "USDJPY": flat_bars(4),
    }
    result = joint(
        [
            candidate(entry_at=T0),
            candidate(entry_at=T0 + 3 * BAR, decision_at=T0 + 2 * BAR),
        ],
        bars,
        settings=cfg(daily_stop_pct=0.01),
        pair_of={0: "EURUSD", 1: "USDJPY"},
    )
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_DAILY_STOP]
    assert result.trades[0].pair == "EURUSD"


def test_a_loss_capacity_breach_latches_entries_and_never_liquidates() -> None:
    """A2: the breach blocks NEW entries; the open position runs to its own exit."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 2 * BAR, 100.0, 100.05, 98.00, 98.50),
            bar(T0 + 3 * BAR, 100.0, 100.05, 99.95, 100.0),
        ]
    }
    result = joint([candidate(entry_at=T0)], bars, settings=cfg(daily_stop_pct=0.01))
    exits = events_of(result, "exit")
    assert len(exits) == 1
    # the only exit is the trade's own exit: no forced liquidation was added
    assert exits[0].reason == X_STOP
    assert exits[0].at == T0 + 3 * BAR


def test_the_per_pair_slot_cap_still_applies_inside_a_shared_portfolio() -> None:
    """Two positions of one pair are allowed; a third is not."""
    bars = {"EURUSD": flat_bars(6)}
    result = joint(
        [
            candidate(entry_at=T0),
            candidate(entry_at=T0 + BAR, decision_at=T0),
            candidate(entry_at=T0 + 2 * BAR, decision_at=T0 + BAR),
        ],
        bars,
        settings=cfg(max_concurrent=4, max_per_pair=2, horizon_days=1),
    )
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_PAIR_SLOTS]
    assert len(result.trades) == 2


# --- 4. Ordering and tie-breaks --------------------------------------------------


def test_simultaneous_entries_are_ordered_and_the_second_sees_the_reservation() -> None:
    """A4: the order is (entry_at, decision_at, pair, setup_id) and it is recorded."""
    bars = {
        "EURUSD": flat_bars(4),
        "USDJPY": flat_bars(4),
    }
    result = joint(
        [
            candidate(entry_at=T0),
            candidate(entry_at=T0),
        ],
        bars,
        settings=cfg(max_concurrent=1, horizon_days=1),
        pair_of={0: "EURUSD", 1: "USDJPY"},
    )
    # EURUSD sorts before USDJPY, so EURUSD takes the only slot
    assert result.trades[0].pair == "EURUSD"
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_MAX_SLOTS]
    assert len(result.tie_breaks) == 1
    assert result.tie_breaks[0].at == T0
    assert result.tie_breaks[0].ordered == (
        ("EURUSD", "SU1-v1", "long"),
        ("USDJPY", "SU1-v1", "long"),
    )


def test_the_event_stream_is_chronological_and_stable() -> None:
    """The event order is reproducible and never goes back in time."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 2 * BAR, 100.0, 100.05, 98.00, 98.50),
        ],
        "USDJPY": flat_bars(3),
    }
    result = joint(
        [
            candidate(entry_at=T0),
            candidate(entry_at=T0 + BAR, decision_at=T0),
        ],
        bars,
        settings=cfg(),
        pair_of={0: "EURUSD", 1: "USDJPY"},
    )
    stamps = [event.at for event in result.events]
    assert stamps == sorted(stamps)
    # the same timeline reproduces the same stream
    again = joint(
        [
            candidate(entry_at=T0),
            candidate(entry_at=T0 + BAR, decision_at=T0),
        ],
        bars,
        settings=cfg(),
        pair_of={0: "EURUSD", 1: "USDJPY"},
    )
    assert [(e.at, e.kind, e.pair, e.reason) for e in again.events] == [
        (e.at, e.kind, e.pair, e.reason) for e in result.events
    ]


def test_an_identical_timeline_reproduces_the_same_fingerprint() -> None:
    """The fingerprint is a hash of the event stream: the same input, the same hash."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + 2 * BAR, 100.0, 100.05, 98.00, 98.50),
        ],
        "USDJPY": flat_bars(3),
    }
    cands = [candidate(entry_at=T0), candidate(entry_at=T0 + BAR, decision_at=T0)]
    pair_of = {0: "EURUSD", 1: "USDJPY"}
    first = joint(cands, bars, settings=cfg(), pair_of=pair_of)
    second = joint(cands, bars, settings=cfg(), pair_of=pair_of)
    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64
    # a different timeline produces a different fingerprint
    other = joint(
        [candidate(entry_at=T0 + 2 * BAR, decision_at=T0 + BAR)],
        bars,
        settings=cfg(),
        pair_of=pair_of,
    )
    assert other.fingerprint != first.fingerprint


def test_the_usd_sign_helper_matches_the_pair_convention() -> None:
    """EURUSD long is short USD; USDJPY long is long USD; a short flips it."""
    assert usd_sign("EURUSD", "long") == -1
    assert usd_sign("EURUSD", "short") == 1
    assert usd_sign("USDJPY", "long") == 1
    assert usd_sign("USDJPY", "short") == -1
    with pytest.raises(ValueError):
        usd_sign("EURUSD", "sideways")


# --- 5. The fill invariant --------------------------------------------------------


def test_a_candidate_whose_price_is_not_a_real_open_is_never_booked() -> None:
    """A5: the fill must be the open of the next M15 bar; else fail closed."""
    bars = {"EURUSD": flat_bars(4)}
    fabricated = candidate(entry_at=T0, entry=100.5, stop=99.5)
    result = joint([fabricated], bars, settings=cfg())

    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_ENTRY_FILL_MISMATCH]
    assert result.trades == ()
    assert result.equity == pytest.approx(10_000.0)


def test_a_candidate_whose_entry_time_is_not_a_bar_open_is_never_booked() -> None:
    """The planned fill time must be a real M15 open as well."""
    bars = {"EURUSD": flat_bars(4)}
    off_schedule = candidate(entry_at=T0 + timedelta(minutes=7))
    result = joint([off_schedule], bars, settings=cfg())
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_ENTRY_FILL_MISMATCH]
    assert result.trades == ()


def test_the_detector_fill_rule_satisfies_the_engine_fill_gate() -> None:
    """A5 ACCEPTANCE PATH: the rule the detectors use to plan a fill is the rule
    the engine accepts.

    The fail-closed gate is only safe while the detector and the engine share
    one fill rule. If a future detector planned a limit-style entry instead of
    the next M15 open, every backtest would silently degrade to zero trades
    behind A_ENTRY_FILL_MISMATCH rejections. This test pins the coupling
    directly: whatever ``_next_m15_open`` plans must pass ``entry_fill_mismatch``.
    """
    bars = [
        bar(T0 + i * BAR, 100.0 + i * 0.25, 100.6 + i * 0.25, 99.4 + i * 0.25, 100.0 + i * 0.25)
        for i in range(12)
    ]
    checked = 0
    for index in range(len(bars)):
        after = bars[index].timestamp - timedelta(minutes=1)
        planned = _next_m15_open(bars, after)
        assert planned is not None
        planned_at, planned_price = planned
        # Exactly how SU1/SU2/SU3 build a candidate's planned fill.
        cand = candidate(
            entry_at=planned_at,
            entry=planned_price,
            stop=planned_price - 1.0,
            decision_at=planned_at - BAR,
        )
        assert entry_fill_mismatch(cand, bars) is None
        checked += 1
    assert checked == len(bars)


def test_a_detector_emitted_candidate_is_never_rejected_for_a_fill_mismatch() -> None:
    """A5 ACCEPTANCE PATH, end to end: the real detectors cannot produce a
    candidate the engine's own fill gate would reject.

    Asserted over whatever the detectors actually emit, so it stays meaningful
    even when a fixture emits none: the invariant under test is a property of
    the detector code, not of the fixture.
    """
    d1, h4, h1, m15 = synthetic_bars()
    detection = detect_candidates(
        "EURUSD", d1=d1, h4=h4, h1=h1, m15=m15, cfg=cfg()
    )
    for cand in detection.candidates:
        assert entry_fill_mismatch(cand, m15) is None, cand.setup_id


def test_a_candidate_without_any_fill_bar_is_reported_not_booked() -> None:
    """No M15 bar at or after the entry: an explicit reason, never a booking."""
    bars = {"EURUSD": [bar(T0, 100.0, 100.05, 99.95, 100.0)]}
    result = joint(
        [candidate(entry_at=T0 + 5 * BAR)],
        bars,
        settings=cfg(),
    )
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_NO_ENTRY_BAR]
    assert result.trades == ()


def test_a_duplicate_candidate_is_never_booked_twice() -> None:
    """Oracle 9: a duplicate receipt leaves the settled parent unchanged."""
    bars = {"EURUSD": flat_bars(4)}
    first = candidate(entry_at=T0)
    duplicate = candidate(entry_at=T0)
    result = joint([first, duplicate], bars, settings=cfg())
    reasons = [event.reason for event in events_of(result, "reject")]
    assert reasons == [A_DUPLICATE]
    assert len(result.trades) == 1


# --- 6. Settled-only aggregates (A1) ---------------------------------------------


def make_trade(*, net_r: float, gross: float = 0.0, cost: float = 0.0, censored: bool) -> Trade:
    return Trade(
        pair="EURUSD",
        setup_id="SU1-v1",
        side="long",
        entry_at=T0,
        exit_at=T0 + BAR,
        entry_price=100.0,
        stop_price=99.0,
        exit_price=100.0,
        atr_h1=1.0,
        risk_price=1.0,
        exit_reason="censored_data_end" if censored else X_STOP,
        r_multiple=gross,
        cost_r=cost,
        net_r=net_r,
        mae_r=0.0,
        mfe_r=0.0,
        bars_held=1,
        partial_taken=False,
        censored=censored,
    )


def test_the_aggregates_are_settled_only_and_the_tail_stays_visible() -> None:
    """A1: the default aggregates exclude the censored tail; the _all do not."""
    win = make_trade(net_r=1.0, gross=1.1, cost=0.1, censored=False)
    loss = make_trade(net_r=-2.0, gross=-2.1, cost=0.1, censored=False)
    unknown = make_trade(net_r=3.0, gross=3.1, cost=0.1, censored=True)

    result = BacktestResult(
        pair="EURUSD",
        start=T0,
        end=T0 + BAR,
        trades=[win, loss, unknown],
        rejections=Counter(),
        setup_counts=Counter({"SU1-v1": 3}),
        opportunities=3,
        config=BacktestConfig(),
        candidates_emitted=4,
    )

    assert result.trade_count == 3
    assert result.settled_count == 2
    assert result.censored_count == 1
    assert result.net_r == pytest.approx(-1.0)          # 1.0 + (-2.0)
    assert result.gross_r == pytest.approx(-1.0)        # 1.1 + (-2.1)
    assert result.costs_r == pytest.approx(0.2)
    assert result.expectancy_r == pytest.approx(-0.5)   # per SETTLED trade
    assert result.net_r_all == pytest.approx(2.0)
    assert result.gross_r_all == pytest.approx(2.1)
    assert result.costs_r_all == pytest.approx(0.3)
    assert result.expectancy_r_all == pytest.approx(2.0 / 3.0)
    assert result.unresolved_r == pytest.approx(3.0)
    assert result.net_r_all == pytest.approx(result.net_r + result.unresolved_r)


def test_a_censored_trade_is_never_a_win() -> None:
    """A1: the win flag is settled-only; a censored trade is not a win."""
    unknown = make_trade(net_r=3.0, gross=3.1, cost=0.1, censored=True)
    settled = make_trade(net_r=1.0, gross=1.1, cost=0.1, censored=False)
    assert unknown.settled is False
    assert unknown.win is False
    assert settled.settled is True
    assert settled.win is True
    losing = make_trade(net_r=-1.0, gross=-0.9, cost=0.1, censored=False)
    assert losing.win is False


def test_the_joint_result_keeps_the_funnel_counts_apart() -> None:
    """A9: emitted, admitted and settled are three different numbers."""
    bars = {"EURUSD": flat_bars(2)}
    result = joint([candidate(entry_at=T0)], bars, settings=cfg(horizon_days=1))
    assert result.admitted_count == 1
    assert result.settled_count == 0
    assert result.censored_count == 1
    assert result.emitted_count == 0  # nothing was detected in this fixture


# --- 7. Price-R oracles (the engine stays in price-R) -----------------------------


def test_the_original_stop_before_one_r_is_minus_one_price_r() -> None:
    """Oracle 1: the protective stop books -1R on the ORIGINAL risk distance."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 100.05, 98.50, 98.60),
        ]
    }
    result = joint([candidate(entry_at=T0)], bars, settings=cfg())
    trade = result.trades[0]
    assert trade.exit_reason == X_STOP
    assert trade.r_multiple == pytest.approx(-1.0, abs=1e-9)
    assert trade.risk_price == pytest.approx(1.0)


def test_a_gap_through_the_stop_is_not_clamped_to_the_nominal_risk() -> None:
    """Oracle 8: a gap of -2R books -2R; the loss is never clamped back to -1R."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 98.0, 98.20, 97.50, 97.60),
        ]
    }
    result = joint([candidate(entry_at=T0)], bars, settings=cfg())
    trade = result.trades[0]
    assert trade.exit_price == pytest.approx(98.0)
    assert trade.r_multiple == pytest.approx(-2.0, abs=1e-9)


def test_half_at_one_r_then_the_runner_at_the_original_stop_is_zero_gross() -> None:
    """Oracle 2: 0.5 * (+1R) + 0.5 * (-1R) = 0R gross on the original 1R."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 101.20, 100.00, 101.00),
            bar(T0 + 2 * BAR, 99.0, 99.10, 98.50, 98.60),
        ]
    }
    result = joint([candidate(entry_at=T0)], bars, settings=cfg())
    trade = result.trades[0]
    assert trade.partial_taken is True
    assert trade.r_multiple == pytest.approx(0.0, abs=1e-9)
    assert trade.risk_price == pytest.approx(1.0)


def test_the_cost_is_charged_once_per_parent_not_once_per_leg() -> None:
    """Oracle 6/12: the round-trip cost is charged once, on the original risk."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 101.20, 100.00, 101.00),
            bar(T0 + 2 * BAR, 99.0, 99.10, 98.50, 98.60),
        ]
    }
    result = joint([candidate(entry_at=T0)], bars, settings=cfg())
    trade = result.trades[0]
    # EURUSD: 1.0 bps round trip + 0.5 bps slippage on 100.0 with a 1.0 risk
    assert trade.cost_r == pytest.approx(0.015, abs=1e-12)
    assert trade.net_r == pytest.approx(trade.r_multiple - trade.cost_r)
    # the partial did not add a second cost
    assert trade.partial_taken is True


def test_the_engine_r_is_price_r_and_not_the_all_in_parent_r() -> None:
    """The engine stays in price-R: 1.0 price-R is never divided by (1 + k)."""
    bars = {
        "EURUSD": [
            bar(T0, 100.0, 100.05, 99.95, 100.0),
            bar(T0 + BAR, 100.0, 101.20, 100.00, 101.00),
            bar(T0 + 2 * BAR, 101.0, 101.10, 100.90, 101.00),
        ]
    }
    result = joint([candidate(entry_at=T0)], bars, settings=cfg())
    trade = result.trades[0]
    assert trade.partial_taken is True
    # half closed at +1R, the runner marked at +1R => +1R gross in PRICE-R
    assert trade.r_multiple == pytest.approx(1.0, abs=1e-9)


# --- 8. The detect_candidates split -----------------------------------------------


def synthetic_bars() -> tuple[list[OHLCBar], list[OHLCBar], list[OHLCBar], list[OHLCBar]]:
    """Long enough series for the detectors to run (d1, h4, h1, m15)."""
    d1 = [
        bar(MONDAY + timedelta(days=k), 100.0, 100.5, 99.5, 100.0) for k in range(40)
    ]
    h4 = [
        bar(MONDAY + timedelta(hours=4 * k), 100.0, 100.5, 99.5, 100.0) for k in range(30)
    ]
    h1 = [bar(MONDAY + timedelta(hours=k), 100.0, 100.5, 99.5, 100.0) for k in range(80)]
    m15 = [
        bar(MONDAY + 15 * k * timedelta(minutes=1), 100.0, 100.5, 99.5, 100.0)
        for k in range(400)
    ]
    return d1, h4, h1, m15


def test_detect_candidates_is_the_detection_half_of_run_backtest() -> None:
    """The split is real: the same detection feeds the single-pair replay."""
    d1, h4, h1, m15 = synthetic_bars()
    detection = detect_candidates("EURUSD", d1=d1, h4=h4, h1=h1, m15=m15, cfg=cfg())
    result = run_backtest("EURUSD", d1=d1, h4=h4, h1=h1, m15=m15, cfg=cfg())

    assert result.opportunities == detection.opportunities
    assert result.candidates_emitted == len(detection.candidates)
    assert result.trade_count <= result.candidates_emitted
    for key, count in detection.rejections.items():
        assert result.rejections[key] == count


def test_run_backtest_keeps_its_signature() -> None:
    """The public entry point of the single-pair replay is unchanged."""
    signature = inspect.signature(run_backtest)
    assert list(signature.parameters) == ["pair", "d1", "h4", "h1", "m15", "cfg"]
    for name in ("d1", "h4", "h1", "m15"):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY


def test_run_backtest_settles_in_event_time() -> None:
    """The single-pair replay books the equity at the exit, not at the entry."""
    d1, h4, h1, m15 = synthetic_bars()
    result = run_backtest("EURUSD", d1=d1, h4=h4, h1=h1, m15=m15, cfg=cfg())
    for trade in result.trades:
        assert trade.settled == (not trade.censored)
    assert result.net_r == pytest.approx(
        sum(t.net_r for t in result.trades if t.settled)
    )


# --- 9. The joint driver over detected candidates --------------------------------


def test_the_joint_driver_runs_both_pairs_against_one_portfolio() -> None:
    """run_joint_backtest detects per pair and admits against ONE portfolio."""
    d1, h4, h1, m15 = synthetic_bars()
    series = [
        PairBars(pair="EURUSD", d1=d1, h4=h4, h1=h1, m15=m15),
        PairBars(pair="USDJPY", d1=d1, h4=h4, h1=h1, m15=m15),
    ]
    result = run_joint_backtest(series, cfg=cfg())
    assert set(result.detections) == {"EURUSD", "USDJPY"}
    assert result.emitted_count == sum(
        len(detection.candidates) for detection in result.detections.values()
    )
    assert result.admitted_count == len(result.trades)
    assert len(result.fingerprint) == 64
    stamps = [event.at for event in result.events]
    assert stamps == sorted(stamps)
    for pair, trades in result.per_pair.items():
        assert all(trade.pair == pair for trade in trades)


def test_the_joint_usd_cap_is_configurable_and_ticket_based() -> None:
    """A6: the cap counts tickets; a notional variant does not live here."""
    bars = {
        "EURUSD": flat_bars(4),
        "USDJPY": flat_bars(4),
    }
    cands = [
        candidate(entry_at=T0),
        candidate(entry_at=T0 + BAR, side="short"),
        candidate(entry_at=T0 + 2 * BAR, decision_at=T0 + BAR),
    ]
    pair_of = {0: "EURUSD", 1: "USDJPY", 2: "EURUSD"}
    strict = joint(
        cands, bars, settings=cfg(max_concurrent=4, horizon_days=1),
        joint_cfg=JointConfig(max_same_usd_sign_tickets=2), pair_of=pair_of,
    )
    assert [event.reason for event in events_of(strict, "reject")] == [A_USD_SIGN_CAP]

    relaxed = joint(
        cands, bars, settings=cfg(max_concurrent=4, horizon_days=1),
        joint_cfg=JointConfig(max_same_usd_sign_tickets=3), pair_of=pair_of,
    )
    assert events_of(relaxed, "reject") == []
    assert len(relaxed.trades) == 3
