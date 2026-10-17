"""Tests for the desk checklist engine (pure; synthetic spec-known scenarios).

Fixtures are designed so every check margin is computable by hand:
H1 = 48 bars (rise 1.1000→1.1058, pullback to 1.1008, flat) → ATR_H1 = 0.0074/14,
H4 = 18 bars with rising HH/HL (detected swings: H 1.1075→1.1085, L 1.1040→1.1050).
Entry 1.1008 / stop 1.0988 (20 pips) passes all 14 checks.
"""

from __future__ import annotations

import pytest

from src.paper.checklist import (
    CandidateContext,
    CheckResult,
    ExposureState,
    atr,
    cost_share_of_r,
    ema,
    evaluate,
    size_risk,
    structure_aligned,
)
from src.paper.config import TradingLimits
from src.paper.store import Bar

ENTRY = 1.1008
STOP = 1.0988  # R = 20 pips

# H4 base path: triangle pattern, extrema at every 4th bar (k=2 fractals are clean).
_H4_BASE = [
    1.1045, 1.1048, 1.1052, 1.1055, 1.1050, 1.1046, 1.1043, 1.1040,
    1.1046, 1.1052, 1.1058, 1.1065, 1.1061, 1.1057, 1.1053, 1.1050,
    1.1054, 1.1058,
]


def _bar(t: int, close: float, tf: str, rng: float = 0.0002) -> Bar:
    return Bar(
        symbol="EURUSDm",
        timeframe=tf,
        time_srv=t,
        open=close,
        high=close + rng,
        low=close - rng,
        close=close,
        tick_volume=10,
        spread_points=8,
    )


def _h1_fixture() -> list[Bar]:
    closes: list[float] = [1.1000 + 0.0002 * i for i in range(30)]
    closes += [1.1058 - 0.0005 * (i - 29) for i in range(30, 40)]
    closes += [1.1008] * 8
    return [_bar(t, c, "H1") for t, c in enumerate(closes)]


def _h4_fixture() -> list[Bar]:
    bars: list[Bar] = []
    for i, base in enumerate(_H4_BASE):
        bars.append(
            Bar(
                symbol="EURUSDm",
                timeframe="H4",
                time_srv=i,
                open=base + 0.001,
                high=base + 0.002,
                low=base,
                close=base + 0.001,
                tick_volume=10,
                spread_points=8,
            )
        )
    return bars


def _context(
    *,
    stop: float = STOP,
    red_event_now: bool = False,
    news_conflict: bool = False,
    trigger_present: bool = True,
    exposure: ExposureState | None = None,
) -> CandidateContext:
    return CandidateContext(
        pair="EURUSD",
        direction="long",
        entry=ENTRY,
        stop=stop,
        bars_by_tf={"H1": _h1_fixture(), "H4": _h4_fixture()},
        strategy_rule_fires=True,
        dqs=0.9,
        bars_fresh=True,
        red_event_now=red_event_now,
        red_event_within_2h=False,
        event_cohort=False,
        session_ok=True,
        spread_ok=True,
        news_conflict=news_conflict,
        bias_aligned=True,
        trigger_present=trigger_present,
        exposure=exposure if exposure is not None else ExposureState(),
    )


def _check(results: tuple[CheckResult, ...], check_id: str) -> CheckResult:
    for c in results:
        if c.check_id == check_id:
            return c
    raise AssertionError(f"missing check {check_id}")


def test_fixture_preconditions() -> None:
    """The synthetic setup must sit inside the spec margins it is meant to test."""
    a = atr(_h1_fixture())
    assert a is not None
    assert a == pytest.approx(0.0074 / 14)  # 6 pullback bars (0.0007) + 8 flat (0.0004)
    assert (ENTRY - STOP) >= 1.2 * a  # S5 margin
    assert cost_share_of_r("EURUSD", ENTRY, STOP) <= 0.10  # H4 gate margin
    ok, _ = structure_aligned(_h4_fixture(), "long")
    assert ok


def test_full_pass_is_a_plus_at_slot0_risk() -> None:
    ev = evaluate(_context())
    assert ev.score == 9
    assert ev.grade == "A+"
    assert ev.trade_allowed
    assert ev.risk_pct == pytest.approx(0.05)
    assert ev.slot_ceiling_pct == pytest.approx(0.05)
    assert ev.framework_version and ev.playbook_version


def test_red_event_now_blocks_gate_h3() -> None:
    ev = evaluate(_context(red_event_now=True))
    assert ev.grade == "C"
    assert not ev.trade_allowed
    assert ev.risk_pct is None
    assert not _check(ev.gates, "H3").passed


def test_news_conflict_downgrades_to_a() -> None:
    ev = evaluate(_context(news_conflict=True))
    assert ev.score == 8
    assert ev.grade == "A"
    assert ev.risk_pct == pytest.approx(0.05 * 0.8)


def test_three_scored_failures_grade_b_plus() -> None:
    ev = evaluate(
        _context(
            trigger_present=False,
            news_conflict=True,
            exposure=ExposureState(same_usd_sign_tickets=2),
        )
    )
    assert ev.score == 6
    assert ev.grade == "B+"
    assert ev.risk_pct == pytest.approx(0.05 * 0.6)


def test_tiny_r_fails_cost_gate() -> None:
    ev = evaluate(_context(stop=ENTRY - 0.0003))
    assert not _check(ev.gates, "H4").passed
    assert ev.grade == "C"


def test_stop_at_pool_fails_s6() -> None:
    # Session low at 1.1006; a stop at 1.1005 sits inside the 0.25xATR buffer of the pool.
    ev = evaluate(_context(stop=1.1005))
    assert not _check(ev.scored, "S6").passed


def test_wall_before_1r_fails_s7() -> None:
    # R = 28 pips → needs 35 pips of room; the nearest opposing level is 32 pips away.
    ev = evaluate(_context(stop=1.0980))
    assert not _check(ev.scored, "S7").passed
    assert ev.grade == "A"  # single scored miss


def test_size_risk_slots_and_caps() -> None:
    zero = ExposureState()
    assert size_risk("A+", zero)[0] == pytest.approx(0.05)
    assert size_risk("A+", ExposureState(open_tickets=1))[0] == pytest.approx(0.04)
    assert size_risk("A+", ExposureState(open_tickets=2))[0] == pytest.approx(0.03)
    assert size_risk("A+", ExposureState(open_tickets=3))[0] == pytest.approx(0.03)
    assert size_risk("A+", ExposureState(open_tickets=4)) == (None, None)
    assert size_risk("C", zero) == (None, None)
    # The 15% open-risk cap blocks a new slot even when the slot itself is free.
    blocked = size_risk("A+", ExposureState(open_tickets=0, open_risk_pct=0.13))
    assert blocked[0] is None
    assert blocked[1] == pytest.approx(0.05)
    # Operator-score reduced envelope scales the ceiling down.
    reduced = size_risk("A+", zero, slot_mult=0.75)
    assert reduced[0] == pytest.approx(0.0375)
    # min_effective_risk_pct floor applies on smaller custom ceilings.
    tight = TradingLimits(slot_risk_ceilings=(0.02,))
    tight_result = size_risk("B", zero, limits=tight)
    assert tight_result[0] is None
    assert tight_result[1] == pytest.approx(0.02)


def test_ema_and_atr_helpers() -> None:
    bars = [_bar(i, 1.1000, "H1") for i in range(20)]
    assert atr(bars) == pytest.approx(0.0004)
    assert ema([b.close for b in bars], 20) == pytest.approx(1.1000)
    assert atr(bars[:5]) is None
    assert ema([1.0, 1.0], 5) is None
