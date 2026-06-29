"""Unit tests for validation calculator primitives."""

from __future__ import annotations

import math

import pytest

from src.validation.calculator import (
    COST_BPS_ROUND_TRIP,
    DEADBAND_BPS,
    brier_score,
    compute_horizon_metrics,
    horizon_metrics_to_payload,
    is_correct,
    is_correct_net,
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
    assert is_correct("NEUTRAL", "NEUTRAL") is True


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


@pytest.mark.parametrize(
    ("pair", "expected_cost"),
    [
        ("EURUSD", 0.2),
        ("USDJPY", 0.3),
        ("USDINR", 10.0),
    ],
)
def test_cost_bps_round_trip(pair: str, expected_cost: float) -> None:
    assert COST_BPS_ROUND_TRIP[pair] == expected_cost


def test_deadband_constant() -> None:
    assert DEADBAND_BPS == 5.0


def test_is_correct_net_neutral_inside_deadband_after_cost() -> None:
    # Gross 5.1 bps is UP, but net 4.9 bps is still NEUTRAL after EUR cost.
    assert is_correct_net("NEUTRAL", 4.9) is True
    assert is_correct_net("NEUTRAL", 5.1) is False


def test_correct_net_uses_cost_adjusted_return() -> None:
    """Net correctness reflects profitability after costs, not gross direction."""
    s0 = 1.0000
    sh = 1.00051  # 5.1 bps gross → realized UP
    result = compute_horizon_metrics(s0, sh, "NEUTRAL", 0.5, "EURUSD")
    assert result is not None
    assert result.correct is False
    assert result.correct_net is True

    sh2 = 1.00003  # 0.3 bps gross → realized NEUTRAL, gross False
    result2 = compute_horizon_metrics(s0, sh2, "BULLISH", 0.5, "EURUSD")
    assert result2 is not None
    assert result2.correct is False
    assert result2.correct_net is True  # net 0.1 bps > 0

    sh3 = 0.9980  # -20 bps
    result3 = compute_horizon_metrics(s0, sh3, "BEARISH", 0.5, "USDJPY")
    assert result3 is not None
    assert result3.correct is True
    assert result3.correct_net is True


def test_inr_cost_edge_net_differs_from_gross() -> None:
    """USDINR 10 bps cost can flip net correctness vs gross."""
    s0 = 83.0
    # ~6 bps gross UP: gross correct for BULLISH, net negative after 10 bps cost.
    sh = s0 * math.exp(6.0 / 10_000.0)
    metrics = compute_horizon_metrics(s0, sh, "BULLISH", 0.7, "USDINR")
    assert metrics is not None
    assert metrics.correct is True
    assert metrics.correct_net is False
    assert metrics.cost_bps == 10.0


def test_horizon_metrics_to_payload_t5_keys() -> None:
    metrics = compute_horizon_metrics(1.0, 1.001, "BULLISH", 0.8, "EURUSD")
    assert metrics is not None
    payload = horizon_metrics_to_payload(metrics, "t5")
    assert payload["correct_t5"] == metrics.correct
    assert payload["correct_net_t5"] == metrics.correct_net
    assert payload["cost_bps_t5"] == metrics.cost_bps


def test_horizon_metrics_to_payload_t20_keys() -> None:
    metrics = compute_horizon_metrics(1.0, 1.001, "BULLISH", 0.8, "EURUSD")
    assert metrics is not None
    payload = horizon_metrics_to_payload(metrics, "t20")
    assert payload["correct_t20"] == metrics.correct
    assert payload["correct_net_t20"] == metrics.correct_net
    assert payload["cost_bps_t20"] == metrics.cost_bps
