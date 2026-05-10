"""Bulk fetch historical FRED yield series and store in ``historical_yields``.

Usage::

    python -m src.backfill.fred_historical
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date
from typing import Any

from fredapi import Fred

from src.db import writer

logger = logging.getLogger(__name__)

SERIES_CONFIG: dict[str, dict[str, Any]] = {
    "DGS2": {"description": "US 2Y Treasury", "start": "1976-01-01"},
    "DGS10": {"description": "US 10Y Treasury", "start": "1962-01-01"},
    "IRLTLT01DEM156N": {"description": "DE 10Y Govt Bond", "start": "1960-01-01"},
    "IRLTLT01JPM156N": {"description": "JP 10Y Govt Bond", "start": "1989-01-01"},
    "INDIRLTLT01STM": {"description": "IN 10Y Govt Bond", "start": "2000-01-01"},
    "T10YIE": {"description": "US 10Y Breakeven Inflation", "start": "2003-01-01"},
}


def _fred_client() -> Fred | None:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        logger.error("FRED_API_KEY not set")
        return None
    return Fred(api_key=key)


def fetch_series_observations(series_id: str, start: str, end: str | None = None) -> list[dict[str, Any]]:
    """Fetch all observations for a FRED series."""
    fred = _fred_client()
    if fred is None:
        return []

    try:
        logger.info("Fetching %s from %s", series_id, start)
        series = fred.get_series(series_id, start=start, end=end)
        if series is None or series.empty:
            logger.warning("FRED %s returned empty series", series_id)
            return []

        rows: list[dict[str, Any]] = []
        for dt, val in series.items():
            if val is None or str(val) in (".", "", "nan"):
                continue
            try:
                rows.append({
                    "date": str(dt)[:10],
                    "series_id": series_id,
                    "value": float(val),
                })
            except (ValueError, TypeError):
                continue
        logger.info("Fetched %d observations for %s", len(rows), series_id)
        return rows
    except Exception as exc:
        logger.error("FRED fetch failed for %s: %s", series_id, exc)
        return []


def backfill_all_fred_series() -> dict[str, int]:
    """Fetch and store all configured FRED series. Returns counts per series."""
    counts: dict[str, int] = {}
    for series_id, cfg in SERIES_CONFIG.items():
        rows = fetch_series_observations(series_id, cfg["start"])
        if not rows:
            counts[series_id] = 0
            continue

        # Batch insert via pg8000 or REST API
        # Using REST upsert for idempotency
        _bulk_upsert_historical_yields(rows)
        counts[series_id] = len(rows)
        time.sleep(1.0)  # Respect FRED rate limits

    return counts


def _bulk_upsert_historical_yields(rows: list[dict[str, Any]]) -> None:
    """Upsert rows into historical_yields using the Supabase client."""
    client = writer._client()
    # Supabase REST upsert in batches of 1000
    batch_size = 1000
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            client.table("historical_yields").upsert(batch, on_conflict="date,series_id").execute()
        except Exception as exc:
            logger.warning("Batch upsert failed: %s", exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = backfill_all_fred_series()
    logger.info("FRED backfill complete: %s", results)
