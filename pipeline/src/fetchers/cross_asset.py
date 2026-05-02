from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from typing import Any

import aiohttp
import pandas as pd
import yfinance as yf

from src.db import writer
from src.fetchers.async_engine import AsyncFetcher
from src.types import spot_tickers_from_universe

logger = logging.getLogger(__name__)


def _yf_row_float(row: Any, attr: str) -> float | None:
    val = getattr(row, attr, None)
    return float(val) if val is not None and pd.notna(val) else None


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
    gold: float | None = None
    copper: float | None = None
    stoxx: float | None = None
    try:
        df = yf.download("GC=F", period=period, auto_adjust=True, progress=False)
        gold, _ = _latest_and_change_1d(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gold fetch failed: %s", exc)
    try:
        df = yf.download("HG=F", period=period, auto_adjust=True, progress=False)
        copper, _ = _latest_and_change_1d(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Copper fetch failed: %s", exc)
    try:
        df = yf.download("^STOXX50E", period=period, auto_adjust=True, progress=False)
        stoxx, _ = _latest_and_change_1d(df)
    except Exception as exc:  # noqa: BLE001
        logger.warning("STOXX50E fetch failed: %s", exc)
    return {
        "vix": vix,
        "dxy": dxy,
        "oil": oil,
        "oil_change_1d": oil_change_1d,
        "gold": gold,
        "copper": copper,
        "stoxx": stoxx,
    }


async def fetch_cross_asset_async(
    session: aiohttp.ClientSession,
    fetcher: AsyncFetcher,
    *,
    lookback_days: int = 5,
) -> dict[str, float | None]:
    """VIX / DXY / WTI concurrently under the shared semaphore (yfinance in threads)."""

    _ = session
    period = f"{max(lookback_days, 1)}d"
    t_batch = time.perf_counter()

    async def _one(label: str, ticker: str) -> tuple[str, float | None]:
        t0 = time.perf_counter()
        async with fetcher.semaphore:

            def _latest() -> float | None:
                try:
                    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
                    latest, _ = _latest_and_change_1d(df)
                    return latest
                except Exception as exc:  # noqa: BLE001
                    logger.warning("%s (%s) async fetch failed: %s", label, ticker, exc)
                    return None

            val = await asyncio.to_thread(_latest)
        logger.info(
            "fetch_cross_asset_async label=%s ticker=%s in %.3fs",
            label,
            ticker,
            time.perf_counter() - t0,
        )
        return label, val

    vix_t, dxy_t, oil_t, gold_t, copper_t, stoxx_t = await asyncio.gather(
        _one("vix", "^VIX"),
        _one("dxy", "DX-Y.NYB"),
        _one("oil", "CL=F"),
        _one("gold", "GC=F"),
        _one("copper", "HG=F"),
        _one("stoxx", "^STOXX50E"),
    )
    out: dict[str, float | None] = {
        vix_t[0]: vix_t[1],
        dxy_t[0]: dxy_t[1],
        oil_t[0]: oil_t[1],
        gold_t[0]: gold_t[1],
        copper_t[0]: copper_t[1],
        stoxx_t[0]: stoxx_t[1],
    }
    logger.info(
        "fetch_cross_asset_async batch wall=%.3fs snapshot=%s",
        time.perf_counter() - t_batch,
        out,
    )
    return out


def fetch_max_history(pair: str, years_back: int = 30) -> int:
    """Fetch deep daily OHLCV history for a pair and upsert into historical_prices.

    This is intended as a one-time backfill helper for 20y-50y archives.
    Returns the number of rows written.
    """
    ticker = spot_tickers_from_universe().get(pair)
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
                "open": _yf_row_float(row, "Open"),
                "high": _yf_row_float(row, "High"),
                "low": _yf_row_float(row, "Low"),
                "close": _yf_row_float(row, "Close"),
                "volume": _yf_row_float(row, "Volume"),
            }
        )

    if not rows:
        return 0

    chunk = 1000
    for idx in range(0, len(rows), chunk):
        writer.write_historical_prices(rows[idx : idx + chunk])
    logger.info("Historical backfill complete pair=%s rows=%s", pair, len(rows))
    return len(rows)
