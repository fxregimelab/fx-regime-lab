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

YF_2Y_TICKERS: dict[str, str] = {
    "us_2y": "^UST2Y",
    "de_2y": "^DE2Y",
    "jp_2y": "^JP2Y",
    "in_2y": "^IN2Y",
}

YF_10Y_TICKERS: dict[str, str] = {
    "us_10y": "^TNX",
    "de_10y": "^TGD10Y",
    "jp_10y": "^JG10Y",
    "in_10y": "^IN10Y",
}

FRED_FALLBACK_SERIES: dict[str, tuple[str, ...]] = {
    "us_2y": ("DGS2",),
    "us_10y": ("DGS10",),
    "de_10y": ("IRLTLT01DEM156N",),
    "jp_10y": ("IRLTLT01JPM156N",),
    "in_10y": ("INDIRLTLT01STM",),
}


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


def _fetch_yf_legs(
    tickers: dict[str, str],
    period: str,
) -> dict[str, float | None]:
    legs: dict[str, float | None] = {}
    total = len(tickers)
    for idx, (leg_name, ticker) in enumerate(tickers.items()):
        legs[leg_name] = _yf_leg(ticker, leg_name, period)
        if idx < total - 1:
            time.sleep(1.0)
    return legs


def fetch_yields(lookback_days: int = 5) -> list[RawYields]:
    """Fetch latest sovereign yield legs with FRED-priority US legs.

    US 2Y/10Y are sourced from FRED first (DGS2/DGS10) to avoid unstable Yahoo tickers.
    Non-US legs still use yfinance first with FRED fallback where configured.
    ``lookback_days`` controls yfinance lookback and remains for API compatibility.
    """
    window_days = max(lookback_days, 1)
    period = f"{window_days}d"
    today = date.today()
    fred_key = os.environ.get("FRED_API_KEY")
    fred = Fred(api_key=fred_key) if fred_key else None
    if fred is None:
        logger.warning("FRED_API_KEY not set — yield fallbacks limited to yfinance only")

    two_year_legs = _fetch_yf_legs(YF_2Y_TICKERS, period)
    time.sleep(1.0)
    ten_year_legs = _fetch_yf_legs(YF_10Y_TICKERS, period)

    # Prioritize FRED for US rates; only use Yahoo when FRED is unavailable.
    fred_us_2y = _fred_leg(fred, FRED_FALLBACK_SERIES["us_2y"], "US 2Y")
    fred_us_10y = _fred_leg(fred, FRED_FALLBACK_SERIES["us_10y"], "US 10Y")
    if fred_us_2y is not None:
        two_year_legs["us_2y"] = fred_us_2y
    elif two_year_legs["us_2y"] is None:
        logger.warning("US 2Y unavailable in both FRED and yfinance")
    if fred_us_10y is not None:
        ten_year_legs["us_10y"] = fred_us_10y
    elif ten_year_legs["us_10y"] is None:
        logger.warning("US 10Y unavailable in both FRED and yfinance")
    if ten_year_legs["de_10y"] is None:
        ten_year_legs["de_10y"] = _fred_leg(fred, FRED_FALLBACK_SERIES["de_10y"], "DE 10Y")
    if ten_year_legs["jp_10y"] is None:
        ten_year_legs["jp_10y"] = _fred_leg(fred, FRED_FALLBACK_SERIES["jp_10y"], "JP 10Y")
    if ten_year_legs["in_10y"] is None:
        ten_year_legs["in_10y"] = _fred_leg(fred, FRED_FALLBACK_SERIES["in_10y"], "IN 10Y")

    # Best effort for EURUSD: if dedicated 2Y is unavailable, use 10Y as tenor proxy.
    if two_year_legs["de_2y"] is None and ten_year_legs["de_10y"] is not None:
        two_year_legs["de_2y"] = ten_year_legs["de_10y"]

    # Best effort for USDINR: if dedicated 2Y is unavailable, use 10Y as tenor proxy.
    if two_year_legs["in_2y"] is None and ten_year_legs["in_10y"] is not None:
        two_year_legs["in_2y"] = ten_year_legs["in_10y"]

    us_2y = two_year_legs["us_2y"]
    if us_2y is None:
        logger.warning("US yield leg missing after fallback; returning empty yields list")
        return []

    return [
        RawYields(
            date=today,
            us_2y=us_2y,
            de_2y=two_year_legs["de_2y"],
            jp_2y=two_year_legs["jp_2y"],
            in_2y=two_year_legs["in_2y"],
            us_10y=ten_year_legs["us_10y"],
            de_10y=ten_year_legs["de_10y"],
            jp_10y=ten_year_legs["jp_10y"],
            in_10y=ten_year_legs["in_10y"],
        )
    ]
