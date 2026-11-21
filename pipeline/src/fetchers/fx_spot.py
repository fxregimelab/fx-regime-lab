"""FX spot OHLC: Polygon.io (primary) → Alpha Vantage (secondary) → yfinance (tertiary)."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import UTC, date, datetime, timedelta
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
_POLYGON_BASE = "https://api.polygon.io/v2/aggs/ticker"
_POLYGON_TIMEOUT_S = 30.0


def _yfinance() -> Any:
    import yfinance as yf

    return yf


# ---------------------------------------------------------------------------
# Polygon.io — primary FX spot source (P1-T4)
# ---------------------------------------------------------------------------


def _polygon_ticker(pair: str) -> str:
    """Convert ``EUR/USD`` → ``C:EURUSD`` for Polygon forex aggregates."""
    return f"C:{pair.replace('/', '')}"


def _retrieval_time(value: datetime | None) -> datetime:
    instant = value if value is not None else datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Retrieval time must include a timezone")
    return instant.astimezone(UTC)


def _valid_ohlc(open_: float, high: float, low: float, close: float) -> bool:
    return bool(
        all(np.isfinite(v) and v > 0 for v in (open_, high, low, close))
        and low <= min(open_, close) <= max(open_, close) <= high
    )


def _parse_polygon_aggs(
    pair: str, data: dict[str, Any], *, retrieved_at: datetime | None = None
) -> list[SpotBar]:
    """Preserve raw provider time; UTC date is a label, not a session claim."""
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return []
    instrument = _polygon_ticker(pair)
    if data.get("ticker") not in (None, instrument):
        return []
    receipt = _retrieval_time(retrieved_at)
    bars: list[SpotBar] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        ts_ms = row.get("t")
        if isinstance(ts_ms, bool) or not isinstance(ts_ms, int):
            continue
        if any(isinstance(row.get(k), bool) for k in ("o", "h", "l", "c", "v")):
            continue
        try:
            instant = datetime.fromtimestamp(ts_ms / 1000, UTC)
            open_, high, low, close = (float(row.get(k, "nan")) for k in ("o", "h", "l", "c"))
            volume = float(row.get("v", 0.0))
        except (TypeError, ValueError, OverflowError, OSError):
            continue
        if instant > receipt or not _valid_ohlc(open_, high, low, close):
            continue
        if not np.isfinite(volume) or volume < 0:
            continue
        metadata: dict[str, Any] = {
            "date_label_policy": "timestamp_utc_date", "raw_timestamp_ms": ts_ms,
        }
        for key, output in (("ticker", "response_ticker"), ("status", "response_status"),
                            ("request_id", "request_id"), ("adjusted", "adjusted")):
            value = data.get(key)
            if isinstance(value, (str, bool, int, float)):
                metadata[output] = value
        bars.append(SpotBar(
            date=instant.date(), pair=pair, open=open_, high=high, low=low,
            close=close, volume=volume, provider="polygon", instrument=instrument,
            retrieved_at=receipt, provider_timestamp=instant,
            provider_metadata=metadata, volume_source="polygon", volume_instrument=instrument,
        ))
    return sorted(bars, key=lambda bar: bar.date)


def fetch_fx_spot_polygon(
    pair: str,
    *,
    lookback_days: int = 30,
) -> list[SpotBar] | None:
    """Fetch FX daily OHLC from Polygon.io.

    Returns ``None`` when the API key is missing or the request fails
    (so the caller can fall back to the next source).
    """
    api_key = (os.environ.get("POLYGON_API_KEY") or "").strip()
    if not api_key:
        return None

    ticker = _polygon_ticker(pair)
    end = _retrieval_time(None).date()
    start = end - timedelta(days=lookback_days + 5)  # buffer for weekends
    url = (
        f"{_POLYGON_BASE}/{ticker}/range/1/day/"
        f"{start.isoformat()}/{end.isoformat()}"
    )
    try:
        resp = requests.get(
            url,
            params={"apiKey": api_key, "adjusted": "true"},
            timeout=_POLYGON_TIMEOUT_S,
        )
        receipt = _retrieval_time(None)
        resp.raise_for_status()
        raw: Any = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Polygon.io request failed for %s (%s)", pair, type(exc).__name__)
        return None

    if not isinstance(raw, dict):
        logger.warning("Polygon.io non-object JSON for %s", pair)
        return None

    status = raw.get("status")
    if status == "ERROR" or status == "NOT_FOUND":
        logger.warning("Polygon.io status=%s for %s", status, pair)
        return None

    bars = _parse_polygon_aggs(pair, raw, retrieved_at=receipt)
    if bars:
        logger.info("Polygon.io pair=%s bars=%s", pair, len(bars))
    return bars if bars else None


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


def _parse_av_fx_daily(
    pair: str, data: dict[str, Any], *, retrieved_at: datetime | None = None
) -> list[SpotBar]:
    series = data.get("Time Series FX (Daily)")
    if not isinstance(series, dict) or not series:
        return []
    receipt = _retrieval_time(retrieved_at)
    raw_meta = data.get("Meta Data")
    raw_meta = raw_meta if isinstance(raw_meta, dict) else {}
    metadata: dict[str, Any] = {"date_label_policy": "provider_date"}
    for key, output in (
        ("2. From Symbol", "from_symbol"), ("3. To Symbol", "to_symbol"),
        ("4. Last Refreshed", "last_refreshed"), ("6. Time Zone", "provider_timezone"),
    ):
        if isinstance(raw_meta.get(key), str):
            metadata[output] = raw_meta[key]
    base, quote = alphavantage_fx_legs_from_pair(pair)
    if metadata.get("from_symbol", base) != base or metadata.get("to_symbol", quote) != quote:
        return []
    bars: list[SpotBar] = []
    for day_s, row in series.items():
        if not isinstance(day_s, str) or not isinstance(row, dict):
            continue
        if any(isinstance(row.get(k), bool) for k in ("1. open", "2. high", "3. low", "4. close")):
            continue
        try:
            day = date.fromisoformat(day_s)
            if day.isoformat() != day_s:
                continue
            open_, high, low, close = (float(row.get(k, "nan")) for k in (
                "1. open", "2. high", "3. low", "4. close"))
        except (TypeError, ValueError):
            continue
        if not _valid_ohlc(open_, high, low, close):
            continue
        bars.append(SpotBar(
            date=day, pair=pair, open=open_, high=high, low=low, close=close,
            provider="alphavantage", instrument=f"{base}/{quote}", retrieved_at=receipt,
            session_timezone=metadata.get("provider_timezone"), provider_metadata=dict(metadata),
        ))
    return sorted(bars, key=lambda bar: bar.date)


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
        receipt = _retrieval_time(None)
        resp.raise_for_status()
        raw: Any = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Alpha Vantage HTTP/json failed pair=%s (%s)", pair, type(exc).__name__)
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

    bars = _parse_av_fx_daily(pair, raw, retrieved_at=receipt)
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
        receipt = _retrieval_time(None)
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance FX batch download failed (%s)", type(exc).__name__)
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
            out[pair] = _bars_from_yf_frame(sub, pair, ticker, retrieved_at=receipt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("parse failed for %s (%s)", ticker, type(exc).__name__)

    for pair in out:
        out[pair].sort(key=lambda b: b.date)
    return out


def fetch_fx_spot(lookback_days: int = 30) -> dict[str, list[SpotBar]]:
    """Download spot history for all pairs.

    3-tier fallback chain:
      1. Polygon.io (primary)
      2. Alpha Vantage FX_DAILY (secondary)
      3. yfinance (tertiary)
    """

    yf_map = spot_tickers_from_universe()
    out: dict[str, list[SpotBar]] = {p: [] for p in yf_map}
    pairs = list(yf_map.keys())

    # ── Tier 1: Polygon.io ──────────────────────────────────────────────
    for pair in pairs:
        bars = fetch_fx_spot_polygon(pair, lookback_days=lookback_days)
        if bars:
            out[pair] = bars

    # ── Tier 2: Alpha Vantage ───────────────────────────────────────────
    missing = [p for p in pairs if not out.get(p)]
    api_key = (os.environ.get("ALPHAVANTAGE_API_KEY") or "").strip()
    if missing and api_key:
        av_stop = False
        for i, pair in enumerate(missing):
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

    # ── Tier 3: yfinance ────────────────────────────────────────────────
    missing = [p for p in pairs if not out.get(p)]
    if missing:
        yf_part = _fetch_fx_spot_yfinance_batch(yf_map, missing, lookback_days)
        for p in missing:
            if yf_part.get(p):
                out[p] = yf_part[p]

    return out


def _bars_from_yf_frame(
    raw: pd.DataFrame, pair: str, ticker: str, *, retrieved_at: datetime | None = None,
    adjusted: bool = True,
) -> list[SpotBar]:
    if raw is None or raw.empty:
        return []
    receipt = _retrieval_time(retrieved_at)
    bars: list[SpotBar] = []
    for idx, row in raw.iterrows():
        try:
            if any(isinstance(row.get(k), (bool, np.bool_)) for k in (
                "Open", "High", "Low", "Close", "Volume",
            )):
                continue
            stamp = pd.Timestamp(idx)
            if pd.isna(stamp):
                continue
            instant = stamp.to_pydatetime() if stamp.tzinfo is not None else None
            if instant is not None:
                instant = instant.astimezone(UTC)
                if instant > receipt:
                    continue
            open_, high, low, close = (
                float(row.get(k, np.nan)) for k in ("Open", "High", "Low", "Close")
            )
            volume_raw = row.get("Volume", 0.0)
            volume = 0.0 if pd.isna(volume_raw) else float(volume_raw)
            if not _valid_ohlc(open_, high, low, close) or not np.isfinite(volume) or volume < 0:
                continue
            timezone = str(stamp.tzinfo) if stamp.tzinfo is not None else None
            bars.append(SpotBar(
                date=stamp.date(), pair=pair, open=open_, high=high, low=low, close=close,
                volume=volume, provider="yahoo", instrument=ticker, retrieved_at=receipt,
                provider_timestamp=instant, session_timezone=timezone,
                provider_metadata={"date_label_policy": "provider_date", "raw_index": str(idx),
                                   "index_timezone": timezone, "adjusted": adjusted},
                volume_source="yahoo", volume_instrument=ticker,
            ))
        except (TypeError, ValueError, OverflowError):
            continue
    return sorted(bars, key=lambda bar: bar.date)


async def _fetch_one_spot_async(
    pair: str,
    ticker: str,
    period: str,
    fetcher: AsyncFetcher,
) -> tuple[str, list[SpotBar]]:
    t0 = time.perf_counter()

    def _download() -> tuple[pd.DataFrame, datetime]:
        frame = cast(
            pd.DataFrame,
            _yfinance().download(ticker, period=period, auto_adjust=True, progress=False),
        )
        return frame, _retrieval_time(None)

    async with fetcher.semaphore:
        try:
            raw, receipt = await asyncio.to_thread(_download)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "yfinance async download failed %s %s (%s)", pair, ticker, type(exc).__name__,
            )
            logger.info(
                "fetch_fx_spot_async pair=%s ticker=%s completed in %.3fs (error)",
                pair,
                ticker,
                time.perf_counter() - t0,
            )
            return pair, []

    frame = raw
    if isinstance(frame.columns, pd.MultiIndex):
        # Single-ticker yfinance downloads use MultiIndex columns
        # with names=['Price', 'Ticker']; flatten to simple columns.
        frame.columns = frame.columns.get_level_values(0)

    bars = _bars_from_yf_frame(frame, pair, ticker, retrieved_at=receipt)
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
    """Spot per instrument: Polygon → Alpha Vantage → yfinance.

    3-tier fallback chain identical to ``fetch_fx_spot``.
    """

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

    # ── Tier 1: Polygon.io ──────────────────────────────────────────────
    for pair, _yf_ticker in tasks:
        bars = await asyncio.to_thread(
            fetch_fx_spot_polygon, pair, lookback_days=lookback_days
        )
        if bars:
            out[pair] = bars

    # ── Tier 2: Alpha Vantage ───────────────────────────────────────────
    missing_tasks = [(p, t) for p, t in tasks if not out.get(p)]
    api_key = (os.environ.get("ALPHAVANTAGE_API_KEY") or "").strip()
    if missing_tasks and api_key:
        av_stop = False
        for i, (pair, _yf_ticker) in enumerate(missing_tasks):
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

    # ── Tier 3: yfinance ────────────────────────────────────────────────
    missing_tasks = [(p, t) for p, t in tasks if not out.get(p)]
    t_batch = time.perf_counter()
    if missing_tasks:
        results = await asyncio.gather(
            *[_fetch_one_spot_async(pair, t, period, gate) for pair, t in missing_tasks],
            return_exceptions=True,
        )
        for res in results:
            if isinstance(res, BaseException):
                logger.error("fetch_fx_spot_async task failed (%s)", type(res).__name__)
                continue
            pair, bars = res
            out[pair] = bars

    logger.info(
        "fetch_fx_spot_async batch pairs=%s total_wall=%.3fs",
        len(out),
        time.perf_counter() - t_batch,
    )

    # Pillar 2: Fetch institutional volume proxies (CME Futures) for RVOL gating
    vol_tasks: list[tuple[str, str]] = []
    for sym, meta in universe.items():
        if not isinstance(meta, dict) or meta.get("class") != "FX":
            continue
        tickers = meta.get("tickers") or {}
        vt = tickers.get("volume_ticker")
        if isinstance(vt, str) and vt.strip():
            vol_tasks.append((sym, vt.strip()))

    if vol_tasks:
        logger.info("fetch_fx_spot_async: fetching volume proxies for %s pairs", len(vol_tasks))
        vol_results = await asyncio.gather(
            *[_fetch_one_spot_async(pair, t, period, gate) for pair, t in vol_tasks],
            return_exceptions=True,
        )
        for res in vol_results:
            if isinstance(res, BaseException) or not res:
                continue
            pair, vol_bars = res
            if not vol_bars or pair not in out:
                continue
            # Merge volume into spot bars by matching date
            vol_map = {b.date: b for b in vol_bars if b.volume > 0}
            for bar in out[pair]:
                if bar.date in vol_map:
                    proxy = vol_map[bar.date]
                    bar.volume = proxy.volume
                    bar.volume_source = proxy.provider
                    bar.volume_instrument = proxy.instrument

    return out
