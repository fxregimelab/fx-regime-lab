"""Unit tests for InvalidationEvaluator pure logic."""

from __future__ import annotations

import pytest

from src.desk.invalidation import (
    INVALIDATION_PERSISTENCE_TICKS,
    INVALIDATION_VOL_MULTIPLIER,
    OFFLINE_FAILURE_THRESHOLD,
    InvalidationEvaluator,
)
from src.desk.invalidation_types import BreachInput, StreakState

_EVALUATOR = InvalidationEvaluator()


def _evaluate(
    *,
    live_spot: float,
    ny_close: float,
    rv20: float,
    vix_trigger: bool = False,
    prev_inv: bool = False,
    streak: int = 0,
) -> tuple[bool, bool, int, bool, bool]:
    decision = _EVALUATOR.evaluate(
        BreachInput(
            live_spot=live_spot,
            ny_close=ny_close,
            realized_vol_20d=rv20,
            vix_trigger=vix_trigger,
            prev_invalidation_triggered=prev_inv,
        ),
        StreakState(streak_count=streak),
    )
    return (
        decision.breach,
        decision.pair_trigger,
        decision.new_streak_count,
        decision.invalidation_triggered,
        decision.pending_invalidation,
    )


@pytest.mark.parametrize(
    ("live_spot", "ny_close", "rv20", "expect_breach"),
    [
        (1.0100, 1.0000, 1.0, False),  # 1% move < 1.5% threshold
        (1.0200, 1.0000, 1.0, True),  # 2% > 1.5%
        (1.0050, 1.0000, 1.0, False),  # 0.5% < 1.5%
        (0.9900, 1.0000, 1.0, False),  # -1% abs < 1.5%
        (0.9800, 1.0000, 1.0, True),  # -2% abs > 1.5%
    ],
)
def test_pair_breach_threshold(
    live_spot: float,
    ny_close: float,
    rv20: float,
    expect_breach: bool,
) -> None:
    breach, pair_trigger, streak, invalidation, pending = _evaluate(
        live_spot=live_spot,
        ny_close=ny_close,
        rv20=rv20,
    )
    assert pair_trigger is expect_breach
    assert breach is expect_breach


def test_no_breach_resets_streak() -> None:
    breach, _, streak, invalidation, pending = _evaluate(
        live_spot=1.001,
        ny_close=1.0,
        rv20=1.0,
        streak=2,
    )
    assert breach is False
    assert streak == 0
    assert invalidation is False
    assert pending is False


def test_breach_increments_streak() -> None:
    breach, _, streak, invalidation, pending = _evaluate(
        live_spot=1.02,
        ny_close=1.0,
        rv20=1.0,
        streak=1,
    )
    assert breach is True
    assert streak == 2
    assert invalidation is False
    assert pending is True


def test_invalidation_at_persistence_threshold() -> None:
    breach, _, streak, invalidation, pending = _evaluate(
        live_spot=1.02,
        ny_close=1.0,
        rv20=1.0,
        streak=INVALIDATION_PERSISTENCE_TICKS - 1,
    )
    assert streak == INVALIDATION_PERSISTENCE_TICKS
    assert invalidation is True
    assert pending is False


def test_prev_invalidation_sticky() -> None:
    breach, _, streak, invalidation, pending = _evaluate(
        live_spot=1.001,
        ny_close=1.0,
        rv20=1.0,
        prev_inv=True,
        streak=0,
    )
    assert breach is False
    assert streak == 0
    assert invalidation is True
    assert pending is False


def test_vix_trigger_causes_breach_without_pair_move() -> None:
    breach, pair_trigger, streak, invalidation, pending = _evaluate(
        live_spot=1.001,
        ny_close=1.0,
        rv20=1.0,
        vix_trigger=True,
    )
    assert pair_trigger is False
    assert breach is True
    assert streak == 1
    assert pending is True


@pytest.mark.parametrize(
    ("live_vix", "baseline_vix", "vol_ref", "expected"),
    [
        (25.0, 20.0, 1.0, True),  # 25% change > 1.5
        (20.2, 20.0, 1.0, False),  # 1% change < 1.5
        (None, 20.0, 1.0, False),
        (25.0, None, 1.0, False),
        (25.0, 0.0, 1.0, False),
        (25.0, 20.0, 0.0, False),
    ],
)
def test_compute_vix_trigger(
    live_vix: float | None,
    baseline_vix: float | None,
    vol_ref: float,
    expected: bool,
) -> None:
    assert (
        InvalidationEvaluator.compute_vix_trigger(live_vix, baseline_vix, vol_ref)
        is expected
    )


def test_constants_unchanged() -> None:
    assert INVALIDATION_VOL_MULTIPLIER == 1.5
    assert INVALIDATION_PERSISTENCE_TICKS == 3
    assert OFFLINE_FAILURE_THRESHOLD == 3


def test_day_change_pct_and_vol_threshold() -> None:
    decision = _EVALUATOR.evaluate(
        BreachInput(live_spot=1.02, ny_close=1.0, realized_vol_20d=2.0, vix_trigger=False),
        StreakState(),
    )
    assert decision.day_change_pct == pytest.approx(2.0)
    assert decision.vol_threshold == pytest.approx(2.0 * INVALIDATION_VOL_MULTIPLIER)
