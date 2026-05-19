from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from typing import Any

import aiohttp
import pandas as pd

from src.db import writer
from src.fetchers.async_engine import AsyncFetcher
from src.types import spot_tickers_from_universe

logger = logging.getLogger(__name__)


def _yfinance() -> Any:
    import yfinance as yf

    return yf


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


def _close_history(df: pd.DataFrame, *, tail: int | None = None) -> list[float]:
    """Close prints ordered oldest → newest (optional trailing ``tail`` points)."""

    if df.empty or "Close" not in df:
        return []
    close_values = df["Close"]
    close_series = (
        close_values.iloc[:, 0] if isinstance(close_values, pd.DataFrame) else close_values
    )
    close_series = close_series.dropna()
    if close_series.empty:
        return []
    arr = [float(x) for x in close_series.astype(float).tolist() if pd.notna(x)]
    if tail is not None and len(arr) > tail:
        return arr[-tail:]
    return arr


def fetch_cross_asset(
    lookback_days: int = 5,
    *,
    percentile_lookback: int | None = None,
) -> dict[str, Any]:
    """Fetch cross-asset levels from yfinance.

    Snapshot fields match prior callers. Optional ``percentile_lookback`` widens the
    yfinance window and attaches ``hist`` (60d-ranked inputs need ~65+ prints).

    **Iron ore:** yfinance lacks a robust front-month ore contract here; ``iron_ore`` is filled
    from **HG=F (COMEX copper)** — same China/IP industrial-beta proxy as documented in-house.
    Copper and iron ore snapshot/hist values are duplicated from a single HG=F download.
    """
    hist_tail = percentile_lookback
    calendar_days = lookback_days
    if percentile_lookback is not None:
        calendar_days = max(lookback_days, percentile_lookback + 25, 70)
    period = f"{max(calendar_days, 1)}d"
    tail_arg: int | None = hist_tail if hist_tail is not None else None

    vix: float | None = None
    dxy: float | None = None
    oil: float | None = None
    oil_change_1d: float | None = None
    gold: float | None = None
    copper: float | None = None
    iron_ore: float | None = None  # HG=F copper proxy — see docstring.
    stoxx: float | None = None
    hist_vix: list[float] = []
    hist_dxy: list[float] = []
    hist_oil: list[float] = []
    hist_gold: list[float] = []
    hist_copper: list[float] = []
    hist_stoxx: list[float] = []

    try:
        df = _yfinance().download("^VIX", period=period, auto_adjust=True, progress=False)
        vix, _ = _latest_and_change_1d(df)
        if tail_arg:
            hist_vix = _close_history(df, tail=tail_arg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("VIX fetch failed: %s", exc)
    try:
        df = _yfinance().download("DX-Y.NYB", period=period, auto_adjust=True, progress=False)
        dxy, _ = _latest_and_change_1d(df)
        if tail_arg:
            hist_dxy = _close_history(df, tail=tail_arg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DXY fetch failed: %s", exc)
    try:
        df = _yfinance().download("CL=F", period=period, auto_adjust=True, progress=False)
        oil, oil_change_1d = _latest_and_change_1d(df)
        if tail_arg:
            hist_oil = _close_history(df, tail=tail_arg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Oil fetch failed: %s", exc)
    try:
        df = _yfinance().download("GC=F", period=period, auto_adjust=True, progress=False)
        gold, _ = _latest_and_change_1d(df)
        if tail_arg:
            hist_gold = _close_history(df, tail=tail_arg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gold fetch failed: %s", exc)
    try:
        # Single HG=F download feeds both industrial-metal slots (iron ore proxy = copper).
        df = _yfinance().download("HG=F", period=period, auto_adjust=True, progress=False)
        copper, _ = _latest_and_change_1d(df)
        iron_ore = copper
        if tail_arg:
            hist_copper = _close_history(df, tail=tail_arg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Copper / iron ore (HG=F) fetch failed: %s", exc)
    try:
        df = _yfinance().download("^STOXX50E", period=period, auto_adjust=True, progress=False)
        stoxx, _ = _latest_and_change_1d(df)
        if tail_arg:
            hist_stoxx = _close_history(df, tail=tail_arg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("STOXX50E fetch failed: %s", exc)

    out: dict[str, Any] = {
        "vix": vix,
        "dxy": dxy,
        "oil": oil,
        "oil_change_1d": oil_change_1d,
        "gold": gold,
        "copper": copper,
        "iron_ore": iron_ore,
        "stoxx": stoxx,
    }
    if hist_tail is not None:
        # iron_ore mirrors copper (HG=F ore proxy — same series).
        hist = {
            "vix": hist_vix,
            "dxy": hist_dxy,
            "oil": hist_oil,
            "gold": hist_gold,
            "copper": hist_copper,
            "iron_ore": list(hist_copper),
            "stoxx": hist_stoxx,
        }
        out["hist"] = hist
    return out


async def fetch_cross_asset_async(
    session: aiohttp.ClientSession,
    fetcher: AsyncFetcher,
    *,
    lookback_days: int = 5,
    percentile_lookback: int | None = None,
) -> dict[str, Any]:
    """VIX / DXY / WTI / metals / STOXX concurrently (yfinance in threads).

    ``iron_ore`` is COMEX HG=F (copper) as an industrial ore proxy — see sync fetcher docstring.
    Pass ``percentile_lookback`` to attach trailing ``hist`` series for ``src.signals.special``.
    """

    _ = session
    hist_tail = percentile_lookback
    calendar_days = lookback_days
    if percentile_lookback is not None:
        calendar_days = max(lookback_days, percentile_lookback + 25, 70)
    period = f"{max(calendar_days, 1)}d"
    tail_arg: int | None = hist_tail if hist_tail is not None else None
    t_batch = time.perf_counter()

    async def _one_hist(label: str, ticker: str) -> tuple[str, float | None, list[float]]:
        t0 = time.perf_counter()
        async with fetcher.semaphore:

            def _work() -> tuple[float | None, list[float]]:
                for attempt in range(1, 3):
                    try:
                        df = _yfinance().download(
                            ticker, period=period, auto_adjust=True, progress=False
                        )
                        latest, _ = _latest_and_change_1d(df)
                        hist_s = _close_history(df, tail=tail_arg) if tail_arg else []
                        if latest is not None:
                            return latest, hist_s
                        logger.warning(
                            "%s (%s) returned None on attempt %s", label, ticker, attempt
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "%s (%s) async fetch failed (attempt %s): %s",
                            label, ticker, attempt, exc,
                        )
                return None, []

            val, hist_s = await asyncio.to_thread(_work)
        logger.info(
            "fetch_cross_asset_async label=%s ticker=%s in %.3fs",
            label,
            ticker,
            time.perf_counter() - t0,
        )
        return label, val, hist_s

    vix_t, dxy_t, oil_t, gold_t, copper_t, stoxx_t = await asyncio.gather(
        _one_hist("vix", "^VIX"),
        _one_hist("dxy", "DX-Y.NYB"),
        _one_hist("oil", "CL=F"),
        _one_hist("gold", "GC=F"),
        _one_hist("copper", "HG=F"),
        _one_hist("stoxx", "^STOXX50E"),
    )
    out: dict[str, Any] = {
        vix_t[0]: vix_t[1],
        dxy_t[0]: dxy_t[1],
        oil_t[0]: oil_t[1],
        gold_t[0]: gold_t[1],
        copper_t[0]: copper_t[1],
        "iron_ore": copper_t[1],
        stoxx_t[0]: stoxx_t[1],
    }
    snapshot_vals = [v for k, v in out.items() if k != "iron_ore"]
    if all(v is None for v in snapshot_vals):
        raise RuntimeError(
            "fetch_cross_asset_async: all tickers returned None — "
            "likely network/yfinance failure"
        )
    if hist_tail is not None:
        out["hist"] = {
            "vix": vix_t[2],
            "dxy": dxy_t[2],
            "oil": oil_t[2],
            "gold": gold_t[2],
            "copper": copper_t[2],
            "iron_ore": list(copper_t[2]),
            "stoxx": stoxx_t[2],
        }
    logger.info(
        "fetch_cross_asset_async batch wall=%.3fs snapshot_keys=%s",
        time.perf_counter() - t_batch,
        [k for k in out if k != "hist"],
    )
    return out


def fetch_india_vix() -> float | None:
    """Fetch latest India VIX from NSE via yfinance.

    Returns VIX level, or None if unavailable.
    """
    try:
        history = _yfinance().Ticker("^INDIAVIX").history(period="5d")
        if history is None or history.empty or "Close" not in history:
            logger.warning("yfinance India VIX (^INDIAVIX) returned empty history")
            return None
        closes = history["Close"].dropna()
        if closes.empty:
            logger.warning("yfinance India VIX (^INDIAVIX) returned empty close series")
            return None
        return float(closes.iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance India VIX (^INDIAVIX) fetch failed: %s", exc)
        return None


def fetch_inr_forward_premium() -> float | None:
    """Fetch USD/INR 1-month forward premium.

    Returns annualized premium in percent, or None if unavailable.

    Formula: ((Forward - Spot) / Spot) * (12 / 1) * 100

    For MVP: attempts yfinance tickers and falls back to None.
    Documented limitation: reliable 1M forward requires NSE derivatives
    or RBI reference rate + OTC forward points.
    """
    try:
        yf = _yfinance()
        # Spot
        spot_hist = yf.Ticker("USDINR=X").history(period="5d")
        if spot_hist is None or spot_hist.empty or "Close" not in spot_hist:
            logger.warning("INR forward premium: spot unavailable")
            return None
        spot = float(spot_hist["Close"].dropna().iloc[-1])

        # Forward proxy — try common forward/futures tickers
        for fwd_ticker in ("USDINR=F", "INR=F"):
            try:
                fwd_hist = yf.Ticker(fwd_ticker).history(period="5d")
                if fwd_hist is None or fwd_hist.empty or "Close" not in fwd_hist:
                    continue
                fwd = float(fwd_hist["Close"].dropna().iloc[-1])
                premium = ((fwd - spot) / spot) * 12 * 100
                logger.info("INR forward premium (%s): %.4f%%", fwd_ticker, premium)
                return float(premium)
            except Exception:
                continue
    except Exception as exc:  # noqa: BLE001
        logger.warning("INR forward premium fetch failed: %s", exc)
    logger.warning("INR forward premium: forward data unavailable (MVP limitation)")
    return None


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
        df = _yfinance().download(ticker, start=start_date, auto_adjust=False, progress=False)
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
