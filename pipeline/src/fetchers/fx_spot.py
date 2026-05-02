"""yfinance FX spot OHLC for configured pairs."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from typing import Any, cast

import aiohttp
import numpy as np
import pandas as pd

from src.fetchers.async_engine import AsyncFetcher
from src.types import SpotBar, spot_tickers_from_universe

logger = logging.getLogger(__name__)


def _yfinance() -> Any:
    import yfinance as yf

    return yf


def fetch_fx_spot(lookback_days: int = 30) -> dict[str, list[SpotBar]]:
    """Download spot history for all pairs; returns bars sorted by date ascending."""
    yf_map = spot_tickers_from_universe()
    ticker_to_pair = {v: k for k, v in yf_map.items()}
    tickers = list(yf_map.values())
    period = f"{lookback_days}d"
    out: dict[str, list[SpotBar]] = {p: [] for p in yf_map}
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
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("parse failed for %s: %s", ticker, exc)

    for pair in out:
        out[pair].sort(key=lambda b: b.date)
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
                )
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
    """Concurrent spot history per universe instrument; returns normalized in-memory bars only."""

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

    t_batch = time.perf_counter()
    results = await asyncio.gather(
        *[_fetch_one_spot_async(pair, t, period, gate) for pair, t in tasks],
        return_exceptions=True,
    )
    out: dict[str, list[SpotBar]] = {}
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
