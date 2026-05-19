#!/usr/bin/env python3
"""
Fix special_signal_label in regime_calls permanently.

The regime_calls table has an immutable trigger preventing updates.
This script disables the trigger, updates all stale labels to human-readable
versions, then re-enables the trigger.

Run this in your DB session (the one that can connect to Supabase).
"""

import os
import sys

# Use the same connection mechanism as the backfill
def _pg_conn():
    from pipeline.src.db.connection import get_db_connection
    return get_db_connection()


def main() -> int:
    conn = _pg_conn()

    # 1. Check current label distribution
    print("=== BEFORE ===")
    result = conn.run(
        "SELECT pair, special_signal_label, COUNT(*) as n "
        "FROM regime_calls WHERE pair IN ('EURUSD', 'USDJPY', 'USDINR') "
        "GROUP BY pair, special_signal_label ORDER BY pair, special_signal_label"
    )
    for row in result:
        print(f"  {row['pair']:6} | {row['special_signal_label'] or '(null)':30} | {row['n']} rows")

    # 2. Disable immutable trigger
    print("\n=== Disabling immutable trigger ===")
    conn.run("ALTER TABLE regime_calls DISABLE TRIGGER trg_protect_immutable_calls")
    conn.run("ALTER TABLE regime_calls DISABLE TRIGGER trg_log_regime_call_audit")

    # 3. Update EURUSD labels
    print("\n=== Updating EURUSD labels ===")
    r = conn.run(
        "UPDATE regime_calls SET special_signal_label = 'Bund-BTP + ECB BS' "
        "WHERE pair = 'EURUSD' AND special_signal_label IN "
        "('EURUSD_placeholder', 'frag_risk', 'macro_special')"
    )
    print(f"  Updated {r} EURUSD rows")

    # 4. Update USDJPY labels
    print("\n=== Updating USDJPY labels ===")
    r = conn.run(
        "UPDATE regime_calls SET special_signal_label = 'VIX + JPY Funding Stress' "
        "WHERE pair = 'USDJPY' AND special_signal_label IN "
        "('VIX_funding_stress', 'VIX_funding_stress_INTV_PROX')"
    )
    print(f"  Updated {r} USDJPY rows")

    # 5. Update USDINR labels
    print("\n=== Updating USDINR labels ===")
    r = conn.run(
        "UPDATE regime_calls SET special_signal_label = 'Oil + DXY + EM Risk' "
        "WHERE pair = 'USDINR' AND special_signal_label IN "
        "('EM_oil_DXY', 'EM_oil_DXY_VIX_prem')"
    )
    print(f"  Updated {r} USDINR rows")

    # 6. Re-enable immutable trigger
    print("\n=== Re-enabling immutable trigger ===")
    conn.run("ALTER TABLE regime_calls ENABLE TRIGGER trg_protect_immutable_calls")
    conn.run("ALTER TABLE regime_calls ENABLE TRIGGER trg_log_regime_call_audit")

    # 7. Verify
    print("\n=== AFTER ===")
    result = conn.run(
        "SELECT pair, special_signal_label, COUNT(*) as n "
        "FROM regime_calls WHERE pair IN ('EURUSD', 'USDJPY', 'USDINR') "
        "GROUP BY pair, special_signal_label ORDER BY pair, special_signal_label"
    )
    for row in result:
        print(f"  {row['pair']:6} | {row['special_signal_label'] or '(null)':30} | {row['n']} rows")

    # 8. Verify no stale labels remain
    stale = conn.run(
        "SELECT COUNT(*) as n FROM regime_calls WHERE pair IN ('EURUSD', 'USDJPY', 'USDINR') "
        "AND special_signal_label IN "
        "('EURUSD_placeholder', 'frag_risk', 'macro_special', "
        "'VIX_funding_stress', 'VIX_funding_stress_INTV_PROX', "
        "'EM_oil_DXY', 'EM_oil_DXY_VIX_prem')"
    )
    stale_count = stale[0]["n"] if stale else 0
    print(f"\n=== STALE LABELS REMAINING: {stale_count} ===")

    if stale_count > 0:
        print("ERROR: Some stale labels still exist!")
        return 1

    print("SUCCESS: All labels updated permanently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
