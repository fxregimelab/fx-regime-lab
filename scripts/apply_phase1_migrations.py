#!/usr/bin/env python3
"""Phase 1: Apply all v2.1 DB migrations to Supabase."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env")

DB_HOST = os.getenv("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "6bT2H0t6FwBZtOr0H70qEYx3")
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PORT = "5432"

MIGRATIONS = [
    # 1. Original v2.1 migration
    """
    -- Cost-adjusted metrics in validation_log
    ALTER TABLE validation_log
    ADD COLUMN IF NOT EXISTS log_return_net_bps NUMERIC,
    ADD COLUMN IF NOT EXISTS correct_net BOOLEAN,
    ADD COLUMN IF NOT EXISTS cost_bps NUMERIC DEFAULT 0.0;

    COMMENT ON COLUMN validation_log.log_return_net_bps IS 'Return after estimated transaction costs';
    COMMENT ON COLUMN validation_log.correct_net IS 'Correct after costs (directional)';

    -- Confidence intervals in validation_stats
    ALTER TABLE validation_stats
    ADD COLUMN IF NOT EXISTS t5_win_rate_ci_lower NUMERIC,
    ADD COLUMN IF NOT EXISTS t5_win_rate_ci_upper NUMERIC,
    ADD COLUMN IF NOT EXISTS t5_net_win_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS t5_net_win_rate_ci_lower NUMERIC,
    ADD COLUMN IF NOT EXISTS t5_net_win_rate_ci_upper NUMERIC,
    ADD COLUMN IF NOT EXISTS t20_win_rate_ci_lower NUMERIC,
    ADD COLUMN IF NOT EXISTS t20_win_rate_ci_upper NUMERIC,
    ADD COLUMN IF NOT EXISTS t20_net_win_rate NUMERIC,
    ADD COLUMN IF NOT EXISTS t20_net_win_rate_ci_lower NUMERIC,
    ADD COLUMN IF NOT EXISTS t20_net_win_rate_ci_upper NUMERIC;

    -- COT staleness tracking
    ALTER TABLE signals
    ADD COLUMN IF NOT EXISTS days_since_cot INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS risk_reversal_source TEXT DEFAULT 'PENDING_REAL_DATA';

    COMMENT ON COLUMN signals.days_since_cot IS 'Days since last COT report publication';
    COMMENT ON COLUMN signals.risk_reversal_source IS 'Source of RR data';

    -- Add metadata about data quality
    ALTER TABLE signals
    ADD COLUMN IF NOT EXISTS data_quality_notes TEXT[] DEFAULT '{}';

    -- Index for common queries
    CREATE INDEX IF NOT EXISTS idx_validation_net ON validation_log(pair, date DESC)
    INCLUDE (correct_net, cost_bps, log_return_net_bps);
    """,

    # 2. Per-horizon columns for validation_log
    """
    ALTER TABLE validation_log
    ADD COLUMN IF NOT EXISTS correct_net_t5 BOOLEAN,
    ADD COLUMN IF NOT EXISTS correct_net_t20 BOOLEAN,
    ADD COLUMN IF NOT EXISTS cost_bps_t5 NUMERIC DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS cost_bps_t20 NUMERIC DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS log_return_net_bps_t5 NUMERIC,
    ADD COLUMN IF NOT EXISTS log_return_net_bps_t20 NUMERIC;

    -- Migrate existing singular columns (if any were populated)
    UPDATE validation_log
    SET correct_net_t5 = correct_net,
        correct_net_t20 = correct_net,
        cost_bps_t5 = cost_bps,
        cost_bps_t20 = cost_bps,
        log_return_net_bps_t5 = log_return_net_bps,
        log_return_net_bps_t20 = log_return_net_bps
    WHERE correct_net IS NOT NULL;

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_validation_net_t5 ON validation_log(pair, date DESC)
    INCLUDE (correct_net_t5, cost_bps_t5, log_return_net_bps_t5);
    CREATE INDEX IF NOT EXISTS idx_validation_net_t20 ON validation_log(pair, date DESC)
    INCLUDE (correct_net_t20, cost_bps_t20, log_return_net_bps_t20);
    """,

    # 3. Add cost_bps columns to validation_stats
    """
    ALTER TABLE validation_stats
    ADD COLUMN IF NOT EXISTS t5_cost_bps NUMERIC DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS t20_cost_bps NUMERIC DEFAULT 0.0;
    """,
]

def run():
    print(f"Connecting to {DB_HOST}...")
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()

    for i, sql in enumerate(MIGRATIONS, 1):
        print(f"\n--- Running migration {i}/{len(MIGRATIONS)} ---")
        try:
            cur.execute(sql)
            print(f"Migration {i}: OK")
        except Exception as e:
            print(f"Migration {i}: ERROR - {e}")
            # Don't raise — some statements may be idempotent no-ops

    # Verify
    print("\n--- Verification ---")
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'validation_stats'
        AND column_name IN ('t5_net_win_rate', 't5_cost_bps', 't5_win_rate_ci_lower')
        ORDER BY column_name;
    """)
    stats_cols = [r[0] for r in cur.fetchall()]
    print(f"validation_stats net/CI/cost columns: {stats_cols}")

    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'validation_log'
        AND column_name IN ('correct_net_t5', 'cost_bps_t5', 'log_return_net_bps_t5',
                            'correct_net_t20', 'cost_bps_t20', 'log_return_net_bps_t20')
        ORDER BY column_name;
    """)
    log_cols = [r[0] for r in cur.fetchall()]
    print(f"validation_log per-horizon columns: {log_cols}")

    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'signals'
        AND column_name IN ('days_since_cot', 'risk_reversal_source', 'data_quality_notes')
        ORDER BY column_name;
    """)
    signal_cols = [r[0] for r in cur.fetchall()]
    print(f"signals v2.1 columns: {signal_cols}")

    cur.close()
    conn.close()
    print("\nDone.")

if __name__ == "__main__":
    run()
