"""Oracle tests for the offline backtest engine (measurement harness only).

These tests pin the honesty properties that make the reported numbers
believable: entry at the next bar's open, stop-before-target on ambiguous
bars, the 1R partial + break-even move, the 4h time stop, canonical costs,
and the T+5 horizon. They use hand-computed fixtures, not real data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.paper.backtest.engine import (
    BacktestConfig,
    Trade,
    context_at,
    d1_context_series,
    simulate_trade,
)
from src.paper.features import OHLCBar
from src.paper.strategies import SetupCandidate

MONDAY = datetime(2026, 10, 19, 0, tzinfo=UTC)


def bar(minutes: int, o: float, h: float, low: float, c: float) -> OHLCBar:
    return OHLCBar(MONDAY + timedelta(minutes=minutes), o, h, low, c, 100.0)


def candidate(*, entry_at: datetime, entry: float = 100.0, stop: float = 99.0) -> SetupCandidate:
    return SetupCandidate(
        setup_id="SU1-v1",
        side="long",
        trigger_at=entry_at - timedelta(hours=1),
        decision_at=entry_at,
        entry_at=entry_at,
        entry_price=entry,
        stop_price=stop,
        target_a_price=entry + (entry - stop),
        atr_h1=1.0,
        expires_at=entry_at + timedelta(hours=1),
        trigger_ids=(),
    )


def cfg(**overrides: object) -> BacktestConfig:
    base = BacktestConfig(breakeven_buffer_pips=0.0)
    return BacktestConfig(**{**base.__dict__, **overrides}) if overrides else base


def test_entry_is_next_bar_open_not_decision_bar_price() -> None:
    """The decision bar closes at T; the fill must be the T+15m bar's open."""
    entry_at = MONDAY + timedelta(minutes=15)
    bars = [
        bar(0, 99.0, 99.2, 98.8, 99.0),          # before the decision
        bar(15, 100.0, 100.4, 99.9, 100.3),      # the fill bar (open 100.0)
        bar(30, 100.3, 101.5, 100.2, 101.4),
    ]
    trade = simulate_trade(candidate(entry_at=entry_at), "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.entry_at == entry_at
    assert trade.entry_price == pytest.approx(100.0)


def test_stop_wins_when_one_bar_spans_stop_and_target() -> None:
    """Pessimistic ambiguity resolution: a bar touching both books the loss."""
    entry_at = MONDAY + timedelta(minutes=15)
    bars = [
        bar(15, 100.0, 100.05, 99.95, 100.0),
        bar(30, 100.0, 101.5, 98.5, 100.0),  # spans target 101 and stop 99
    ]
    trade = simulate_trade(candidate(entry_at=entry_at), "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.exit_reason == "stop"
    assert trade.r_multiple == pytest.approx(-1.0, abs=1e-9)


def test_partial_at_one_r_then_breakeven_stop() -> None:
    """50% off at +1R, then the runner stops at entry for +0.5R gross."""
    entry_at = MONDAY + timedelta(minutes=15)
    bars = [
        bar(15, 100.0, 100.1, 99.9, 100.0),
        bar(30, 100.0, 101.2, 100.0, 101.0),   # partial fills at 101
        bar(45, 101.0, 101.1, 99.9, 100.0),    # runner stopped at BE
    ]
    trade = simulate_trade(candidate(entry_at=entry_at), "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.partial_taken is True
    assert trade.r_multiple == pytest.approx(0.5, abs=1e-9)
    assert trade.exit_reason in ("partial_then_exit", "trail")


def test_time_stop_closes_stalled_trade_after_four_hours() -> None:
    entry_at = MONDAY + timedelta(minutes=15)
    bars = [bar(15, 100.0, 100.05, 99.95, 100.0)]
    for k in range(1, 18):
        bars.append(bar(15 + 15 * k, 100.0, 100.1, 99.9, 100.02))
    trade = simulate_trade(candidate(entry_at=entry_at), "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.exit_reason == "time_stop"
    assert trade.bars_held == 16  # 4 hours of M15 bars


def test_costs_are_charged_separately_and_reduce_net_r() -> None:
    entry_at = MONDAY + timedelta(minutes=15)
    bars = [
        bar(15, 100.0, 100.05, 99.95, 100.0),
        bar(30, 100.0, 101.2, 100.0, 101.0),
        bar(45, 101.0, 101.1, 99.9, 100.0),
    ]
    trade = simulate_trade(candidate(entry_at=entry_at), "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.cost_r > 0.0
    assert trade.net_r == pytest.approx(trade.r_multiple - trade.cost_r)


def test_horizon_caps_the_hold() -> None:
    entry_at = MONDAY + timedelta(minutes=15)
    bars = [bar(15, 100.0, 100.02, 99.98, 100.0)]
    for k in range(1, 600):
        bars.append(bar(15 + 15 * k, 100.0, 100.05, 99.95, 100.0))
    trade = simulate_trade(candidate(entry_at=entry_at), "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert (trade.exit_at - trade.entry_at) <= timedelta(days=5, hours=1)


def test_short_mirror_stops_out_on_a_rally() -> None:
    entry_at = MONDAY + timedelta(minutes=15)
    bars = [
        bar(15, 100.0, 100.05, 99.95, 100.0),
        bar(30, 100.0, 100.2, 99.9, 100.0),
        bar(45, 100.0, 101.2, 99.9, 100.4),
    ]
    cand = SetupCandidate(
        setup_id="SU1-v1", side="short", trigger_at=entry_at - timedelta(hours=1),
        decision_at=entry_at, entry_at=entry_at, entry_price=100.0, stop_price=101.0,
        target_a_price=99.0, atr_h1=1.0, expires_at=entry_at + timedelta(hours=1),
        trigger_ids=(),
    )
    trade = simulate_trade(cand, "EURUSD", bars, [], cfg=cfg())
    assert trade is not None
    assert trade.exit_reason == "stop"
    assert trade.r_multiple == pytest.approx(-1.0, abs=1e-9)


def test_d1_context_never_reads_a_future_label() -> None:
    d1 = []
    price = 100.0
    for k in range(40):
        price += 0.5
        d1.append(OHLCBar(MONDAY + timedelta(days=k), price, price + 0.2, price - 0.2, price, 1.0))
    series = d1_context_series(d1, period=20, slope_bars=3)
    assert series, "expected labels after the seed"
    first_ts = series[0][0]
    assert context_at(series, first_ts - timedelta(days=1)) == "neutral"
    assert context_at(series, first_ts) == series[0][1]


def test_trade_win_property_uses_net_r() -> None:
    trade = Trade(
        pair="EURUSD", setup_id="SU1-v1", side="long", entry_at=MONDAY,
        exit_at=MONDAY, entry_price=100.0, stop_price=99.0, exit_price=100.0,
        atr_h1=1.0, risk_price=1.0, exit_reason="trail", r_multiple=0.05,
        cost_r=0.06, net_r=-0.01, mae_r=0.0, mfe_r=0.0, bars_held=1,
        partial_taken=False,
    )
    assert trade.win is False
