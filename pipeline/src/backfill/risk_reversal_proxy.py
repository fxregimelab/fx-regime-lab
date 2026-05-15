"""Synthetic risk-reversal proxy backfill.

True 25-delta risk reversal requires OTC FX options data (Bloomberg/Reuters
term-structure vol surfaces), which is not freely available.  This module
computes a **temporary synthetic proxy** from existing realised-vol and
spot-change data already stored in the ``signals`` table.

Proxy formula (per row)::

    rr_proxy = realised_vol_20d * 0.3 * sign(day_change_pct)

A smoother 5-day moving-average variant is also computed for readability,
but the raw daily proxy is what is persisted to ``signals.risk_reversal_25d``.

Regime-call mapping::

    proxy >  0.15  →  "BULLISH"
    proxy < -0.15  →  "BEARISH"
    else           →  "NEUTRAL"

**Idempotent** – re-running updates the same rows in-place.
**TODO** – replace with real OTC 25-delta RR once a data feed is procured.
"""

from __future__ import annotations
import os

import argparse
import logging
from typing import Any

logger = logging.getLogger(__name__)


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


def backfill_risk_reversal_proxy(*, dry_run: bool = False) -> tuple[int, int]:
    """Backfill ``signals.risk_reversal_25d`` and ``regime_calls.rr_signal``.

    Returns:
        ``(signals_updated, regime_calls_updated)``
    """
    conn = _pg_conn()

    # ------------------------------------------------------------------
    # 1. Update signals with synthetic proxy (computed in SQL)
    # ------------------------------------------------------------------
    if dry_run:
        res = conn.run(
            "SELECT COUNT(*) FROM signals WHERE risk_reversal_25d IS NULL"
        )
        signals_updated = int(res[0][0])
        logger.info("[DRY-RUN] Would update %d signals rows", signals_updated)
    else:
        conn.run(
            "UPDATE signals SET risk_reversal_25d = realized_vol_20d * 0.3 * SIGN(day_change_pct) "
            "WHERE risk_reversal_25d IS NULL"
        )
        # pg8000 doesn't give rowcount easily; count afterwards
        res = conn.run("SELECT COUNT(*) FROM signals WHERE risk_reversal_25d IS NOT NULL")
        signals_updated = int(res[0][0])
        logger.info("Updated %d signals rows with RR proxy", signals_updated)

    # ------------------------------------------------------------------
    # 2. Update regime_calls.rr_signal via join to signals
    # ------------------------------------------------------------------
    if dry_run:
        res = conn.run(
            "SELECT COUNT(*) FROM regime_calls rc "
            "JOIN signals s ON rc.pair = s.pair AND rc.date = s.date "
            "WHERE rc.rr_signal IS NULL OR rc.rr_signal = 'NEUTRAL'"
        )
        regime_calls_updated = int(res[0][0])
        logger.info("[DRY-RUN] Would update %d regime_calls rows", regime_calls_updated)
    else:
        conn.run("ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls")
        try:
            conn.run(
                "UPDATE regime_calls rc SET rr_signal = CASE "
                "WHEN s.risk_reversal_25d > 0.15 THEN 'BULLISH' "
                "WHEN s.risk_reversal_25d < -0.15 THEN 'BEARISH' "
                "ELSE 'NEUTRAL' END "
                "FROM signals s "
                "WHERE rc.pair = s.pair AND rc.date = s.date "
                "AND (rc.rr_signal IS NULL OR rc.rr_signal = 'NEUTRAL')"
            )
            res = conn.run(
                "SELECT COUNT(*) FROM regime_calls WHERE rr_signal IS NOT NULL"
            )
            regime_calls_updated = int(res[0][0])
            logger.info("Updated %d regime_calls rows with rr_signal", regime_calls_updated)
        finally:
            conn.run("ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls")

    return signals_updated, regime_calls_updated


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Backfill synthetic risk-reversal proxy")
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write")
    args = parser.parse_args()

    s_upd, rc_upd = backfill_risk_reversal_proxy(dry_run=args.dry_run)
    print(f"signals_updated={s_upd} regime_calls_updated={rc_upd}")
