"""Canonical validation math for T+5/T+20 horizon metrics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

COST_BPS_ROUND_TRIP: dict[str, float] = {
    "EURUSD": 0.2,  # 0.1 bps each way
    "USDJPY": 0.3,
    "USDINR": 10.0,  # EM spread
}

DEADBAND_BPS = 5.0


def log_return_bps(s0: float, sh: float) -> float:
    """Log-return in basis points: 10_000 * ln(sh / s0)."""
    return 10_000.0 * math.log(sh / s0)


def realized_direction(bps: float, deadband: float = DEADBAND_BPS) -> str:
    """Map log-return bps to realized directional label."""
    if bps > deadband:
        return "UP"
    if bps < -deadband:
        return "DOWN"
    return "NEUTRAL"


def is_correct(predicted: str, realized: str) -> bool:
    """Check if predicted direction matches realized direction."""
    p = predicted.strip().upper()
    r = realized.strip().upper()
    if p == "BULLISH":
        return r == "UP"
    if p == "BEARISH":
        return r == "DOWN"
    if p == "NEUTRAL":
        return r == "NEUTRAL"
    return False


def is_correct_net(predicted: str, bps_net: float) -> bool:
    """Net correctness: did the trade make money after costs?

    For directional predictions this is simply the sign of the cost-adjusted
    log return. NEUTRAL predictions are net-correct only when the net move is
    inside the same deadband used for gross realized direction.
    """
    p = predicted.strip().upper()
    if p == "BULLISH":
        return bps_net > 0.0
    if p == "BEARISH":
        return bps_net < 0.0
    if p == "NEUTRAL":
        return realized_direction(bps_net) == "NEUTRAL"
    return False


def brier_score(confidence: float, correct: bool) -> float | None:
    """Brier score: (p - y)^2 on gross directional match."""
    p = float(confidence)
    y = 1.0 if correct else 0.0
    return (p - y) ** 2


@dataclass(frozen=True, slots=True)
class HorizonMetrics:
    log_return_bps: float
    log_return_net_bps: float
    realized_direction: str
    correct: bool
    correct_net: bool
    brier_score: float | None
    cost_bps: float


def compute_horizon_metrics(
    s0: float,
    sh: float | None,
    predicted: str,
    confidence: float,
    pair: str,
) -> HorizonMetrics | None:
    """Compute validation metrics including cost-adjusted returns."""
    if sh is None:
        return None

    bps_gross = log_return_bps(s0, sh)
    cost_bps = COST_BPS_ROUND_TRIP.get(pair, 0.5)
    bps_net = bps_gross - cost_bps

    realized_gross = realized_direction(bps_gross)
    correct_gross = is_correct(predicted, realized_gross)
    correct_net = is_correct_net(predicted, bps_net)
    brier = brier_score(confidence, correct_gross)

    return HorizonMetrics(
        log_return_bps=bps_gross,
        log_return_net_bps=bps_net,
        realized_direction=realized_gross,
        correct=correct_gross,
        correct_net=correct_net,
        brier_score=brier,
        cost_bps=cost_bps,
    )


def horizon_metrics_to_payload(
    metrics: HorizonMetrics,
    horizon: Literal["t5", "t20"],
) -> dict[str, Any]:
    """Map HorizonMetrics to validation_log column names for one horizon."""
    if horizon == "t5":
        return {
            "log_return_t5_bps": metrics.log_return_bps,
            "correct_t5": metrics.correct,
            "brier_score_t5": metrics.brier_score,
            "actual_direction_t5": metrics.realized_direction,
            "actual_return_5d": metrics.log_return_bps / 10_000.0,
            "correct_5d": metrics.correct,
            "brier_5d": metrics.brier_score,
            "log_return_net_bps_t5": metrics.log_return_net_bps,
            "correct_net_t5": metrics.correct_net,
            "cost_bps_t5": metrics.cost_bps,
        }

    return {
        "log_return_t20_bps": metrics.log_return_bps,
        "correct_t20": metrics.correct,
        "brier_score_t20": metrics.brier_score,
        "actual_direction_t20": metrics.realized_direction,
        "actual_return_20d": metrics.log_return_bps / 10_000.0,
        "correct_20d": metrics.correct,
        "brier_20d": metrics.brier_score,
        "log_return_net_bps_t20": metrics.log_return_net_bps,
        "correct_net_t20": metrics.correct_net,
        "cost_bps_t20": metrics.cost_bps,
    }
