"""Time-decayed Markov transition probabilities for regime persistence/shift."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarkovResult:
    pair: str
    as_of_date: str
    current_regime: str
    forward_window_days: int
    continuation_probability: float
    transition_probabilities: dict[str, float]
    weighted_sample_size: float


def _to_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def compute_time_decayed_markov(
    pair: str,
    as_of_date: date,
    current_regime: str,
    historical_prices: list[dict[str, Any]],
    regime_calls: list[dict[str, Any]],
    forward_days: int = 5,
    half_life_years: float = 3.0,
) -> MarkovResult:
    _ = historical_prices
    by_date: dict[date, str] = {}
    for row in regime_calls:
        dt = _to_date(row.get("date"))
        regime = row.get("regime")
        if dt is None or regime is None:
            continue
        if dt >= as_of_date:
            continue
        by_date[dt] = str(regime)

    ordered_dates = sorted(by_date)
    if len(ordered_dates) <= forward_days:
        return MarkovResult(
            pair=pair,
            as_of_date=as_of_date.isoformat(),
            current_regime=current_regime,
            forward_window_days=forward_days,
            continuation_probability=0.0,
            transition_probabilities={},
            weighted_sample_size=0.0,
        )

    lambda_decay = math.log(2.0) / (half_life_years * 365.25)
    totals_by_target: dict[str, float] = {}
    total_weight = 0.0
    continuation_weight = 0.0

    for idx in range(0, len(ordered_dates) - forward_days):
        t0 = ordered_dates[idx]
        t1 = ordered_dates[idx + forward_days]
        from_regime = by_date[t0]
        to_regime = by_date[t1]
        if from_regime != current_regime:
            continue
        age_days = (as_of_date - t0).days
        if age_days < 0:
            continue
        weight = math.exp(-lambda_decay * age_days)
        total_weight += weight
        totals_by_target[to_regime] = totals_by_target.get(to_regime, 0.0) + weight
        if to_regime == current_regime:
            continuation_weight += weight

    if total_weight <= 0.0:
        logger.info("Markov result empty for %s (%s)", pair, current_regime)
        return MarkovResult(
            pair=pair,
            as_of_date=as_of_date.isoformat(),
            current_regime=current_regime,
            forward_window_days=forward_days,
            continuation_probability=0.0,
            transition_probabilities={},
            weighted_sample_size=0.0,
        )

    probabilities = {
        regime: (weight / total_weight) * 100.0
        for regime, weight in sorted(
            totals_by_target.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    }
    continuation = (continuation_weight / total_weight) * 100.0
    logger.info(
        "Markov probabilities for %s (%s): continuation=%.2f",
        pair,
        current_regime,
        continuation,
    )
    return MarkovResult(
        pair=pair,
        as_of_date=as_of_date.isoformat(),
        current_regime=current_regime,
        forward_window_days=forward_days,
        continuation_probability=continuation,
        transition_probabilities=probabilities,
        weighted_sample_size=total_weight,
    )
