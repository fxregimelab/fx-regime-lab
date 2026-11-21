"""Acquire historical Yahoo bars into the append-only observation archive."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pandas as pd

from src.core.price_archive_stage import archive_price_snapshot
from src.db import writer
from src.fetchers.fx_spot import _bars_from_yf_frame
from src.types import SpotBar, spot_tickers_from_universe

logger = logging.getLogger(__name__)
_LOCKED_PAIRS = frozenset({"EURUSD", "USDJPY", "USDINR"})


def _validate_range(start: date, end: date) -> None:
    if type(start) is not date or type(end) is not date:
        raise TypeError("Historical acquisition bounds must be calendar dates")
    if start > end:
        raise ValueError("Historical acquisition start date must not follow end date")
    if end > datetime.now(UTC).date():
        raise ValueError("Historical acquisition end date cannot be in the future")


def _yfinance() -> Any:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("Historical Yahoo acquisition requires yfinance") from exc
    return yf


def _yf_download(pair: str, ticker: str, start: date, end: date) -> list[SpotBar]:
    """Fetch unadjusted Yahoo daily bars and parse their provider metadata."""
    _validate_range(start, end)

    try:
        frame = _yfinance().download(
            ticker,
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            progress=False,
            auto_adjust=False,
            ignore_tz=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Historical Yahoo acquisition failed pair=%s error_type=%s",
            pair,
            type(exc).__name__,
        )
        raise RuntimeError(
            f"Historical Yahoo acquisition failed for {pair} ({type(exc).__name__})"
        ) from None
    receipt = datetime.now(UTC)

    if frame is None or frame.empty:
        return []

    if isinstance(frame.columns, pd.MultiIndex):
        frame = frame.copy()
        frame.columns = frame.columns.get_level_values(0)
    bars = _bars_from_yf_frame(
        frame,
        pair,
        ticker,
        retrieved_at=receipt,
        adjusted=False,
    )
    return [bar for bar in bars if start <= bar.date <= end]


def fetch_historical_spot_yfinance(
    pair: str,
    start: date,
    end: date,
) -> list[SpotBar]:
    """Fetch historical spot bars for ``pair`` between ``start`` and ``end``.

    Uses the Yahoo ticker from ``universe.json`` (e.g. ``EURUSD=X``).
    """
    _validate_range(start, end)
    if pair not in _LOCKED_PAIRS:
        raise ValueError(f"Historical acquisition pair is outside the locked universe: {pair}")
    tickers = spot_tickers_from_universe()
    ticker = tickers.get(pair)
    if not ticker:
        raise ValueError(f"Historical acquisition pair is not configured: {pair}")

    bars = _yf_download(pair, ticker, start, end)
    logger.info("Fetched %d bars for %s (%s) from %s to %s", len(bars), pair, ticker, start, end)
    return bars


def backfill_spot_for_pair(
    pair: str,
    start: date,
    end: date,
) -> int:
    """Fetch and archive historical observations. Returns confirmed row count."""
    bars = fetch_historical_spot_yfinance(pair, start, end)
    if not bars:
        return 0
    receipts = [bar.retrieved_at for bar in bars]
    if any(value is None for value in receipts):
        raise RuntimeError("Historical Yahoo parser returned a bar without retrieval evidence")
    cutoff = max(value for value in receipts if value is not None)
    result = archive_price_snapshot(
        {pair: bars},
        as_of=end,
        cutoff=cutoff,
        writer=writer,
    )
    if result.archived_count != len(bars):
        raise RuntimeError(
            "Historical Yahoo acquisition contained invalid, future, or incomplete metadata"
        )
    logger.info(
        "Archived %d provisional provider observations for %s; canonical closes unqualified",
        result.archived_count,
        pair,
    )
    return result.archived_count
