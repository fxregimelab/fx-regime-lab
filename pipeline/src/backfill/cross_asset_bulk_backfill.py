"""Bulk historical backfill for cross-asset data (VIX, DXY, oil, gold, copper, STOXX).

Uses yfinance to fetch deep history and persists to ``historical_cross_asset``,
then back-propagates into ``signals`` via exact-date join + forward-fill.

Usage::

    python -m src.backfill.cross_asset_bulk_backfill
"""

from __future__ import annotations
import os

import logging
import time
from datetime import date
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

_TICKERS: dict[str, str] = {
    "vix": "^VIX",
    "dxy": "DX-Y.NYB",
    "oil": "CL=F",
    "gold": "GC=F",
    "copper": "HG=F",
    "stoxx": "^STOXX50E",
}

_START = "1997-01-01"


def _pg_conn() -> Any:
    import ssl

    import pg8000.native

    ctx = ssl._create_unverified_context()
    return pg8000.native.Connection(
        host=os.environ.get("SUPABASE_DB_HOST", ""),
        database="postgres",
        user="postgres",
        password=os.environ.get("SUPABASE_DB_PASSWORD", ""),
        ssl_context=ctx,
    )


def _extract_close_series(df: pd.DataFrame) -> pd.Series:
    """Extract a clean close series from a yfinance MultiIndex DataFrame."""
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    close_values = df["Close"]
    close_series = (
        close_values.iloc[:, 0]
        if isinstance(close_values, pd.DataFrame)
        else close_values
    )
    return close_series.dropna()


