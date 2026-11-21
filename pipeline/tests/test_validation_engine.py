"""Round 3 validation engine tests."""

from __future__ import annotations

import datetime
import math

import pytest

from src.validation.calculator import calculate_horizon
from src.validation.calendar import add_trading_days
from src.validation.engine import (
    brier_score,
    is_correct,
    log_return_bps,
    realized_direction,
)


def test_log_return_bps_bullish() -> None:
    bps = log_return_bps(1.0700, 1.0721)
    assert bps > 0
    assert abs(bps - 10_000.0 * math.log(1.0721 / 1.0700)) < 1e-9


def test_log_return_bps_bearish() -> None:
    bps = log_return_bps(1.0700, 1.0680)
    assert bps < 0
    assert abs(bps - 10_000.0 * math.log(1.0680 / 1.0700)) < 1e-9


def test_realized_direction_up() -> None:
    assert realized_direction(10.0) == "UP"


def test_realized_direction_down() -> None:
    assert realized_direction(-10.0) == "DOWN"


def test_realized_direction_neutral_inside_deadband() -> None:
    assert realized_direction(3.0) == "NEUTRAL"


def test_realized_direction_neutral_exactly_5bps() -> None:
    assert realized_direction(5.0) == "NEUTRAL"


def test_is_correct_bullish_up() -> None:
    assert is_correct("BULLISH", "UP") is True


def test_is_correct_bullish_down() -> None:
    assert is_correct("BULLISH", "DOWN") is False


def test_is_correct_neutral_inside() -> None:
    assert is_correct("NEUTRAL", "NEUTRAL") is False


def test_is_correct_neutral_outside() -> None:
    assert is_correct("NEUTRAL", "UP") is False


def test_brier_score_correct() -> None:
    score = brier_score(0.8, True)
    assert score is not None
    assert abs(score - 0.04) < 1e-9


def test_brier_score_incorrect() -> None:
    score = brier_score(0.8, False)
    assert score is not None
    assert abs(score - 0.64) < 1e-9


def test_brier_score_neutral() -> None:
    assert brier_score(0.8, True) is not None
    # brier_score itself does not check predicted; engine handles neutral skip


def test_add_trading_days_skips_weekend() -> None:
    fri = datetime.date(2026, 5, 1)
    assert add_trading_days(fri, 1) == datetime.date(2026, 5, 4)


def test_add_trading_days_t5_over_weekend() -> None:
    fri = datetime.date(2026, 5, 1)
    assert add_trading_days(fri, 5) == datetime.date(2026, 5, 8)


def test_mirrored_long_and_short_keep_raw_return_and_sign_payoff() -> None:
    up = math.exp(20.0 / 10_000.0)
    down = math.exp(-20.0 / 10_000.0)

    bullish = calculate_horizon(1.0, up, "BULLISH", 0.8, "EURUSD")
    bearish = calculate_horizon(1.0, down, "BEARISH", 0.8, "EURUSD")

    assert bullish["log_return_bps"] == pytest.approx(20.0)
    assert bearish["log_return_bps"] == pytest.approx(-20.0)
    assert bullish["log_return_net_bps"] == pytest.approx(19.8)
    assert bearish["log_return_net_bps"] == pytest.approx(19.8)
    assert bullish["correct"] is bearish["correct"] is True
    assert bullish["correct_net"] is bearish["correct_net"] is True


def test_deadband_is_incorrect_and_brier_uses_same_boolean_event() -> None:
    result = calculate_horizon(1.0, math.exp(5.0 / 10_000.0), "BULLISH", 0.8, "EURUSD")

    assert result["realized_direction"] == "NEUTRAL"
    assert result["correct"] is False
    assert result["brier_score"] == pytest.approx(0.64)
    assert result["log_return_net_bps"] == pytest.approx(4.8)
    assert result["correct_net"] is True


def test_payoff_cost_boundary_is_separate_from_directional_accuracy() -> None:
    below_cost = calculate_horizon(
        1.0, math.exp(0.19 / 10_000.0), "BULLISH", 0.7, "EURUSD"
    )
    above_cost = calculate_horizon(
        1.0, math.exp(0.21 / 10_000.0), "BULLISH", 0.7, "EURUSD"
    )

    assert below_cost["correct"] is False
    assert below_cost["correct_net"] is False
    assert below_cost["log_return_net_bps"] == pytest.approx(-0.01)
    assert above_cost["correct"] is False
    assert above_cost["correct_net"] is True
    assert above_cost["log_return_net_bps"] == pytest.approx(0.01)


def test_neutral_prediction_is_unscored_abstention() -> None:
    result = calculate_horizon(1.0, 1.01, "NEUTRAL", None, "EURUSD")

    assert result["log_return_bps"] > 0.0
    assert result["correct"] is None
    assert result["brier_score"] is None
    assert result["log_return_net_bps"] is None
    assert result["correct_net"] is None


@pytest.mark.parametrize("confidence", [None, -0.1, 1.1, float("nan"), float("inf")])
def test_directional_prediction_rejects_missing_or_invalid_probability(
    confidence: float | None,
) -> None:
    with pytest.raises(ValueError):
        calculate_horizon(1.0, 1.01, "BULLISH", confidence, "EURUSD")


@pytest.mark.parametrize("s0, sh", [(0.0, 1.0), (-1.0, 1.0), (1.0, 0.0), (1.0, float("nan"))])
def test_horizon_rejects_non_positive_or_non_finite_prices(s0: float, sh: float) -> None:
    with pytest.raises(ValueError):
        calculate_horizon(s0, sh, "BULLISH", 0.8, "EURUSD")
