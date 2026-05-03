"""FX spot OHLC: Alpha Vantage FX_DAILY (primary) with yfinance fallback."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import date, timedelta
from typing import Any, cast

import aiohttp
import numpy as np
import pandas as pd
import requests

from src.fetchers.async_engine import AsyncFetcher
from src.types import SpotBar, alphavantage_fx_legs_from_pair, spot_tickers_from_universe

logger = logging.getLogger(__name__)

_AV_BASE = "https://www.alphavantage.co/query"
_AV_REQUEST_TIMEOUT_S = 75.0


def _yfinance() -> Any:
    import yfinance as yf

    return yf


def _alphavantage_payload_suggests_stop(data: dict[str, Any]) -> bool:
    """True when AV returns throttle / premium / error messaging (no usable series)."""

    if "Error Message" in data:
        return True
    note = data.get("Note")
    if isinstance(note, str) and note.strip():
        return True
    info = data.get("Information")
    if isinstance(info, str) and info.strip():
        return True
    return False


def _trim_lookback(bars: list[SpotBar], lookback_days: int) -> list[SpotBar]:
    if not bars or lookback_days <= 0:
        return bars
    ordered = sorted(bars, key=lambda b: b.date)
    last = ordered[-1].date
    start = last - timedelta(days=lookback_days)
    return [b for b in ordered if b.date >= start]


def _parse_av_fx_daily(pair: str, data: dict[str, Any]) -> list[SpotBar]:
    ts = data.get("Time Series FX (Daily)")
    if not isinstance(ts, dict) or not ts:
        return []
    bars: list[SpotBar] = []
    for day_s, row in ts.items():
        if not isinstance(row, dict):
            continue
        try:
            d = date.fromisoformat(str(day_s)[:10])
            o = float(str(row.get("1. open", "nan")))
            h = float(str(row.get("2. high", "nan")))
            lo = float(str(row.get("3. low", "nan")))
            c = float(str(row.get("4. close", "nan")))
        except (TypeError, ValueError):
            continue
        if any(np.isnan(v) for v in (o, h, lo, c)):
            continue
        bars.append(
            SpotBar(date=d, pair=pair, open=o, high=h, low=lo, close=c),
        )
    bars.sort(key=lambda b: b.date)
    return bars


def _alphavantage_fx_daily_request(
    pair: str,
    *,
    api_key: str,
    lookback_days: int,
) -> tuple[list[SpotBar], bool]:
    """GET FX_DAILY; returns (bars, stop_av_chain)."""

    try:
        from_sym, to_sym = alphavantage_fx_legs_from_pair(pair)
    except ValueError as exc:
        logger.warning("Alpha Vantage skip %s: %s", pair, exc)
        return [], False

    params = {
        "function": "FX_DAILY",
        "from_symbol": from_sym,
        "to_symbol": to_sym,
        "outputsize": "compact",
        "apikey": api_key,
    }
    try:
        resp = requests.get(_AV_BASE, params=params, timeout=_AV_REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        raw: Any = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alpha Vantage HTTP/json failed pair=%s: %s", pair, exc)
        return [], False

    if not isinstance(raw, dict):
        logger.warning("Alpha Vantage non-object JSON pair=%s", pair)
        return [], False

    if _alphavantage_payload_suggests_stop(raw) and "Time Series FX (Daily)" not in raw:
        logger.warning(
            "Alpha Vantage throttle/limit pair=%s; yfinance fallback for rest",
            pair,
        )
        return [], True

    bars = _parse_av_fx_daily(pair, raw)
    bars = _trim_lookback(bars, lookback_days)
    if bars:
        logger.info(
            "Alpha Vantage FX_DAILY pair=%s legs=%s/%s bars=%s",
            pair,
            from_sym,
            to_sym,
            len(bars),
        )
    return bars, False


def fetch_fx_spot_alphavantage(pair: str, *, lookback_days: int = 30) -> list[SpotBar]:
    """Fetch FX daily OHLC from Alpha Vantage ``FX_DAILY`` (uses ``ALPHAVANTAGE_API_KEY``)."""

    api_key = (os.environ.get("ALPHAVANTAGE_API_KEY") or "").strip()
    if not api_key:
        return []
    bars, _ = _alphavantage_fx_daily_request(pair, api_key=api_key, lookback_days=lookback_days)
    return bars


def _fetch_fx_spot_yfinance_batch(
    yf_map: dict[str, str],
    pairs_subset: list[str],
    lookback_days: int,
) -> dict[str, list[SpotBar]]:
    """Batch yfinance download for a subset of pairs (Yahoo tickers from ``yf_map``)."""

    out: dict[str, list[SpotBar]] = {p: [] for p in pairs_subset}
    if not pairs_subset:
        return out
    tickers = [yf_map[p] for p in pairs_subset]
    ticker_to_pair = {yf_map[p]: p for p in pairs_subset}
    period = f"{lookback_days}d"
    try:
        raw = _yfinance().download(
            tickers,
            period=period,
            auto_adjust=True,
            group_by="ticker",
            progress=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance FX batch download failed: %s", exc)
        return out

    if raw is None or raw.empty:
        logger.warning("yfinance FX download returned empty frame")
        return out

    for ticker in tickers:
        pair = ticker_to_pair.get(ticker)
        if pair is None:
            continue
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                sub = raw[ticker]
            elif len(tickers) == 1:
                sub = raw
            else:
                sub = raw
            if sub.empty:
                continue
            for idx, row in sub.iterrows():
                d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
                o = row.get("Open", np.nan)
                h = row.get("High", np.nan)
                lo = row.get("Low", np.nan)
                c = row.get("Close", np.nan)
                if any(pd.isna(v) for v in (o, h, lo, c)):
                    continue
                out[pair].append(
                    SpotBar(
                        date=d,
                        pair=pair,
                        open=float(o),
                        high=float(h),
                        low=float(lo),
                        close=float(c),
                    ),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("parse failed for %s: %s", ticker, exc)

    for pair in out:
        out[pair].sort(key=lambda b: b.date)
    return out


def fetch_fx_spot(lookback_days: int = 30) -> dict[str, list[SpotBar]]:
    """Download spot history for all pairs; Alpha Vantage first, then yfinance for gaps."""

    yf_map = spot_tickers_from_universe()
    out: dict[str, list[SpotBar]] = {p: [] for p in yf_map}
    pairs = list(yf_map.keys())
    api_key = (os.environ.get("ALPHAVANTAGE_API_KEY") or "").strip()

    if api_key:
        av_stop = False
        for i, pair in enumerate(pairs):
            if av_stop:
                break
            if i > 0:
                time.sleep(12)
            bars, stop = _alphavantage_fx_daily_request(
                pair,
                api_key=api_key,
                lookback_days=lookback_days,
            )
            if bars:
                out[pair] = bars
            if stop:
                av_stop = True

    missing = [p for p in pairs if not out.get(p)]
    if missing:
        yf_part = _fetch_fx_spot_yfinance_batch(yf_map, missing, lookback_days)
        for p in missing:
            if yf_part.get(p):
                out[p] = yf_part[p]

    return out


def _bars_from_yf_frame(raw: pd.DataFrame, pair: str, ticker: str) -> list[SpotBar]:
    bars: list[SpotBar] = []
    if raw is None or raw.empty:
        return bars
    try:
        for idx, row in raw.iterrows():
            d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
            o = row.get("Open", np.nan)
            h = row.get("High", np.nan)
            lo = row.get("Low", np.nan)
            c = row.get("Close", np.nan)
            if any(pd.isna(v) for v in (o, h, lo, c)):
                continue
            bars.append(
                SpotBar(
                    date=d,
                    pair=pair,
                    open=float(o),
                    high=float(h),
                    low=float(lo),
                    close=float(c),
                ),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("parse failed for %s (%s): %s", pair, ticker, exc)
    bars.sort(key=lambda b: b.date)
    return bars


async def _fetch_one_spot_async(
    pair: str,
    ticker: str,
    period: str,
    fetcher: AsyncFetcher,
) -> tuple[str, list[SpotBar]]:
    t0 = time.perf_counter()

    def _download() -> pd.DataFrame:
        return cast(
            pd.DataFrame,
            _yfinance().download(ticker, period=period, auto_adjust=True, progress=False),
        )

    async with fetcher.semaphore:
        try:
            raw = await asyncio.to_thread(_download)
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance async download failed %s %s: %s", pair, ticker, exc)
            logger.info(
                "fetch_fx_spot_async pair=%s ticker=%s completed in %.3fs (error)",
                pair,
                ticker,
                time.perf_counter() - t0,
            )
            return pair, []

    frame = raw
    if isinstance(frame.columns, pd.MultiIndex):
        if ticker in frame.columns.get_level_values(0):
            frame = frame[ticker]
        else:
            logger.warning("multiindex frame missing ticker %s for %s", ticker, pair)
            frame = pd.DataFrame()

    bars = _bars_from_yf_frame(frame, pair, ticker)
    logger.info(
        "fetch_fx_spot_async pair=%s ticker=%s bars=%s in %.3fs",
        pair,
        ticker,
        len(bars),
        time.perf_counter() - t0,
    )
    return pair, bars


async def fetch_fx_spot_async(
    universe: dict[str, Any],
    session: aiohttp.ClientSession,
    *,
    lookback_days: int = 30,
    fetcher: AsyncFetcher | None = None,
) -> dict[str, list[SpotBar]]:
    """Spot per instrument: Alpha Vantage (sequential, rate-limited), then yfinance."""

    _ = session  # reserved for future HTTP-backed spot providers
    period = f"{max(lookback_days, 1)}d"
    gate = fetcher if fetcher is not None else AsyncFetcher()
    tasks: list[tuple[str, str]] = []
    for sym, meta in universe.items():
        if not isinstance(meta, dict) or meta.get("class") != "FX":
            continue
        tickers = meta.get("tickers") or {}
        st_raw = tickers.get("spot_ticker")
        raw_spot = st_raw if isinstance(st_raw, str) else tickers.get("spot")
        spot_t = raw_spot if isinstance(raw_spot, str) else None
        if not spot_t:
            logger.warning("fetch_fx_spot_async skip %s: missing spot ticker", sym)
            continue
        tasks.append((sym, spot_t))

    out: dict[str, list[SpotBar]] = {}
    api_key = (os.environ.get("ALPHAVANTAGE_API_KEY") or "").strip()

    if api_key:
        av_stop = False
        for i, (pair, _yf_ticker) in enumerate(tasks):
            if av_stop:
                break
            if i > 0:
                await asyncio.sleep(12)

            def _av_sync() -> tuple[list[SpotBar], bool]:
                return _alphavantage_fx_daily_request(
                    pair,
                    api_key=api_key,
                    lookback_days=lookback_days,
                )

            bars, stop = await asyncio.to_thread(_av_sync)
            if bars:
                out[pair] = bars
            if stop:
                av_stop = True

    missing_tasks = [(p, t) for p, t in tasks if not out.get(p)]
    t_batch = time.perf_counter()
    if missing_tasks:
        results = await asyncio.gather(
            *[_fetch_one_spot_async(pair, t, period, gate) for pair, t in missing_tasks],
            return_exceptions=True,
        )
        for res in results:
            if isinstance(res, BaseException):
                logger.error("fetch_fx_spot_async task failed: %s", res)
                continue
            pair, bars = res
            out[pair] = bars

    logger.info(
        "fetch_fx_spot_async batch pairs=%s total_wall=%.3fs",
        len(out),
        time.perf_counter() - t_batch,
    )
    return out