def fetch_ticker_history(ticker: str, label: str) -> dict[date, float]:
    """Download daily close history for a single ticker."""
    import yfinance as yf

    try:
        df = yf.download(ticker, start=_START, auto_adjust=True, progress=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s (%s) download failed: %s", label, ticker, exc)
        return {}

    series = _extract_close_series(df)
    if series.empty:
        logger.warning("%s (%s) returned no close data", label, ticker)
        return {}

    out: dict[date, float] = {}
    for dt, val in series.items():
        if pd.isna(val):
            continue
        d = dt.date() if hasattr(dt, "date") else date.fromisoformat(str(dt)[:10])
        out[d] = float(val)
    logger.info("%s (%s) fetched %d rows", label, ticker, len(out))
    return out


def create_table_if_not_exists() -> None:
    conn = _pg_conn()
    conn.run(
        """
        CREATE TABLE IF NOT EXISTS historical_cross_asset (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            vix DOUBLE PRECISION,
            dxy DOUBLE PRECISION,
            oil DOUBLE PRECISION,
            gold DOUBLE PRECISION,
            copper DOUBLE PRECISION,
            stoxx DOUBLE PRECISION,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(date)
        )
        """
    )
    conn.close()
    logger.info("Table historical_cross_asset ensured")


def upsert_rows(rows: list[dict[str, Any]], batch_size: int = 1000) -> int:
    """Upsert rows into historical_cross_asset via pg8000."""
    if not rows:
        return 0
    conn = _pg_conn()
    inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        placeholders: list[str] = []
        params: dict[str, Any] = {}
        for bidx, row in enumerate(batch):
            prefix = f"p{i}_{bidx}_"
            ph = (
                f"(:{prefix}date, :{prefix}vix, :{prefix}dxy, :{prefix}oil, "
                f":{prefix}gold, :{prefix}copper, :{prefix}stoxx)"
            )
            placeholders.append(ph)
            params[f"{prefix}date"] = row["date"]
            params[f"{prefix}vix"] = row.get("vix")
            params[f"{prefix}dxy"] = row.get("dxy")
            params[f"{prefix}oil"] = row.get("oil")
            params[f"{prefix}gold"] = row.get("gold")
            params[f"{prefix}copper"] = row.get("copper")
            params[f"{prefix}stoxx"] = row.get("stoxx")

        sql = f"""
            INSERT INTO historical_cross_asset (date, vix, dxy, oil, gold, copper, stoxx)
            VALUES {', '.join(placeholders)}
            ON CONFLICT (date) DO UPDATE SET
                vix = EXCLUDED.vix,
                dxy = EXCLUDED.dxy,
                oil = EXCLUDED.oil,
                gold = EXCLUDED.gold,
                copper = EXCLUDED.copper,
                stoxx = EXCLUDED.stoxx,
                created_at = NOW()
        """
        conn.run(sql, **params)
        inserted += len(batch)
    conn.close()
    return inserted


def update_signals_exact_match() -> int:
    """Set cross-asset columns on signals where date matches exactly."""
    conn = _pg_conn()
    result = conn.run(
        """
        UPDATE signals s
        SET
            cross_asset_vix = h.vix,
            cross_asset_dxy = h.dxy,
            cross_asset_oil = h.oil,
            cross_asset_gold = h.gold,
            cross_asset_copper = h.copper,
            cross_asset_stoxx = h.stoxx
        FROM historical_cross_asset h
        WHERE s.date = h.date
          AND s.cross_asset_vix IS NULL
        """
    )
    conn.close()
    count = result[0][0] if result and len(result) > 0 and len(result[0]) > 0 else 0
    logger.info("Signals exact-match updated: %s rows", count)
    return int(count)


def update_signals_forward_fill() -> int:
    """Forward-fill remaining NULL cross-asset columns from most recent prior date."""
    conn = _pg_conn()
    # LATERAL join: for each signals row, pick the most recent historical row <= signal date
    result = conn.run(
        """
        WITH ff AS (
            SELECT
                s.date AS signal_date,
                h.vix,
                h.dxy,
                h.oil,
                h.gold,
                h.copper,
                h.stoxx
            FROM signals s
            LEFT JOIN LATERAL (
                SELECT *
                FROM historical_cross_asset h2
                WHERE h2.date <= s.date
                ORDER BY h2.date DESC
                LIMIT 1
            ) h ON true
            WHERE s.cross_asset_vix IS NULL
        )
        UPDATE signals
        SET
            cross_asset_vix = ff.vix,
            cross_asset_dxy = ff.dxy,
            cross_asset_oil = ff.oil,
            cross_asset_gold = ff.gold,
            cross_asset_copper = ff.copper,
            cross_asset_stoxx = ff.stoxx
        FROM ff
        WHERE signals.date = ff.signal_date
          AND signals.cross_asset_vix IS NULL
        """
    )
    conn.close()
    count = result[0][0] if result and len(result) > 0 and len(result[0]) > 0 else 0
    logger.info("Signals forward-fill updated: %s rows", count)
    return int(count)


def run_backfill() -> dict[str, Any]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # 1. Create table
    create_table_if_not_exists()

    # 2. Download history per ticker
    data_by_label: dict[str, dict[date, float]] = {}
    failed_tickers: list[str] = []
    for label, ticker in _TICKERS.items():
        hist = fetch_ticker_history(ticker, label)
        if not hist:
            failed_tickers.append(ticker)
        data_by_label[label] = hist
        if label != list(_TICKERS.keys())[-1]:
            time.sleep(2)

    # 3. Align dates and build rows
    all_dates: set[date] = set()
    for hist in data_by_label.values():
        all_dates.update(hist.keys())
    sorted_dates = sorted(all_dates)

    rows: list[dict[str, Any]] = []
    for d in sorted_dates:
        row: dict[str, Any] = {"date": d}
        for label in _TICKERS:
            row[label] = data_by_label[label].get(d)
        rows.append(row)

    logger.info("Aligned rows to upsert: %d", len(rows))

    # 4. Upsert
    upserted = upsert_rows(rows)

    # 5. Update signals
    exact_count = update_signals_exact_match()
    ff_count = update_signals_forward_fill()

    # 6. Verify
    conn = _pg_conn()
    verify = conn.run(
        """
        SELECT
            pair,
            COUNT(*) AS total,
            COUNT(cross_asset_vix) AS vix,
            COUNT(cross_asset_dxy) AS dxy,
            COUNT(cross_asset_oil) AS oil,
            COUNT(cross_asset_gold) AS gold,
            COUNT(cross_asset_copper) AS copper,
            COUNT(cross_asset_stoxx) AS stoxx
        FROM signals
        GROUP BY pair
        ORDER BY pair
        """
    )
    conn.close()

    verification = {}
    for row in verify:
        verification[row[0]] = {
            "total": row[1],
            "vix": row[2],
            "dxy": row[3],
            "oil": row[4],
            "gold": row[5],
            "copper": row[6],
            "stoxx": row[7],
        }

    return {
        "historical_rows_upserted": upserted,
        "failed_tickers": failed_tickers,
        "signals_exact_match": exact_count,
        "signals_forward_fill": ff_count,
        "verification": verification,
    }


if __name__ == "__main__":
    result = run_backfill()
    print("=" * 60)
    print("CROSS-ASSET BACKFILL SUMMARY")
    print("=" * 60)
    print(f"Historical rows upserted: {result['historical_rows_upserted']}")
    print(f"Failed tickers: {result['failed_tickers'] or 'None'}")
    print(f"Signals exact-match updated: {result['signals_exact_match']}")
    print(f"Signals forward-fill updated: {result['signals_forward_fill']}")
    print("Verification:")
    for pair, counts in result["verification"].items():
        print(
            f"  {pair}: total={counts['total']}, vix={counts['vix']}, "
            f"dxy={counts['dxy']}, oil={counts['oil']}, gold={counts['gold']}, "
            f"copper={counts['copper']}, stoxx={counts['stoxx']}"
        )
