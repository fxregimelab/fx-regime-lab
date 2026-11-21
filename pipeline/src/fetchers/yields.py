"""Yield legs fetched from yfinance with FRED fallbacks."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import aiohttp
from fredapi import Fred

from src.fetchers.async_engine import AsyncFetcher
from src.signals.rate_inputs import SOURCE_DEFINITIONS, RateInstrument
from src.signals.rate_observation import RateObservation

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

_LOGGABLE_YIELD_IDS = frozenset(
    {
        *YF_2Y_TICKERS.values(),
        *YF_10Y_TICKERS.values(),
        *_US_YAHOO_TO_FRED.values(),
        *(series_id for series_ids in FRED_FALLBACK_SERIES.values() for series_id in series_ids),
        "ECBASSETSW",
        "ECBDFR",
        "IRLTLT01ITM156N",
        "IRSTCI01JPM156N",
        "T10YIE",
    }
)

_OBSERVATION_INSTRUMENTS: dict[str, RateInstrument] = {
    **SOURCE_DEFINITIONS,
    "DGS10": RateInstrument("USD", 10, "government_yield", "daily"),
    "IRLTLT01DEM156N": RateInstrument("EUR", 10, "government_yield", "monthly"),
    "IRLTLT01ITM156N": RateInstrument("EUR", 10, "government_yield", "monthly"),
    "T10YIE": RateInstrument("USD", 10, "inflation_compensation", "daily"),
}


def _yield_id_for_log(source_id: str) -> str:
    """Return only a known yield identifier for diagnostic context."""

    return source_id if source_id in _LOGGABLE_YIELD_IDS else "<unrecognized-yield-id>"


def _record_observation(
    sink: dict[str, RateObservation] | None,
    key: str,
    source_id: str,
    value: float | None,
    observed_on: Any,
    retrieved_at: datetime,
    vintage: str | None = None,
    missing_reason: str | None = None,
    provider_realtime_start: str | None = None,
    provider_realtime_end: str | None = None,
) -> None:
    if sink is None:
        return
    try:
        observed = observed_on.date() if isinstance(observed_on, datetime) else observed_on
        if not hasattr(observed, "year"):
            observed = datetime.fromisoformat(str(observed)[:10]).date()
    except (TypeError, ValueError):
        observed = None
    instrument = _OBSERVATION_INSTRUMENTS.get(source_id)
    sink[key] = RateObservation(
        source_id=source_id,
        instrument=instrument,
        observed_on=observed,
        available_at=None,
        retrieved_at=retrieved_at,
        vintage=vintage,
        value=value,
        unit=instrument.unit if instrument else None,
        missing_reason=missing_reason if value is None else None,
        provider_realtime_start=provider_realtime_start,
        provider_realtime_end=provider_realtime_end,
    )


def _yf_leg(
    ticker: str, label: str, period: str, observations: dict[str, RateObservation] | None = None
) -> float | None:
    try:
        history = _yfinance().Ticker(ticker).history(period=period)
        retrieved_at = datetime.now(UTC)
        if history is None or history.empty or "Close" not in history:
            logger.warning("yfinance yield returned empty history")
            return None
        closes = history["Close"].dropna()
        if closes.empty:
            logger.warning("yfinance yield returned empty close series")
            return None
        value = float(closes.iloc[-1])
        _record_observation(observations, label, ticker, value, closes.index[-1], retrieved_at)
        return value
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance yield fetch failed: %s", type(exc).__name__)
        return None


def _fred_leg(
    fred: Fred | None,
    series_ids: tuple[str, ...],
    label: str,
    observations: dict[str, RateObservation] | None = None,
    key: str | None = None,
) -> float | None:
    if fred is None:
        return None
    for series_id in series_ids:
        try:
            values = fred.get_series_latest_release(series_id)
            retrieved_at = datetime.now(UTC)
            if values is None or values.empty:
                logger.warning("FRED yield returned empty series")
                continue
            clean = values.dropna()
            if clean.empty:
                logger.warning("FRED yield returned NaN-only series")
                continue
            value = float(clean.iloc[-1])
            _record_observation(
                observations, key or series_id, series_id, value, clean.index[-1], retrieved_at
            )
            return value
        except Exception as exc:  # noqa: BLE001
            logger.warning("FRED yield fetch failed: %s", type(exc).__name__)
    return None


def _fetch_yf_legs(
    tickers: dict[str, str],
    period: str,
    observations: dict[str, RateObservation] | None = None,
) -> dict[str, float | None]:
    legs: dict[str, float | None] = {leg_name: None for leg_name in tickers}
    if not tickers:
        return legs
    try:
        ticker_list = list(tickers.values())
        # yfinance 0.2.x download returns a multi-index dataframe if >1 ticker
        df = _yfinance().download(ticker_list, period=period, auto_adjust=True, progress=False)
        retrieved_at = datetime.now(UTC)
        if df.empty or "Close" not in df:
            return legs
        closes = df["Close"]
        for leg_name, ticker in tickers.items():
            try:
                if len(ticker_list) == 1:
                    series = closes.dropna()
                else:
                    series = closes[ticker].dropna()
                if not series.empty:
                    legs[leg_name] = float(series.iloc[-1])
                    _record_observation(
                        observations,
                        leg_name,
                        ticker,
                        legs[leg_name],
                        series.index[-1],
                        retrieved_at,
                    )
            except Exception as exc:
                logger.warning("yfinance batch parse failed: %s", type(exc).__name__)
    except Exception as exc:
        logger.warning("yfinance batch download failed: %s", type(exc).__name__)
    return legs


def fetch_legacy_10y_legs(
    lookback_days: int = 5, *, observations: dict[str, RateObservation] | None = None
) -> dict[str, float | None]:
    """US/DE/JP/IN 10Y legs only (FRED-primary US; Yahoo + FRED fallbacks for others)."""

    window_days = max(lookback_days, 1)
    period = f"{window_days}d"
    fred_key = os.environ.get("FRED_API_KEY")
    fred = Fred(api_key=fred_key) if fred_key else None
    if fred is None:
        logger.warning("FRED_API_KEY not set — US 10Y will use yfinance only")

    yf_10y_non_us = {k: v for k, v in YF_10Y_TICKERS.items() if k != "us_10y"}
    ten_year_legs = _fetch_yf_legs(yf_10y_non_us, period, observations)

    us_10y = _fred_leg(fred, FRED_FALLBACK_SERIES["us_10y"], "US 10Y", observations, "us_10y")
    if us_10y is None:
        us_10y = _yf_leg(YF_10Y_TICKERS["us_10y"], "us_10y", period, observations)
    if us_10y is None:
        logger.warning("US 10Y unavailable in both FRED and yfinance")
    ten_year_legs["us_10y"] = us_10y
    if ten_year_legs["de_10y"] is None:
        ten_year_legs["de_10y"] = _fred_leg(
            fred, FRED_FALLBACK_SERIES["de_10y"], "DE 10Y", observations, "de_10y"
        )
    if ten_year_legs["jp_10y"] is None:
        ten_year_legs["jp_10y"] = _fred_leg(
            fred, FRED_FALLBACK_SERIES["jp_10y"], "JP 10Y", observations, "jp_10y"
        )
    if ten_year_legs["in_10y"] is None:
        ten_year_legs["in_10y"] = _fred_leg(
            fred, FRED_FALLBACK_SERIES["in_10y"], "IN 10Y", observations, "in_10y"
        )
    if observations is not None:
        for leg, value in ten_year_legs.items():
            if value is None and leg not in observations:
                source_id = (
                    FRED_FALLBACK_SERIES[leg][-1] if fred is not None
                    else YF_10Y_TICKERS[leg]
                )
                _record_observation(
                    observations, leg, source_id, None, None,
                    datetime.now(UTC), missing_reason="provider_unavailable",
                )
    return ten_year_legs


def fetch_ecb_balance_sheet(fred: Fred | None = None) -> float | None:
    """Fetch latest ECB total assets (ECBASSETSW) from FRED.

    Returns the latest value in billions EUR, or None if unavailable.
    The FRED series is in millions of EUR — divide by 1000 before returning.
    """
    fred_key = os.environ.get("FRED_API_KEY")
    fred = fred or (Fred(api_key=fred_key) if fred_key else None)
    if fred is None:
        logger.warning("FRED_API_KEY not set — ECB balance sheet skipped")
        return None
    try:
        values = fred.get_series_latest_release("ECBASSETSW")
        if values is None or values.empty:
            logger.warning("FRED ECB balance sheet (ECBASSETSW) returned empty series")
            return None
        clean = values.dropna()
        if clean.empty:
            logger.warning("FRED ECB balance sheet (ECBASSETSW) returned NaN-only series")
            return None
        return float(clean.iloc[-1]) / 1000.0
    except Exception as exc:  # noqa: BLE001
        logger.warning("FRED ECB balance sheet (ECBASSETSW) fetch failed: %s", type(exc).__name__)
        return None


def fetch_bund_btp_spread(
    fred: Fred | None = None, germany_10y: float | None = None
) -> float | None:
    """Compute 10Y Bund - 10Y BTP spread from FRED.

    Returns spread in percentage points, or None if either leg missing.

    IMPORTANT: Re-use the existing Germany 10Y value when available
    (already fetched for yields). Pass it via ``germany_10y`` to avoid
    duplicating the FRED call.
    """
    fred_key = os.environ.get("FRED_API_KEY")
    fred = fred or (Fred(api_key=fred_key) if fred_key else None)

    bund = germany_10y
    if bund is None and fred is not None:
        bund = _fred_leg(fred, ("IRLTLT01DEM156N",), "Germany 10Y")

    btp: float | None = None
    if fred is not None:
        btp = _fred_leg(fred, ("IRLTLT01ITM156N",), "Italy 10Y")

    if bund is None or btp is None:
        logger.warning("Bund-BTP spread unavailable (bund=%s, btp=%s)", bund, btp)
        return None
    return float(bund) - float(btp)


def fetch_boj_policy_rate(fred: Fred | None = None) -> float | None:
    """Fetch latest BoJ policy rate proxy (IRSTCI01JPM156N) from FRED.

    Returns rate in percent, or None if unavailable.

    NOTE: Uses IRSTCI01JPM156N (OECD Japan call money rate) instead of
    the stale INTDSRJPM193N. This series tracks the BoJ policy rate
    with minimal lag and is current to present.
    """
    fred_key = os.environ.get("FRED_API_KEY")
    fred = fred or (Fred(api_key=fred_key) if fred_key else None)
    if fred is None:
        logger.warning("FRED_API_KEY not set — BoJ policy rate skipped")
        return None
    return _fred_leg(fred, ("IRSTCI01JPM156N",), "BoJ policy rate")


def fetch_yields(
    lookback_days: int = 5, *, observations: dict[str, RateObservation] | None = None
) -> dict[str, float | None]:
    """Legacy sync yield fetch; flat map with keys like ``us_2y``, ``us_10y``."""

    window_days = max(lookback_days, 1)
    period = f"{window_days}d"
    fred_key = os.environ.get("FRED_API_KEY")
    fred = Fred(api_key=fred_key) if fred_key else None
    if fred is None:
        logger.warning("FRED_API_KEY not set — US yields will use yfinance only")

    yf_2y_non_us = {k: v for k, v in YF_2Y_TICKERS.items() if k != "us_2y"}
    two_year_legs = _fetch_yf_legs(yf_2y_non_us, period, observations)
    time.sleep(1.0)
    ten_year_legs = (
        fetch_legacy_10y_legs(window_days)
        if observations is None
        else fetch_legacy_10y_legs(window_days, observations=observations)
    )

    us_2y = _fred_leg(fred, FRED_FALLBACK_SERIES["us_2y"], "US 2Y", observations, "us_2y")
    if us_2y is None:
        us_2y = _yf_leg(YF_2Y_TICKERS["us_2y"], "us_2y", period, observations)
    if us_2y is None:
        logger.warning("US 2Y unavailable in both FRED and yfinance")
    two_year_legs["us_2y"] = us_2y

    if us_2y is None:
        _record_observation(
            observations, "us_2y", YF_2Y_TICKERS["us_2y"], None, None,
            datetime.now(UTC), missing_reason="provider_unavailable",
        )
        logger.warning("US yield leg missing after fallback; returning empty yield map")
        return {}

    out: dict[str, float | None] = {}
    out.update(two_year_legs)
    out.update(ten_year_legs)
    bei = _fred_leg(fred, ("T10YIE",), "US 10Y breakeven T10YIE", observations)
    if bei is not None:
        out["T10YIE"] = bei
    if observations is not None:
        for leg, value in out.items():
            if value is None and leg not in observations:
                _record_observation(
                    observations, leg, YF_2Y_TICKERS.get(leg, leg), None, None,
                    datetime.now(UTC), missing_reason="provider_unavailable",
                )
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
    observations: dict[str, RateObservation] | None = None,
) -> float | None:
    t0 = time.perf_counter()

    def _close() -> float | None:
        history = _yfinance().Ticker(ticker).history(period=period)
        retrieved_at = datetime.now(UTC)
        if history is None or history.empty or "Close" not in history:
            logger.warning("yfinance async %s returned empty history", _yield_id_for_log(ticker))
            return None
        closes = history["Close"].dropna()
        if closes.empty:
            logger.warning(
                "yfinance async %s returned empty close series", _yield_id_for_log(ticker)
            )
            return None
        value = float(closes.iloc[-1])
        _record_observation(
            observations, ticker, ticker, value, closes.index[-1], retrieved_at
        )
        return value

    async with fetcher.semaphore:
        try:
            out = await asyncio.to_thread(_close)
        except Exception as exc:  # noqa: BLE001
            logger.warning("yfinance async yield failed: %s", type(exc).__name__)
            out = None
    if out is None:
        _record_observation(
            observations, ticker, ticker, None, None,
            datetime.now(UTC), missing_reason="provider_unavailable",
        )
        logger.info("fetch_yields_async yahoo unavailable in %.3fs", time.perf_counter() - t0)
    else:
        logger.info(
            "fetch_yields_async yahoo ticker=%s value=%s in %.3fs",
            _yield_id_for_log(ticker),
            out,
            time.perf_counter() - t0,
        )
    return out


async def _fred_latest_async(
    series_id: str,
    session: aiohttp.ClientSession,
    fetcher: AsyncFetcher,
    observations: dict[str, RateObservation] | None = None,
) -> float | None:
    t0 = time.perf_counter()
    key = os.environ.get("FRED_API_KEY")
    if not key:
        logger.warning("FRED_API_KEY not set — async yield leg skipped")
        logger.info("fetch_yields_async FRED skipped in %.3fs", time.perf_counter() - t0)
        return None
    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={quote(series_id, safe='')}&api_key={key}&file_type=json"
        "&limit=1&sort_order=desc"
    )
    status, body = await fetcher.fetch_with_retry(url, session)
    retrieved_at = datetime.now(UTC)
    result: float | None = None
    observed_on: Any = None
    provider_realtime_start: str | None = None
    provider_realtime_end: str | None = None
    missing_reason: str | None = "provider_unavailable"
    if status != 200 or body is None:
        logger.warning("FRED async yield HTTP status=%s", status)
    else:
        try:
            payload = json.loads(body.decode("utf-8"))
            obs = payload.get("observations") or []
            if obs:
                missing_reason = "provider_missing_value"
                val = obs[0].get("value")
                observed_on = obs[0].get("date")
                provider_realtime_start = obs[0].get("realtime_start")
                provider_realtime_end = obs[0].get("realtime_end")
                if val not in (None, ".", ""):
                    result = float(val)
                    missing_reason = None
        except Exception as exc:  # noqa: BLE001
            missing_reason = "provider_parse_failed"
            logger.warning("FRED async yield parse failed: %s", type(exc).__name__)
    if result is None:
        logger.info("fetch_yields_async FRED unavailable in %.3fs", time.perf_counter() - t0)
    else:
        logger.info(
            "fetch_yields_async FRED series_id=%s value=%s in %.3fs",
            _yield_id_for_log(series_id),
            result,
            time.perf_counter() - t0,
        )
    _record_observation(
        observations,
        series_id,
        series_id,
        result,
        observed_on,
        retrieved_at,
        None,
        missing_reason,
        provider_realtime_start,
        provider_realtime_end,
    )
    return result


async def _fetch_yield_leg_async(
    series_id: str,
    session: aiohttp.ClientSession,
    fetcher: AsyncFetcher,
    period: str,
    observations: dict[str, RateObservation] | None = None,
) -> tuple[str, float | None]:
    fred_override = _US_YAHOO_TO_FRED.get(series_id)
    if fred_override is not None:
        val = await _fred_latest_async(fred_override, session, fetcher, observations)
        if val is None:
            val = await _yahoo_yield_latest_async(series_id, period, fetcher, observations)
            if observations is not None and series_id in observations:
                observations[series_id] = observations.pop(series_id)
        elif observations is not None and fred_override in observations:
            observations[series_id] = observations[fred_override]
        return series_id, val
    if _is_yahoo_yield_symbol(series_id):
        val = await _yahoo_yield_latest_async(series_id, period, fetcher, observations)
    else:
        val = await _fred_latest_async(series_id, session, fetcher, observations)
    return series_id, val


async def fetch_yields_async(
    universe: dict[str, Any],
    session: aiohttp.ClientSession,
    *,
    lookback_days: int = 5,
    fetcher: AsyncFetcher | None = None,
    observations: dict[str, RateObservation] | None = None,
) -> dict[str, float | None]:
    """Resolve yield legs from ``universe``; normalized in-memory map only (no Supabase)."""

    window_days = max(lookback_days, 1)
    period = f"{window_days}d"
    gate = fetcher if fetcher is not None else AsyncFetcher()
    ids = _unique_yield_ids(universe)
    t_batch = time.perf_counter()
    results = await asyncio.gather(
        *[_fetch_yield_leg_async(sid, session, gate, period, observations) for sid in ids],
        return_exceptions=True,
    )
    out: dict[str, float | None] = {}
    for res in results:
        if isinstance(res, BaseException):
            logger.error("fetch_yields_async leg task failed: %s", type(res).__name__)
            continue
        key, val = res
        out[key] = val
        if observations is not None and val is None and key not in observations:
            source_id = _US_YAHOO_TO_FRED.get(key, key)
            _record_observation(
                observations, key, source_id, None, None,
                datetime.now(UTC), missing_reason="provider_unavailable",
            )
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
    observations: dict[str, RateObservation] | None = None,
) -> float | None:
    """FRED T10YIE — 10-year breakeven inflation (%), for real-rate adjustment."""

    return await _fred_latest_async("T10YIE", session, fetcher, observations)
