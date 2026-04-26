"""Yield spread signal and normalization."""

from __future__ import annotations

import numpy as np

from src.types import RawYields


def compute_rate_signal(yields: RawYields | None, pair: str) -> tuple[float | None, str]:
    """Return (2y spread in percentage points, direction label)."""
    if yields is None:
        return None, "NEUTRAL"
    spread: float | None = None
    if pair == "EURUSD":
        if yields.de_2y is None:
            return None, "NEUTRAL"
        spread = yields.us_2y - yields.de_2y
    elif pair == "USDJPY":
        if yields.jp_2y is None:
            return None, "NEUTRAL"
        spread = yields.us_2y - yields.jp_2y
    elif pair == "USDINR":
        if yields.in_2y is None:
            return None, "NEUTRAL"
        spread = yields.us_2y - yields.in_2y
    else:
        return None, "NEUTRAL"

    if spread is None:
        return None, "NEUTRAL"
    if spread > 0.5:
        direction = "BULLISH"
    elif spread < -0.5:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"
    return spread, direction


def normalize_rate_signal(spread: float, pair: str) -> float:
    if pair == "EURUSD":
        return float(np.clip(spread / 3.0, -1.0, 1.0))
    if pair in ("USDJPY", "USDINR"):
        return float(np.clip((spread - 3.0) / 3.0, -1.0, 1.0))
    return float(np.clip(spread / 3.0, -1.0, 1.0))
