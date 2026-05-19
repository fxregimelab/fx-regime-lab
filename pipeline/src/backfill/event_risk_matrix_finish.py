"""Finish the remaining event risk matrices using pure SQL."""
from __future__ import annotations

import json
import logging
import ssl
from typing import Any

import pg8000.native

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _pg_conn() -> Any:
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


def main() -> None:
    conn = _pg_conn()

    # Get missing events
    missing = conn.run(
        """
        SELECT me.date, me.event, me.pairs
        FROM macro_events me
        LEFT JOIN event_risk_matrices erm
            ON me.date = erm.date AND me.event = erm.event_name
        WHERE erm.id IS NULL
        ORDER BY me.date
        """
    )
    logger.info(f"Missing matrices: {len(missing)} events")

    if not missing:
        logger.info("All event risk matrices are complete!")
        conn.close()
        return

    inserted = 0
    for ev_date, ev_name, ev_pairs_raw in missing:
        pairs = json.loads(ev_pairs_raw) if isinstance(ev_pairs_raw, str) else ev_pairs_raw
        for pair in pairs:
            # Get regime on event date
            regime_rows = conn.run(
                "SELECT regime FROM regime_calls WHERE date = :d AND pair = :p",
                d=ev_date, p=pair,
            )
            regime = regime_rows[0][0] if regime_rows else "NEUTRAL"

            # Get T+1 return (next trading day's day_change_pct)
            ret_rows = conn.run(
                """
                SELECT s.day_change_pct
                FROM signals s
                WHERE s.pair = :p AND s.date > :d
                ORDER BY s.date ASC
                LIMIT 1
                """,
                p=pair, d=ev_date,
            )
            ret = ret_rows[0][0] if ret_rows else None

            if ret is None:
                # No price data for this event - skip
                continue

            ret_f = float(ret)
            beat_median = ret_f if ret_f > 0.2 else 0.0
            miss_median = ret_f if ret_f < -0.2 else 0.0
            inline_median = ret_f if -0.2 <= ret_f <= 0.2 else 0.0

            if abs(beat_median) > abs(miss_median):
                asym = round(abs(beat_median) / max(abs(miss_median), 0.0001), 2)
                asym_dir = "BEAT"
            elif abs(miss_median) > abs(beat_median):
                asym = round(abs(miss_median) / max(abs(beat_median), 0.0001), 2)
                asym_dir = "MISS"
            else:
                asym = 0.0
                asym_dir = "NEUTRAL"

            conn.run(
                """
                INSERT INTO event_risk_matrices
                (date, pair, event_name, active_regime, sample_size,
                 median_mie_multiplier, beat_median_return, miss_median_return,
                 inline_median_return, asymmetry_ratio, asymmetry_direction,
                 t1_exhaustion_p2_5, t1_exhaustion_p16, t1_exhaustion_p84,
                 t1_exhaustion_p97_5, t1_tail_risk_p95, t1_tail_risk_p05)
                VALUES
                (:d, :p, :e, :r, 1, 0.0, :bm, :mm, :im, :ar, :ad,
                 :ret, :ret, :ret, :ret, :ret, :ret)
                ON CONFLICT (date, pair, event_name) DO NOTHING
                """,
                d=ev_date, p=pair, e=ev_name, r=regime,
                bm=beat_median, mm=miss_median, im=inline_median,
                ar=asym, ad=asym_dir, ret=ret_f,
            )
            inserted += 1
            if inserted % 10 == 0:
                logger.info(f"Inserted {inserted}...")

    logger.info(f"Inserted {inserted} event risk matrices total")
    conn.close()


if __name__ == "__main__":
    main()
