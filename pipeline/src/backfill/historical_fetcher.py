"""Round 4 Phase 1 — Historical data backfill via yfinance.

Fetches multi-year FX spot OHLC series for the 3-pair FX basket.  Stores raw bars
in ``historical_prices`` (upsert idempotent on ``date, pair``) so the
historical pipeline runner can replay signal generation for any date.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import pandas as pd

from src.db import writer
from src.types import SpotBar, spot_tickers_from_universe

logger = logging.getLogger(__name__)


def _yf_download(ticker: str, start: date, end: date) -> list[SpotBar]:
    """Fetch daily OHLC from yfinance; return empty on failure."""
    try:
        import yfinance as yf
    except ImportError as exc:
        logger.warning("yfinance not installed: %s", exc)
        return []

    try:
        df = yf.download(
            ticker,
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            progress=False,
            auto_adjust=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance download failed for %s: %s", ticker, exc)
        return []

    if df is None or df.empty:
        return []

    # yfinance returns MultiIndex columns in recent versions (Price, Ticker)
    # Normalise to simple column names by dropping the Ticker level
    if isinstance(df.columns, pd.MultiIndex):
        if "Price" in df.columns.names:
            df.columns = df.columns.droplevel("Ticker" if "Ticker" in df.columns.names else 1)
        else:
            df.columns = [
                "_".join(str(c) for c in col).strip("_") if isinstance(col, tuple) else str(col)
                for col in df.columns
            ]

    bars: list[SpotBar] = []
    for idx, row in df.iterrows():
        try:
            d = date.fromisoformat(str(idx)[:10])
        except ValueError:
            continue
        open_v = row.get("Open")
        high_v = row.get("High")
        low_v = row.get("Low")
        close_v = row.get("Close")
        vol_v = row.get("Volume") or 0.0
        if close_v is None:
            continue
        try:
            bars.append(
                SpotBar(
                    date=d,
                    pair="",  # filled downstream
                    open=float(open_v) if open_v is not None else float(close_v),
                    high=float(high_v) if high_v is not None else float(close_v),
                    low=float(low_v) if low_v is not None else float(close_v),
                    close=float(close_v),
                    volume=float(vol_v) if vol_v is not None else 0.0,
                )
            )
        except (ValueError, TypeError):
            continue
    return bars


def fetch_historical_spot_yfinance(
    pair: str,
    start: date,
    end: date,
) -> list[SpotBar]:
    """Fetch historical spot bars for ``pair`` between ``start`` and ``end``.

    Uses the Yahoo ticker from ``universe.json`` (e.g. ``EURUSD=X``).
    """
    tickers = spot_tickers_from_universe()
    ticker = tickers.get(pair)
    if not ticker:
        logger.warning("No spot ticker configured for %s in universe", pair)
        return []

    bars = _yf_download(ticker, start, end)
    for b in bars:
        b.pair = pair
    logger.info("Fetched %d bars for %s (%s) from %s to %s", len(bars), pair, ticker, start, end)
    return bars


def backfill_spot_for_pair(
    pair: str,
    start: date,
    end: date,
) -> int:
    """Fetch and persist historical spot bars. Returns count written."""
    bars = fetch_historical_spot_yfinance(pair, start, end)
    if not bars:
        return 0

    rows: list[dict[str, Any]] = []
    for b in bars:
        rows.append(
            {
                "date": b.date.isoformat(),
                "pair": b.pair,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
        )

    writer.write_historical_prices(rows, source="yfinance")
    return len(rows)
