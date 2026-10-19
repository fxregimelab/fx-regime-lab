"""PD-00B regression oracles for the offline backtest engine (research only).

The payoff-desk study may only reuse this simulator's numbers after the
structural execution-price and horizon properties hold. These are the hand
oracles from ``docs/specs/payoff-desk/04-payoff-study.md`` and the PD-00B
packet in ``docs/specs/payoff-desk/05-delivery.md``:

- a gap through the protective stop fills at the ADVERSE OPEN, both sides;
- a one-day research horizon cannot settle at a bar far past the horizon;
- appending post-horizon bars cannot change the settlement;
- partial fractions and the ORIGINAL risk denominator are preserved;
- the censored / final-bar path is explicit, never a silent settlement;
- the research horizon is a calendar-day horizon, not broker-session T+5.

The fixtures are hand-computed bars. No broker, no model, no database, no
network: nothing here can reach a live account or a production ledger.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest

from src.paper.backtest.engine import (
    X_CENSORED,
    X_HORIZON,
    BacktestConfig,
    BacktestResult,
    Trade,
    simulate_trade,
)
from src.paper.features import OHLCBar
from src.paper.strategies import SetupCandidate

MONDAY = datetime(2026, 10, 19, 0, tzinfo=UTC)
BAR = timedelta(minutes=15)
ENTRY = MONDAY + BAR  # the fill bar opens here


def bar(open_at: datetime, o: float, h: float, low: float, c: float) -> OHLCBar:
    """A completed M15 bar. The engine reads ``timestamp`` as the CLOSE time."""
    return OHLCBar(open_at + BAR, o, h, low, c, 100.0)


def flat_bars(
    start: datetime, *, until: datetime, price: float = 100.0
) -> list[OHLCBar]:
    """Flat M15 bars from ``start`` up to and including the bar opening at ``until``."""
    out: list[OHLCBar] = []
    t = start
    while t <= until:
        out.append(bar(t, price, price, price, price))
        t += BAR
    return out


def candidate(
    *, entry_at: datetime = ENTRY, side: str = "long", entry: float = 100.0, stop: float = 99.0
) -> SetupCandidate:
    risk = abs(entry - stop)
    target = entry + risk if side == "long" else entry - risk
    return SetupCandidate(
        setup_id="SU1-v1",
        side=side,
        trigger_at=entry_at - timedelta(hours=1),
        decision_at=entry_at,
        entry_at=entry_at,
        entry_price=entry,
        stop_price=stop,
        target_a_price=target,
        atr_h1=1.0,
        expires_at=entry_at + timedelta(hours=1),
        trigger_ids=(),
    )


def cfg(**overrides: object) -> BacktestConfig:
    """Zero break-even buffer unless a test says otherwise."""
    base = BacktestConfig(breakeven_buffer_pips=0.0)
    return BacktestConfig(**{**vars(base), **overrides})


# --- 1. Adverse gap fills at the adverse open -----------------------------------


def test_long_gap_through_the_stop_fills_at_the_adverse_open() -> None:
    """Entry 100, stop 99: a gap open at 98 must lose 2 price-R, not 1."""
    bars = [
        bar(ENTRY, 100.0, 100.05, 99.95, 100.0),  # the fill bar opens at the plan
        bar(ENTRY + BAR, 98.0, 98.20, 97.50, 97.60),  # gaps down through the stop
    ]
    trade = simulate_trade(candidate(), "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.entry_price == pytest.approx(100.0)
    assert trade.exit_reason == "stop"
    assert trade.exit_price == pytest.approx(98.0)
    assert trade.r_multiple == pytest.approx(-2.0, abs=1e-9)
    # the loss is a price-R loss before costs; costs are reported separately
    assert trade.cost_r > 0.0
    assert trade.net_r == pytest.approx(trade.r_multiple - trade.cost_r)


def test_short_gap_through_the_stop_fills_at_the_adverse_open() -> None:
    """Entry 100, stop 101: a gap open at 102 must lose 2 price-R, not 1."""
    bars = [
        bar(ENTRY, 100.0, 100.05, 99.95, 100.0),
        bar(ENTRY + BAR, 102.0, 102.50, 101.00, 102.00),  # gaps up through the stop
    ]
    cand = candidate(side="short", entry=100.0, stop=101.0)
    trade = simulate_trade(cand, "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.exit_reason == "stop"
    assert trade.exit_price == pytest.approx(102.0)
    assert trade.r_multiple == pytest.approx(-2.0, abs=1e-9)
    assert trade.net_r == pytest.approx(trade.r_multiple - trade.cost_r)


def test_a_stop_touched_without_a_gap_still_fills_at_the_stop_price() -> None:
    """No gap: the stop fills at the stop price, not at the bar open."""
    bars = [
        bar(ENTRY, 100.0, 100.05, 99.95, 100.0),
        bar(ENTRY + BAR, 100.0, 100.05, 98.50, 98.60),  # trades down through the stop
    ]
    trade = simulate_trade(candidate(), "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.exit_reason == "stop"
    assert trade.exit_price == pytest.approx(99.0)
    assert trade.r_multiple == pytest.approx(-1.0, abs=1e-9)


# --- 2. Horizon settlement -------------------------------------------------------


def test_one_day_horizon_never_settles_at_a_bar_far_past_the_horizon() -> None:
    """A one-day research horizon settles at the horizon, never at the 50h bar."""
    horizon = ENTRY + timedelta(days=1)
    bars = flat_bars(ENTRY, until=ENTRY + timedelta(hours=50))
    # everything beyond the horizon carries a unmistakable price
    for index, item in enumerate(bars):
        if item.timestamp - BAR > horizon:
            bars[index] = bar(item.timestamp - BAR, 130.0, 130.0, 130.0, 130.0)
    trade = simulate_trade(
        candidate(), "EURUSD", bars, [], cfg=cfg(horizon_days=1, time_stop_hours=1000)
    )
    assert trade is not None
    assert trade.exit_reason == X_HORIZON
    assert trade.censored is False
    assert trade.exit_price == pytest.approx(100.0)
    assert trade.exit_at >= horizon
    assert trade.exit_at <= horizon + BAR


def test_appending_post_horizon_bars_cannot_change_the_settlement() -> None:
    """Bars after the horizon are invisible to the settlement."""
    horizon = ENTRY + timedelta(days=1)
    base = flat_bars(ENTRY, until=horizon)
    extended = base + flat_bars(horizon + BAR, until=ENTRY + timedelta(hours=50), price=130.0)
    settings = cfg(horizon_days=1, time_stop_hours=1000)
    first = simulate_trade(candidate(), "EURUSD", base, [], cfg=settings)
    second = simulate_trade(candidate(), "EURUSD", extended, [], cfg=settings)
    assert first is not None and second is not None
    assert first.exit_at == second.exit_at
    assert first.exit_price == pytest.approx(second.exit_price)
    assert first.r_multiple == pytest.approx(second.r_multiple)
    assert first.exit_reason == second.exit_reason
    assert first.censored is second.censored


def test_the_horizon_is_calendar_day_and_not_broker_session_t_plus_5() -> None:
    """The research horizon is a calendar-day bound; T+5 sessions are NOT bound here."""
    horizon_days = 1
    horizon = ENTRY + timedelta(days=horizon_days)
    bars = flat_bars(ENTRY, until=horizon)
    trade = simulate_trade(
        candidate(), "EURUSD", bars, [], cfg=cfg(horizon_days=horizon_days, time_stop_hours=1000)
    )
    assert trade is not None
    assert trade.exit_reason == X_HORIZON
    assert trade.horizon_basis == "calendar_day"
    # a calendar-day horizon is not a trading-session count: it is stated, not implied
    assert X_HORIZON != "t_plus_5"
    assert "t_plus_5" not in {X_HORIZON, X_CENSORED}
    assert trade.exit_at <= horizon + BAR


# --- 3. Censored / final-bar path ------------------------------------------------


def test_an_unresolved_final_trade_is_censored_not_settled() -> None:
    """The input ends before the horizon: the outcome is UNKNOWN and explicit."""
    bars = [
        bar(ENTRY, 100.0, 100.02, 99.98, 100.0),
        bar(ENTRY + BAR, 100.0, 100.02, 99.98, 100.0),
    ]
    trade = simulate_trade(candidate(), "EURUSD", bars, [], cfg=cfg(horizon_days=1))
    assert trade is not None
    assert trade.censored is True
    assert trade.exit_reason == X_CENSORED
    assert trade.exit_reason != X_HORIZON


def test_censored_trades_are_neither_settled_wins_nor_settled_losses() -> None:
    """An unresolved trade is reported, not booked as a win or dropped as a loss."""

    def make(*, net_r: float, censored: bool) -> Trade:
        return Trade(
            pair="EURUSD",
            setup_id="SU1-v1",
            side="long",
            entry_at=ENTRY,
            exit_at=ENTRY,
            entry_price=100.0,
            stop_price=99.0,
            exit_price=100.0,
            atr_h1=1.0,
            risk_price=1.0,
            exit_reason=X_CENSORED if censored else "stop",
            r_multiple=net_r,
            cost_r=0.0,
            net_r=net_r,
            mae_r=0.0,
            mfe_r=0.0,
            bars_held=1,
            partial_taken=False,
            censored=censored,
        )

    win = make(net_r=1.0, censored=False)
    loss = make(net_r=-1.0, censored=False)
    unresolved = make(net_r=2.0, censored=True)
    result = BacktestResult(
        pair="EURUSD",
        start=ENTRY,
        end=ENTRY,
        trades=[win, loss, unresolved],
        rejections=Counter(),
        setup_counts=Counter(),
        opportunities=3,
        config=BacktestConfig(),
    )
    assert result.wins == [win]
    assert result.losses == [loss]
    assert result.censored_trades == [unresolved]
    assert result.win_rate == pytest.approx(0.5)


# --- 4. Partial fractions and the original-risk denominator ----------------------


def test_half_at_one_r_then_the_runner_at_the_original_stop_is_zero_gross() -> None:
    """M1 hand oracle: half at +1R, runner back at the ORIGINAL stop => 0R gross."""
    bars = [
        bar(ENTRY, 100.0, 100.05, 99.95, 100.0),  # fill at 100
        bar(ENTRY + BAR, 100.0, 101.20, 100.00, 101.00),  # +1R: the partial fills
        bar(ENTRY + 2 * BAR, 99.0, 99.10, 98.50, 98.60),  # gaps back to the original stop
    ]
    trade = simulate_trade(candidate(), "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.partial_taken is True
    assert trade.exit_price == pytest.approx(99.0)
    # 0.5 * (+1R) + 0.5 * (-1R) on the ORIGINAL 1R denominator = 0R gross
    assert trade.r_multiple == pytest.approx(0.0, abs=1e-9)
    assert trade.risk_price == pytest.approx(1.0)


def test_the_runner_is_scored_on_the_original_risk_never_a_reset_denominator() -> None:
    """Half at +1R, runner marked at +0.5R => 0.75R gross on the original 1R."""
    horizon = ENTRY + timedelta(days=1)
    bars = [
        bar(ENTRY, 100.0, 100.05, 99.95, 100.0),
        bar(ENTRY + BAR, 100.0, 101.20, 100.00, 101.00),  # +1R: the partial fills
    ]
    bars += flat_bars(ENTRY + 2 * BAR, until=horizon, price=100.5)
    trade = simulate_trade(
        candidate(), "EURUSD", bars, [], cfg=cfg(horizon_days=1, time_stop_hours=1000)
    )
    assert trade is not None
    assert trade.partial_taken is True
    assert trade.risk_price == pytest.approx(1.0)
    # 0.5 * (+1R) + 0.5 * (+0.5R) = 0.75R gross, denominator still the original 1R
    assert trade.r_multiple == pytest.approx(0.75, abs=1e-9)
