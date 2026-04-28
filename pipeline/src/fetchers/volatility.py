"""Realized vol from spot closes; implied vol from listed FX options (best effort)."""

from __future__ import annotations

import logging

import numpy as np
import yfinance as yf

from src.types import SpotBar

logger = logging.getLogger(__name__)


def fetch_realized_vol(spots: dict[str, list[SpotBar]]) -> dict[str, dict[str, float]]:
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
    """Best-effort implied vol proxy from CBOE FX volatility indices."""
    vol_symbol_by_pair: dict[str, str | None] = {
        "EURUSD": "^EUV",
        "USDJPY": "^JXV",
        "USDINR": None,
    }
    symbol = vol_symbol_by_pair.get(pair)
    if symbol is None:
        return None

    try:
        history = yf.Ticker(symbol).history(period="5d")
        if history is None or history.empty or "Close" not in history:
            return None
        closes = history["Close"].dropna()
        if closes.empty:
            return None
        return float(closes.iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.debug("implied vol unavailable for %s via %s: %s", pair, symbol, exc)
        return None
