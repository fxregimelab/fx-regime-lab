"""Async HTTP + concurrency helpers for configuration-driven fetchers."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Final

import aiohttp

from src.fetchers.buffer_keys import KEY_COT, KEY_CROSS_ASSET, KEY_FX_SPOT, KEY_YIELDS
from src.types import load_universe

logger: Final[logging.Logger] = logging.getLogger(__name__)


def _safe_url_for_log(url: str, max_len: int = 120) -> str:
    redacted = url
    if "api_key=" in redacted:
        redacted = redacted.split("api_key=")[0] + "api_key=REDACTED"
    return redacted[:max_len]


# Strict cap: free-tier providers (Yahoo/FRED/CFTC) share one gate.
_FETCH_CONCURRENCY: Final[int] = 5


class AsyncFetcher:
    """Shared concurrency gate for remote data (yfinance, FRED, etc.)."""

    __slots__ = ("_semaphore",)

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(_FETCH_CONCURRENCY)

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore

    async def fetch_with_retry(
        self,
        url: str,
        session: aiohttp.ClientSession,
        *,
        retries: int = 3,
    ) -> tuple[int, bytes | None]:
        """GET ``url`` with exponential backoff. Returns ``(status, body)``."""

        t_start = time.perf_counter()
        last_status = -1
        async with self._semaphore:
            for attempt in range(max(retries, 1)):
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=90)) as resp:
                        body = await resp.read()
                        last_status = resp.status
                        if resp.status == 200:
                            elapsed = time.perf_counter() - t_start
                            logger.info(
                                "fetch_with_retry ok url=%s attempt=%s status=%s bytes=%s in %.3fs",
                                _safe_url_for_log(url),
                                attempt + 1,
                                resp.status,
                                len(body),
                                elapsed,
                            )
                            return resp.status, body
                        logger.warning(
                            "fetch_with_retry non-200 url=%s attempt=%s status=%s",
                            _safe_url_for_log(url),
                            attempt + 1,
                            resp.status,
                        )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "fetch_with_retry error url=%s attempt=%s: %s",
                        _safe_url_for_log(url),
                        attempt + 1,
                        exc,
                    )
                if attempt < retries - 1:
                    delay = 2**attempt
                    logger.info("fetch_with_retry backoff %.1fs before retry", delay)
                    await asyncio.sleep(delay)
        elapsed = time.perf_counter() - t_start
        logger.error(
            "fetch_with_retry exhausted url=%s last_status=%s in %.3fs",
            _safe_url_for_log(url),
            last_status,
            elapsed,
        )
        return last_status, None


async def build_master_buffer(
    *,
    spot_lookback_days: int = 120,
    yield_lookback_days: int = 5,
) -> dict[str, Any]:
    """Concurrent ingestion: spots, yields (universe + legacy 10Y), COT, cross-asset."""

    from src.fetchers.cot import fetch_cot_async
    from src.fetchers.cross_asset import fetch_cross_asset_async
    from src.fetchers.fx_spot import fetch_fx_spot_async
    from src.fetchers.yields import (
        fetch_legacy_10y_legs,
        fetch_t10yie_breakeven_async,
        fetch_yields_async,
    )

    universe = load_universe()
    fetcher = AsyncFetcher()
    t0 = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        spots_t, ylds_t, cot_t, cross_t, ten_t, bei_t = await asyncio.gather(
            fetch_fx_spot_async(
                universe,
                session,
                lookback_days=spot_lookback_days,
                fetcher=fetcher,
            ),
            fetch_yields_async(
                universe,
                session,
                lookback_days=yield_lookback_days,
                fetcher=fetcher,
            ),
            fetch_cot_async(universe, session, fetcher=fetcher),
            fetch_cross_asset_async(session, fetcher),
            asyncio.to_thread(fetch_legacy_10y_legs, yield_lookback_days),
            fetch_t10yie_breakeven_async(session, fetcher),
            return_exceptions=True,
        )

    buffer: dict[str, Any] = {}

    if isinstance(spots_t, Exception):
        logger.error("build_master_buffer fx_spot failed: %s", spots_t)
        buffer[KEY_FX_SPOT] = {}
    elif isinstance(spots_t, dict):
        buffer[KEY_FX_SPOT] = spots_t
    else:
        logger.error("build_master_buffer fx_spot unexpected type: %s", type(spots_t))
        buffer[KEY_FX_SPOT] = {}

    ylds: dict[str, float | None] = {}
    if isinstance(ylds_t, Exception):
        logger.error("build_master_buffer yields (async universe) failed: %s", ylds_t)
    elif isinstance(ylds_t, dict):
        ylds = dict(ylds_t)

    if isinstance(ten_t, Exception):
        logger.error("build_master_buffer legacy 10Y failed: %s", ten_t)
    elif isinstance(ten_t, dict):
        ylds = {**ylds, **ten_t}

    if isinstance(bei_t, Exception):
        logger.warning("build_master_buffer T10YIE breakeven failed: %s", bei_t)
    elif isinstance(bei_t, (int, float)):
        ylds["T10YIE"] = float(bei_t)

    buffer[KEY_YIELDS] = ylds

    if isinstance(cot_t, Exception):
        logger.error("build_master_buffer cot failed: %s", cot_t)
        buffer[KEY_COT] = []
    elif isinstance(cot_t, list):
        buffer[KEY_COT] = cot_t
    else:
        logger.error("build_master_buffer cot unexpected type: %s", type(cot_t))
        buffer[KEY_COT] = []

    if isinstance(cross_t, Exception):
        logger.error("build_master_buffer cross_asset failed: %s", cross_t)
        buffer[KEY_CROSS_ASSET] = {
            "vix": None,
            "dxy": None,
            "oil": None,
            "gold": None,
            "copper": None,
            "stoxx": None,
        }
    elif isinstance(cross_t, dict):
        buffer[KEY_CROSS_ASSET] = cross_t
    else:
        logger.error("build_master_buffer cross_asset unexpected type: %s", type(cross_t))
        buffer[KEY_CROSS_ASSET] = {
            "vix": None,
            "dxy": None,
            "oil": None,
            "gold": None,
            "copper": None,
            "stoxx": None,
        }

    wall = time.perf_counter() - t0
    logger.info("build_master_buffer Total Wall Clock Time: %.3fs", wall)
    return buffer
