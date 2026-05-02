"""Yield legs fetched from yfinance with FRED fallbacks."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any
from urllib.parse import quote

import aiohttp
from fredapi import Fred

from src.fetchers.async_engine import AsyncFetcher

logger = logging.getLogger(__name__)


def _yfinance() -> Any:
    import yfinance as yf

    return yf


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

# Yahoo US Treasury proxies → FRED series (FRED-first in async path).
_US_YAHOO_TO_FRED: dict[str, str] = {
    "^UST2Y": "DGS2",
    "^TNX": "DGS10",
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
        history = _yfinance().Ticker(ticker).history(period=period)
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


def fetch_legacy_10y_legs(lookback_days: int = 5) -> dict[str, float | None]:
    """US/DE/JP/IN 10Y legs only (FRED-primary US; Yahoo + FRED fallbacks for others)."""

    window_days = max(lookback_days, 1)
    period = f"{window_days}d"
    fred_key = os.environ.get("FRED_API_KEY")
    fred = Fred(api_key=fred_key) if fred_key else None
    if fred is None:
        logger.warning("FRED_API_KEY not set — US 10Y will use yfinance only")

    yf_10y_non_us = {k: v for k, v in YF_10Y_TICKERS.items() if k != "us_10y"}
    ten_year_legs = _fetch_yf_legs(yf_10y_non_us, period)

    us_10y = _fred_leg(fred, FRED_FALLBACK_SERIES["us_10y"], "US 10Y")
    if us_10y is None:
        us_10y = _yf_leg(YF_10Y_TICKERS["us_10y"], "us_10y", period)
    if us_10y is None:
        logger.warning("US 10Y unavailable in both FRED and yfinance")
    ten_year_legs["us_10y"] = us_10y
    if ten_year_legs["de_10y"] is None:
        ten_year_legs["de_10y"] = _fred_leg(fred, FRED_FALLBACK_SERIES["de_10y"], "DE 10Y")
    if ten_year_legs["jp_10y"] is None:
        ten_year_legs["jp_10y"] = _fred_leg(fred, FRED_FALLBACK_SERIES["jp_10y"], "JP 10Y")
    if ten_year_legs["in_10y"] is None:
        ten_year_legs["in_10y"] = _fred_leg(fred, FRED_FALLBACK_SERIES["in_10y"], "IN 10Y")
    return ten_year_legs


def fetch_yields(lookback_days: int = 5) -> dict[str, float | None]:
    """Legacy sync yield fetch; flat map with keys like ``us_2y``, ``us_10y``."""

    window_days = max(lookback_days, 1)
    period = f"{window_days}d"
    fred_key = os.environ.get("FRED_API_KEY")
    fred = Fred(api_key=fred_key) if fred_key else None
    if fred is None:
        logger.warning("FRED_API_KEY not set — US yields will use yfinance only")

    yf_2y_non_us = {k: v for k, v in YF_2Y_TICKERS.items() if k != "us_2y"}
    two_year_legs = _fetch_yf_legs(yf_2y_non_us, period)
    time.sleep(1.0)
    ten_year_legs = fetch_legacy_10y_legs(window_days)

    us_2y = _fred_leg(fred, FRED_FALLBACK_SERIES["us_2y"], "US 2Y")
    if us_2y is None:
        us_2y = _yf_leg(YF_2Y_TICKERS["us_2y"], "us_2y", period)
    if us_2y is None:
        logger.warning("US 2Y unavailable in both FRED and yfinance")
    two_year_legs["us_2y"] = us_2y

    # Best effort for EURUSD: if dedicated 2Y is unavailable, use 10Y as tenor proxy.
    if two_year_legs["de_2y"] is None and ten_year_legs["de_10y"] is not None:
        two_year_legs["de_2y"] = ten_year_legs["de_10y"]

    # Best effort for USDINR: if dedicated 2Y is unavailable, use 10Y as tenor proxy.
    if two_year_legs["in_2y"] is None and ten_year_legs["in_10y"] is not None:
        two_year_legs["in_2y"] = ten_year_legs["in_10y"]

    if us_2y is None:
        logger.warning("US yield leg missing after fallback; returning empty yield map")
        return {}

    out: dict[str, float | None] = {}
    out.update(two_year_legs)
    out.update(ten_year_legs)
    bei = _fred_leg(fred, ("T10YIE",), "US 10Y breakeven T10YIE")
    if bei is not None:
        out["T10YIE"] = bei
    return out


def _is_yahoo_yield_symbol(symbol: str) -> bool:
    return "=" in symbol or symbol.startswith("^")


def _unique_yield_ids(universe: dict[str, Any]) -> list[str]:
    """Collect ordered unique ``yield_base`` / ``yield_quote`` symbols from FX universe rows."""

    seen: set[str] = set()
    ordered: list[str] = []
    for _sym, meta in universe.items():
        if not isinstance(meta, dict) or meta.get("class") != "FX":
            continue
        tickers = meta.get("tickers") or {}
        for key in ("yield_base", "yield_quote"):
            tid = tickers.get(key)
            if isinstance(tid, str) and tid not in seen:
                seen.add(tid)
                ordered.append(tid)
    return ordered


async def _yahoo_yield_latest_async(
    ticker: str,
    period: str,
    fetcher: AsyncFetcher,
) -> float | None:
    t0 = time.perf_counter()

    def _close() -> float | None:
        history = _yfinance().Ticker(ticker).history(period=period)
        if history is None or history.empty or "Close" not in history:
            logger.warning("yfinance async %s returned empty history", ticker)
            return None
        closes = history["Close"].dropna()
        if closes.empty:
            logger.warning("yfinance async %s returned empty close series", ticker)
            return None
        return float(closes.iloc[-1])

    async with fetcher.semaphore:
        try:
            out = await asyncio.to_thread(_close)
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance async %s failed: %s", ticker, exc)
            out = None
    logger.info(
        "fetch_yields_async yahoo ticker=%s value=%s in %.3fs",
        ticker,
        out,
        time.perf_counter() - t0,
    )
    return out


async def _fred_latest_async(
    series_id: str,
    session: aiohttp.ClientSession,
    fetcher: AsyncFetcher,
) -> float | None:
    t0 = time.perf_counter()
    key = os.environ.get("FRED_API_KEY")
    if not key:
        logger.warning("FRED_API_KEY not set — async leg %s skipped", series_id)
        logger.info(
            "fetch_yields_async FRED series_id=%s skipped in %.3fs",
            series_id,
            time.perf_counter() - t0,
        )
        return None
    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={quote(series_id, safe='')}&api_key={key}&file_type=json"
        "&limit=1&sort_order=desc"
    )
    status, body = await fetcher.fetch_with_retry(url, session)
    result: float | None = None
    if status != 200 or body is None:
        logger.warning("FRED async %s HTTP status=%s", series_id, status)
    else:
        try:
            payload = json.loads(body.decode("utf-8"))
            obs = payload.get("observations") or []
            if obs:
                val = obs[0].get("value")
                if val not in (None, ".", ""):
                    result = float(val)
        except Exception as exc:  # noqa: BLE001
            logger.warning("FRED async parse %s failed: %s", series_id, exc)
    logger.info(
        "fetch_yields_async FRED series_id=%s value=%s in %.3fs",
        series_id,
        result,
        time.perf_counter() - t0,
    )
    return result


async def _fetch_yield_leg_async(
    series_id: str,
    session: aiohttp.ClientSession,
    fetcher: AsyncFetcher,
    period: str,
) -> tuple[str, float | None]:
    fred_override = _US_YAHOO_TO_FRED.get(series_id)
    if fred_override is not None:
        val = await _fred_latest_async(fred_override, session, fetcher)
        if val is None:
            val = await _yahoo_yield_latest_async(series_id, period, fetcher)
        return series_id, val
    if _is_yahoo_yield_symbol(series_id):
        val = await _yahoo_yield_latest_async(series_id, period, fetcher)
    else:
        val = await _fred_latest_async(series_id, session, fetcher)
    return series_id, val


async def fetch_yields_async(
    universe: dict[str, Any],
    session: aiohttp.ClientSession,
    *,
    lookback_days: int = 5,
    fetcher: AsyncFetcher | None = None,
) -> dict[str, float | None]:
    """Resolve yield legs from ``universe``; normalized in-memory map only (no Supabase)."""

    window_days = max(lookback_days, 1)
    period = f"{window_days}d"
    gate = fetcher if fetcher is not None else AsyncFetcher()
    ids = _unique_yield_ids(universe)
    t_batch = time.perf_counter()
    results = await asyncio.gather(
        *[_fetch_yield_leg_async(sid, session, gate, period) for sid in ids],
        return_exceptions=True,
    )
    out: dict[str, float | None] = {}
    for res in results:
        if isinstance(res, BaseException):
            logger.error("fetch_yields_async leg task failed: %s", res)
            continue
        key, val = res
        out[key] = val
    logger.info(
        "fetch_yields_async unique_legs=%s ok=%s wall=%.3fs",
        len(ids),
        len(out),
        time.perf_counter() - t_batch,
    )
    return out


async def fetch_t10yie_breakeven_async(
    session: aiohttp.ClientSession,
    fetcher: AsyncFetcher,
) -> float | None:
    """FRED T10YIE — 10-year breakeven inflation (%), for real-rate adjustment."""

    return await _fred_latest_async("T10YIE", session, fetcher)
