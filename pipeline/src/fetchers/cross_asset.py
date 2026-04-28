from __future__ import annotations

import logging
from datetime import date
from typing import Any

import pandas as pd
import yfinance as yf

from src.db import writer
from src.types import YF_TICKERS

logger = logging.getLogger(__name__)


def _latest_and_change_1d(df: pd.DataFrame) -> tuple[float | None, float | None]:
    if df.empty or "Close" not in df:
        return None, None
    close_values = df["Close"]
    close_series = (
        close_values.iloc[:, 0] if isinstance(close_values, pd.DataFrame) else close_values
    )
    close_series = close_series.dropna()
    if close_series.empty:
        return None, None
    latest = float(close_series.iloc[-1])
    if len(close_series) < 2:
        return latest, None
    change_1d = float(close_series.iloc[-1] - close_series.iloc[-2])
    return latest, change_1d


def fetch_cross_asset(lookback_days: int = 5) -> dict[str, float | None]:
    period = f"{lookback_days}d"
    vix: float | None = None
    dxy: float | None = None
    oil: float | None = None
    oil_change_1d: float | None = None
    try:
        df = yf.download("^VIX", period=period, auto_adjust=True, progress=False)
        vix, _ = _latest_and_change_1d(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("VIX fetch failed: %s", exc)
    try:
        df = yf.download("DX-Y.NYB", period=period, auto_adjust=True, progress=False)
        dxy, _ = _latest_and_change_1d(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DXY fetch failed: %s", exc)
    try:
        df = yf.download("CL=F", period=period, auto_adjust=True, progress=False)
        oil, oil_change_1d = _latest_and_change_1d(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Oil fetch failed: %s", exc)
    return {
        "vix": vix,
        "dxy": dxy,
        "oil": oil,
        "oil_change_1d": oil_change_1d,
    }


def fetch_max_history(pair: str, years_back: int = 30) -> int:
    """Fetch deep daily OHLCV history for a pair and upsert into historical_prices.

    This is intended as a one-time backfill helper for 20y-50y archives.
    Returns the number of rows written.
    """
    ticker = YF_TICKERS.get(pair)
    if not ticker:
        logger.warning("No yfinance ticker configured for pair=%s", pair)
        return 0

    start_year = max(1970, date.today().year - years_back)
    start_date = f"{start_year}-01-01"
    try:
        df = yf.download(ticker, start=start_date, auto_adjust=False, progress=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Deep history fetch failed for %s: %s", pair, exc)
        return 0

    if df.empty:
        logger.warning("No deep history rows returned for %s", pair)
        return 0

    normalized = df.reset_index().rename(columns={"Date": "date"})
    rows: list[dict[str, Any]] = []
    for row in normalized.itertuples(index=False):
        d = getattr(row, "date", None)
        if d is None:
            continue
        rows.append(
            {
                "date": str(d)[:10],
                "pair": pair,
                "open": float(getattr(row, "Open", 0.0)) if pd.notna(getattr(row, "Open", None)) else None,
                "high": float(getattr(row, "High", 0.0)) if pd.notna(getattr(row, "High", None)) else None,
                "low": float(getattr(row, "Low", 0.0)) if pd.notna(getattr(row, "Low", None)) else None,
                "close": float(getattr(row, "Close", 0.0)) if pd.notna(getattr(row, "Close", None)) else None,
                "volume": float(getattr(row, "Volume", 0.0)) if pd.notna(getattr(row, "Volume", None)) else None,
            }
        )

    if not rows:
        return 0

    chunk = 1000
    for idx in range(0, len(rows), chunk):
        writer.write_historical_prices(rows[idx : idx + chunk])
    logger.info("Historical backfill complete pair=%s rows=%s", pair, len(rows))
    return len(rows)
