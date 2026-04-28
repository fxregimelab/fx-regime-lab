"""Yield legs fetched from yfinance with FRED fallbacks."""

from __future__ import annotations

import logging
import os
import time
from datetime import date

import yfinance as yf
from fredapi import Fred

from src.types import RawYields

logger = logging.getLogger(__name__)


def _yf_leg(ticker: str, label: str, period: str) -> float | None:
    try:
        history = yf.Ticker(ticker).history(period=period)
        if history is None or history.empty or "Close" not in history:
            logger.warning("yfinance %s (%s) returned empty history", label, ticker)
            return None
        closes = history["Close"].dropna()
        if closes.empty:
            logger.warning("yfinance %s (%s) returned empty close series", label, ticker)
            return None
        return float(closes.iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance %s (%s) fetch failed: %s", label, ticker, exc)
        return None


def _fred_leg(fred: Fred | None, series_ids: tuple[str, ...], label: str) -> float | None:
    if fred is None:
        return None
    for series_id in series_ids:
        try:
            values = fred.get_series_latest_release(series_id)
            if values is None or values.empty:
                logger.warning("FRED %s (%s) returned empty series", label, series_id)
                continue
            clean = values.dropna()
            if clean.empty:
                logger.warning("FRED %s (%s) returned NaN-only series", label, series_id)
                continue
            return float(clean.iloc[-1])
        except Exception as exc:  # noqa: BLE001
            logger.warning("FRED %s (%s) fetch failed: %s", label, series_id, exc)
    return None


def fetch_yields(lookback_days: int = 5) -> list[RawYields]:
    """Fetch latest sovereign yield legs with yfinance first and FRED fallback.

    Uses yfinance proxies first, then FRED fallback for missing legs. ``lookback_days`` controls
    yfinance lookback and remains for API compatibility.
    """
    window_days = max(lookback_days, 1)
    period = f"{window_days}d"
    today = date.today()
    fred_key = os.environ.get("FRED_API_KEY")
    fred = Fred(api_key=fred_key) if fred_key else None
    if fred is None:
        logger.warning("FRED_API_KEY not set — yield fallbacks limited to yfinance only")

    us_2y = _yf_leg("^IRX", "US short-term yield proxy", period)
    time.sleep(1.0)
    de_2y = _yf_leg("^DE2Y", "DE 2Y", period)
    time.sleep(1.0)
    jp_2y = _yf_leg("^JP2Y", "JP 2Y", period)
    time.sleep(1.0)
    in_2y = _yf_leg("^IN2Y", "IN 2Y", period)
    time.sleep(1.0)

    us_10y = _yf_leg("^TNX", "US 10Y", period)
    time.sleep(1.0)
    de_10y = _yf_leg("^TGD10Y", "DE 10Y proxy", period)
    time.sleep(1.0)
    jp_10y = _yf_leg("^JG10Y", "JP 10Y proxy", period)
    time.sleep(1.0)
    in_10y = _yf_leg("^IN10Y", "IN 10Y proxy", period)

    if us_2y is None:
        us_2y = _fred_leg(fred, ("DGS2",), "US 2Y")
    if us_10y is None:
        us_10y = _fred_leg(fred, ("DGS10",), "US 10Y")
    if jp_10y is None:
        jp_10y = _fred_leg(fred, ("IRLTLT01JPM156N",), "JP 10Y")
    if in_10y is None:
        in_10y = _fred_leg(fred, ("INDIRLTLT01STM",), "IN 10Y")
    if de_10y is None:
        de_10y = _fred_leg(fred, ("IRLTLT01DEM156N",), "DE 10Y")

    # Best effort for USDINR: if dedicated 2Y is unavailable, use 10Y as tenor proxy.
    if in_2y is None and in_10y is not None:
        in_2y = in_10y

    if us_2y is None:
        logger.warning("US yield leg missing after fallback; returning empty yields list")
        return []

    return [
        RawYields(
            date=today,
            us_2y=us_2y,
            de_2y=de_2y,
            jp_2y=jp_2y,
            in_2y=in_2y,
            us_10y=us_10y,
            de_10y=de_10y,
            jp_10y=jp_10y,
            in_10y=in_10y,
        )
    ]
