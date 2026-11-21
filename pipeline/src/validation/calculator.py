"""Pure, shared validation calculations for live and replay evaluation."""

from __future__ import annotations

import math
from typing import Any, TypedDict

DEADBAND_BPS = 5.0
EVALUATION_VERSION = "publication-snapshot-v2"

# Research assumptions, not observed execution costs.
COST_BPS_ROUND_TRIP: dict[str, float] = {
    "EURUSD": 0.2,
    "USDJPY": 0.3,
    "USDINR": 10.0,
}

_DIRECTION_SIDE = {"BULLISH": 1.0, "BEARISH": -1.0}
_VALID_DIRECTIONS = frozenset((*_DIRECTION_SIDE, "NEUTRAL"))


class HorizonEvaluation(TypedDict):
    log_return_bps: float
    log_return_net_bps: float | None
    realized_direction: str
    correct: bool | None
    correct_net: bool | None
    brier_score: float | None
    cost_bps: float


def _finite_float(value: Any, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number")
    return number


def normalize_predicted_direction(value: Any) -> str:
    """Return a supported published direction or reject the call as unknown."""
    if value is None:
        raise ValueError("predicted_direction is required")
    direction = str(value).strip().upper()
    if direction not in _VALID_DIRECTIONS:
        raise ValueError(f"unsupported predicted_direction: {value!r}")
    return direction


def validate_probability(value: Any) -> float:
    """Return a finite probability in the closed interval [0, 1]."""
    probability = _finite_float(value, "confidence")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    return probability


def validate_price(value: Any, label: str) -> float:
    """Return a finite, strictly positive market price."""
    price = _finite_float(value, label)
    if price <= 0.0:
        raise ValueError(f"{label} must be positive")
    return price


def log_return_bps(s0: Any, sh: Any) -> float:
    """Underlying market log return in basis points, before direction or cost."""
    start = validate_price(s0, "s0")
    horizon = validate_price(sh, "sh")
    return 10_000.0 * math.log(horizon / start)


def realized_direction(bps: Any, deadband: float = DEADBAND_BPS) -> str:
    """Map an underlying market return to UP, DOWN, or the deadband."""
    market_return = _finite_float(bps, "log_return_bps")
    threshold = _finite_float(deadband, "deadband")
    if threshold < 0.0:
        raise ValueError("deadband must be non-negative")
    if market_return > threshold:
        return "UP"
    if market_return < -threshold:
        return "DOWN"
    return "NEUTRAL"


def directional_correctness(predicted: Any, realized: Any) -> bool | None:
    """Score a directional call; NEUTRAL is an abstention and has no score."""
    direction = normalize_predicted_direction(predicted)
    actual = str(realized).strip().upper()
    if actual not in {"UP", "DOWN", "NEUTRAL"}:
        raise ValueError(f"unsupported realized direction: {realized!r}")
    if direction == "NEUTRAL":
        return None
    if direction == "BULLISH":
        return actual == "UP"
    return actual == "DOWN"


def brier_score(probability: Any, correct: bool) -> float:
    """Binary Brier score using the same correctness event as accuracy."""
    if not isinstance(correct, bool):
        raise ValueError("correct must be boolean")
    p = validate_probability(probability)
    y = 1.0 if correct else 0.0
    return (p - y) ** 2


def calculate_horizon(
    s0: Any,
    sh: Any,
    predicted_direction: Any,
    confidence: Any,
    pair: str,
) -> HorizonEvaluation:
    """Calculate one horizon using the canonical validation event definition."""
    predicted = normalize_predicted_direction(predicted_direction)
    raw_return = log_return_bps(s0, sh)
    actual = realized_direction(raw_return)
    correct = directional_correctness(predicted, actual)
    if pair not in COST_BPS_ROUND_TRIP:
        raise ValueError(f"no explicit cost assumption for pair: {pair!r}")
    cost_bps = _finite_float(COST_BPS_ROUND_TRIP[pair], "cost_bps")
    if cost_bps <= 0.0:
        raise ValueError("cost_bps must be positive")

    if predicted == "NEUTRAL":
        if confidence is not None:
            validate_probability(confidence)
        return {
            "log_return_bps": raw_return,
            "log_return_net_bps": None,
            "realized_direction": actual,
            "correct": None,
            "correct_net": None,
            "brier_score": None,
            "cost_bps": cost_bps,
        }

    probability = validate_probability(confidence)
    assert correct is not None
    payoff_bps = _DIRECTION_SIDE[predicted] * raw_return - cost_bps
    return {
        "log_return_bps": raw_return,
        "log_return_net_bps": payoff_bps,
        "realized_direction": actual,
        "correct": correct,
        "correct_net": payoff_bps > 0.0,
        "brier_score": brier_score(probability, correct),
        "cost_bps": cost_bps,
    }
