"""Yield spread signal and normalization."""

from __future__ import annotations

import math

from src.types import RawYields


def compute_rate_signal(
    yields: RawYields | None, pair: str
) -> tuple[float | None, float | None, str]:
    """Return (2y spread, 10y spread, direction) in percentage points."""
    if yields is None:
        return None, None, "NEUTRAL"
    spread_2y: float | None = None
    spread_10y: float | None = None
    if pair == "EURUSD":
        if yields.de_2y is not None:
            spread_2y = yields.us_2y - yields.de_2y
        if yields.us_10y is not None and yields.de_10y is not None:
            spread_10y = yields.us_10y - yields.de_10y
    elif pair == "USDJPY":
        if yields.jp_2y is not None:
            spread_2y = yields.us_2y - yields.jp_2y
        if yields.us_10y is not None and yields.jp_10y is not None:
            spread_10y = yields.us_10y - yields.jp_10y
    elif pair == "USDINR":
        if yields.in_2y is not None:
            spread_2y = yields.us_2y - yields.in_2y
        if yields.us_10y is not None and yields.in_10y is not None:
            spread_10y = yields.us_10y - yields.in_10y
    else:
        return None, None, "NEUTRAL"

    directional_spread = spread_2y if spread_2y is not None else spread_10y
    if directional_spread is None:
        return spread_2y, spread_10y, "NEUTRAL"
    if directional_spread > 0.5:
        direction = "BULLISH"
    elif directional_spread < -0.5:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"
    return spread_2y, spread_10y, direction


def normalize_rate_signal(spread: float, pair: str, historical_spreads: list[float]) -> float:
    _ = pair
    if not historical_spreads:
        return 0.0

    mean = sum(historical_spreads) / len(historical_spreads)
    variance = sum((x - mean) ** 2 for x in historical_spreads) / len(historical_spreads)
    std = math.sqrt(variance)
    z_score = (spread - mean) / std if std > 0 else 0.0
    z_clipped = max(-2.0, min(2.0, z_score))
    return z_clipped / 2.0
