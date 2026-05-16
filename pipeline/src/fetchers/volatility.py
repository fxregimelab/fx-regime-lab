"""Realized vol from spot closes; implied vol from listed FX options (best effort)."""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np

from src.types import SpotBar

logger = logging.getLogger(__name__)


def fetch_realized_vol(spots: dict[str, Sequence[SpotBar]]) -> dict[str, dict[str, float]]:
    """Annualized realized vol (%) from log returns over 5d and 20d windows."""
    out: dict[str, dict[str, float]] = {}
    for pair, bars in spots.items():
        if len(bars) < 6:
            continue
        closes = np.array([b.close for b in bars], dtype=float)
        if np.any(closes <= 0):
            continue
        log_returns = np.diff(np.log(closes))
        if log_returns.size < 20:
            continue
        rv5 = float(np.std(log_returns[-5:], ddof=0) * np.sqrt(252) * 100)
        rv20 = float(np.std(log_returns[-20:], ddof=0) * np.sqrt(252) * 100)
        out[pair] = {"realized_vol_5d": rv5, "realized_vol_20d": rv20}
    return out


def fetch_implied_vol(pair: str) -> float | None:
    """Best-effort implied vol proxy from CBOE FX volatility indices.

    .. note::
        CBOE FX vol indices (^EUV, ^JXV) were delisted from Yahoo Finance.
        This function currently returns ``None`` for all pairs until a
        replacement data source (e.g. CME options vol, broker feed) is
        wired in.
    """
    _ = pair
    logger.debug("implied_vol_30d is currently unavailable — CBOE FX vol indices delisted")
    return None
