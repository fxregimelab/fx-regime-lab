"""Bulk historical backfill for implied volatility (EURUSD, USDJPY).

Uses yfinance to fetch deep history for CBOE FX volatility indices (^EUV, ^JXV).
Falls back to FRED EVZCLS for EURUSD and VIX proxy for USDJPY when yfinance
tickers are unavailable.

Persists to ``historical_implied_vol``, then back-propagates into ``signals``
via exact-date join + forward-fill.  USDINR is proxied from realized_vol_20d.

Usage::

    python -m src.backfill.implied_vol_bulk_backfill
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

_START = "1997-01-01"


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _pg_conn() -> Any:
    import ssl

    import pg8000.native

    ctx = ssl._create_unverified_context()
    import os
    host = os.environ.get("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        raise RuntimeError("SUPABASE_DB_PASSWORD must be set in the environment.")
    return pg8000.native.Connection(
        host=host,
        database="postgres",
        user="postgres",
        password=password,
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


def fetch_yfinance_history(ticker: str, label: str) -> dict[date, float]:
    """Download daily close history from yfinance."""
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


def fetch_fred_evz() -> dict[date, float]:
    """Fetch EURUSD implied vol from FRED EVZCLS (CBOE EuroCurrency Volatility Index)."""
    import os

    import requests

    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        logger.warning("FRED_API_KEY not set; skipping FRED EVZ fetch")
        return {}

    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=EVZCLS&api_key={api_key}&file_type=json"
    )
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("FRED EVZCLS fetch failed: %s", exc)
        return {}

    out: dict[date, float] = {}
    for obs in data.get("observations", []):
        val = obs.get("value")
        if val is None or val == ".":
            continue
        try:
            d = date.fromisoformat(obs["date"])
            out[d] = float(val)
        except (ValueError, TypeError):
            continue
    logger.info("FRED EVZCLS fetched %d rows", len(out))
    return out


def fetch_vix_proxy_from_db() -> dict[date, float]:
    """Load VIX history from historical_cross_asset as a USDJPY vol proxy."""
    conn = _pg_conn()
    result = conn.run(
        "SELECT date, vix FROM historical_cross_asset WHERE vix IS NOT NULL ORDER BY date"
    )
    out: dict[date, float] = {}
    for row in result:
        d = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0])[:10])
        out[d] = float(row[1])
    conn.close()
    logger.info("VIX proxy loaded from DB: %d rows", len(out))
    return out


def create_table_if_not_exists() -> None:
    conn = _pg_conn()
    conn.run(
        """
        CREATE TABLE IF NOT EXISTS historical_implied_vol (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            euv DOUBLE PRECISION,
            jxv DOUBLE PRECISION,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(date)
        )
        """
    )
    conn.close()
    logger.info("Table historical_implied_vol ensured")


def upsert_rows(rows: list[dict[str, Any]], batch_size: int = 1000) -> int:
    """Upsert rows into historical_implied_vol via pg8000."""
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
            ph = f"(:{prefix}date, :{prefix}euv, :{prefix}jxv)"
            placeholders.append(ph)
            params[f"{prefix}date"] = row["date"]
            params[f"{prefix}euv"] = row.get("euv")
            params[f"{prefix}jxv"] = row.get("jxv")

        sql = f"""
            INSERT INTO historical_implied_vol (date, euv, jxv)
            VALUES {', '.join(placeholders)}
            ON CONFLICT (date) DO UPDATE SET
                euv = EXCLUDED.euv,
                jxv = EXCLUDED.jxv,
                created_at = NOW()
        """
        conn.run(sql, **params)
        inserted += len(batch)
    conn.close()
    return inserted


def update_signals_exact_match() -> dict[str, int]:
    """Set implied_vol_30d on signals where date matches exactly (pair-aware)."""
    conn = _pg_conn()
    results: dict[str, int] = {}

    for pair, col in (("EURUSD", "euv"), ("USDJPY", "jxv")):
        res = conn.run(
            f"""
            UPDATE signals s
            SET implied_vol_30d = h.{col}
            FROM historical_implied_vol h
            WHERE s.date = h.date
              AND s.pair = '{pair}'
              AND s.implied_vol_30d IS NULL
            """
        )
        count = res[0][0] if res and len(res) > 0 and len(res[0]) > 0 else 0
        results[pair] = int(count)
        logger.info("Signals exact-match updated for %s: %s rows", pair, count)

    conn.close()
    return results


def update_signals_forward_fill() -> dict[str, int]:
    """Forward-fill remaining NULL implied_vol_30d from most recent prior date."""
    conn = _pg_conn()
    results: dict[str, int] = {}

    for pair, col in (("EURUSD", "euv"), ("USDJPY", "jxv")):
        res = conn.run(
            f"""
            WITH ff AS (
                SELECT
                    s.date AS signal_date,
                    h.{col} AS iv
                FROM signals s
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM historical_implied_vol h2
                    WHERE h2.date <= s.date
                    ORDER BY h2.date DESC
                    LIMIT 1
                ) h ON true
                WHERE s.pair = '{pair}'
                  AND s.implied_vol_30d IS NULL
            )
            UPDATE signals
            SET implied_vol_30d = ff.iv
            FROM ff
            WHERE signals.date = ff.signal_date
              AND signals.pair = '{pair}'
              AND signals.implied_vol_30d IS NULL
            """
        )
        count = res[0][0] if res and len(res) > 0 and len(res[0]) > 0 else 0
        results[pair] = int(count)
        logger.info("Signals forward-fill updated for %s: %s rows", pair, count)

    conn.close()
    return results


def update_signals_eurusd_vix_proxy() -> int:
    """Fill remaining EURUSD implied_vol_30d with VIX for dates before EVZCLS starts."""
    conn = _pg_conn()
    result = conn.run(
        """
        WITH ff AS (
            SELECT
                s.date AS signal_date,
                h.vix AS iv
            FROM signals s
            LEFT JOIN LATERAL (
                SELECT *
                FROM historical_cross_asset h2
                WHERE h2.date <= s.date
                ORDER BY h2.date DESC
                LIMIT 1
            ) h ON true
            WHERE s.pair = 'EURUSD'
              AND s.implied_vol_30d IS NULL
        )
        UPDATE signals
        SET implied_vol_30d = ff.iv
        FROM ff
        WHERE signals.date = ff.signal_date
          AND signals.pair = 'EURUSD'
          AND signals.implied_vol_30d IS NULL
        """
    )
    conn.close()
    count = result[0][0] if result and len(result) > 0 and len(result[0]) > 0 else 0
    logger.info("Signals EURUSD VIX proxy updated: %s rows", count)
    return int(count)


def update_signals_usdinr_proxy() -> int:
    """Set USDINR implied_vol_30d = realized_vol_20d * 1.15."""
    conn = _pg_conn()
    result = conn.run(
        """
        UPDATE signals
        SET implied_vol_30d = realized_vol_20d * 1.15
        WHERE pair = 'USDINR'
          AND implied_vol_30d IS NULL
          AND realized_vol_20d IS NOT NULL
        """
    )
    conn.close()
    count = result[0][0] if result and len(result) > 0 and len(result[0]) > 0 else 0
    logger.info("Signals USDINR proxy updated: %s rows", count)
    return int(count)


def run_backfill() -> dict[str, Any]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _load_env()

    # 1. Create table
    create_table_if_not_exists()

    # 2. Download history — yfinance first, then fallbacks
    euv_hist = fetch_yfinance_history("^EUV", "euv")
    time.sleep(2)
    jxv_hist = fetch_yfinance_history("^JXV", "jxv")
    time.sleep(2)

    failed_tickers: list[str] = []
    fallbacks_used: list[str] = []

    if not euv_hist:
        failed_tickers.append("^EUV")
        euv_hist = fetch_fred_evz()
        if euv_hist:
            fallbacks_used.append("euv <- FRED EVZCLS")
        else:
            logger.error("EURUSD implied vol: yfinance ^EUV failed and FRED fallback failed")

    if not jxv_hist:
        failed_tickers.append("^JXV")
        jxv_hist = fetch_vix_proxy_from_db()
        if jxv_hist:
            fallbacks_used.append("jxv <- VIX (historical_cross_asset)")
        else:
            logger.error("USDJPY implied vol: yfinance ^JXV failed and VIX proxy failed")

    # 3. Align dates and build rows
    all_dates: set[date] = set()
    for hist in (euv_hist, jxv_hist):
        if hist:
            all_dates.update(hist.keys())
    sorted_dates = sorted(all_dates)

    rows: list[dict[str, Any]] = []
    for d in sorted_dates:
        rows.append(
            {
                "date": d,
                "euv": euv_hist.get(d),
                "jxv": jxv_hist.get(d),
            }
        )

    logger.info("Aligned rows to upsert: %d", len(rows))

    # 4. Upsert
    upserted = upsert_rows(rows)

    # 5. Update signals
    exact_counts = update_signals_exact_match()
    ff_counts = update_signals_forward_fill()
    usdinr_count = update_signals_usdinr_proxy()

    # 6. Fallback: EURUSD pre-2007 implied vol from VIX proxy
    eurusd_vix_proxy_count = update_signals_eurusd_vix_proxy()

    # 7. Verify
    conn = _pg_conn()
    verify = conn.run(
        """
        SELECT
            pair,
            COUNT(*) AS total,
            COUNT(implied_vol_30d) AS iv
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
            "iv": row[2],
        }

    return {
        "historical_rows_upserted": upserted,
        "failed_tickers": failed_tickers,
        "fallbacks_used": fallbacks_used,
        "signals_exact_match": exact_counts,
        "signals_forward_fill": ff_counts,
        "signals_usdinr_proxy": usdinr_count,
        "signals_eurusd_vix_proxy": eurusd_vix_proxy_count,
        "verification": verification,
    }


if __name__ == "__main__":
    result = run_backfill()
    print("=" * 60)
    print("IMPLIED VOL BACKFILL SUMMARY")
    print("=" * 60)
    print(f"Historical rows upserted: {result['historical_rows_upserted']}")
    print(f"Failed tickers: {result['failed_tickers'] or 'None'}")
    print(f"Fallbacks used: {result['fallbacks_used'] or 'None'}")
    em = result["signals_exact_match"]
    ff = result["signals_forward_fill"]
    print(
        f"Signals exact-match: EURUSD={em.get('EURUSD', 0)}, "
        f"USDJPY={em.get('USDJPY', 0)}"
    )
    print(
        f"Signals forward-fill: EURUSD={ff.get('EURUSD', 0)}, "
        f"USDJPY={ff.get('USDJPY', 0)}"
    )
    print(f"Signals USDINR proxy: {result['signals_usdinr_proxy']}")
    print(f"Signals EURUSD VIX proxy: {result['signals_eurusd_vix_proxy']}")
    print("Verification:")
    for pair, counts in result["verification"].items():
        print(f"  {pair}: total={counts['total']}, iv={counts['iv']}")
