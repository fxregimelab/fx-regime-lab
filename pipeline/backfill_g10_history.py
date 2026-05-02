#!/usr/bin/env python3
"""Backfill the last 1,260 daily bars (~5y trading days) for G10 expansion pairs.

Writes to Supabase ``historical_prices`` via ``writer.write_historical_prices`` only.
Spot source: Yahoo (same symbols as ``universe.json`` ``spot_ticker``), matching live FX spot.
Yield sanity: one synchronous ``fetch_yields()`` call (FRED-first for US legs) logs a snapshot.

Run from repo root::

    cd pipeline && python backfill_g10_history.py

Requires ``.env`` at repo root with Supabase credentials.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

from src.db import writer
from src.fetchers.yields import fetch_yields
from src.types import spot_tickers_from_universe

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

NEW_PAIRS: tuple[str, ...] = ("GBPUSD", "AUDUSD", "USDCAD", "USDCHF")
TARGET_BARS = 1260
# Calendar window wide enough to capture ~1260 sessions after weekends/holidays.
CAL_WINDOW_DAYS = int(TARGET_BARS * 2.2)


def _yf_row_float(row: Any, attr: str) -> float | None:
    val = getattr(row, attr, None)
    return float(val) if val is not None and pd.notna(val) else None


def _rows_from_df(pair: str, df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    
    # Flatten Multi-index columns if they exist (yfinance 0.2.40+ behavior)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    normalized = df.reset_index().rename(columns={"Date": "date"})
    rows: list[dict[str, Any]] = []
    for row in normalized.itertuples(index=False):
        # Access date from itertuple which might have been renamed or remained as 'Index'/'date'
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
    return rows


def backfill_pair(pair: str, ticker: str) -> int:
    try:
        df = yf.download(
            ticker,
            period=f"{CAL_WINDOW_DAYS}d",
            auto_adjust=False,
            progress=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("yfinance failed %s %s: %s", pair, ticker, exc)
        return 0
    if df.empty:
        logger.warning("empty frame %s", pair)
        return 0
    rows = _rows_from_df(pair, df)
    if len(rows) > TARGET_BARS:
        rows = rows[-TARGET_BARS:]
    if not rows:
        return 0
    chunk = 1000
    for idx in range(0, len(rows), chunk):
        writer.write_historical_prices(rows[idx : idx + chunk])
    logger.info("backfill_g10_history %s rows=%s", pair, len(rows))
    return len(rows)


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    ymap = spot_tickers_from_universe()
    legs = fetch_yields(lookback_days=5)
    logger.info(
        "FRED-first yield sanity snapshot: us_2y=%s us_10y=%s",
        legs.get("us_2y"),
        legs.get("us_10y"),
    )
    total = 0
    for pair in NEW_PAIRS:
        t = ymap.get(pair)
        if not t:
            logger.error("no spot ticker for %s in universe", pair)
            continue
        total += backfill_pair(pair, t)
    logger.info("backfill_g10_history total rows written: %s", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
