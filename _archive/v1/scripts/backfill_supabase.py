# Run once from repo root after Supabase schema is confirmed:
#   python scripts/backfill_supabase.py
#   python scripts/backfill_cot.py
#   python scripts/backfill_inr.py
# These are safe to re-run (upsert, not insert).
# After running, verify row counts in Supabase dashboard.
#
# Master CSV columns (reference — see data/latest_with_cot.csv after a full pipeline run):
#   Index: date
#   FX: EURUSD, USDJPY, USDINR, DXY, Brent, Gold (optional VIX if present)
#   Spreads: US_DE_2Y_spread, US_DE_10Y_spread, US_JP_2Y_spread, US_JP_10Y_spread,
#            US_IN_policy_spread, US_IN_10Y_spread
#   COT (ffilled): EUR_lev_net, EUR_assetmgr_net, EUR_lev_percentile,
#                  JPY_lev_net, JPY_assetmgr_net, JPY_lev_percentile
#   Vol: EURUSD_vol30, USDJPY_vol30, USDINR_vol30
"""Backfill `signals` from merged master CSV (full history, chunked upserts)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env", override=True)
except ImportError:
    pass

os.chdir(_ROOT)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.paths import LATEST_WITH_COT_CSV  # noqa: E402
from core.signal_write import build_all_signal_rows, log_pipeline_error  # noqa: E402
from core.supabase_client import get_client  # noqa: E402

CHUNK = 100


def backfill_signals() -> None:
    client = get_client()
    if not client:
        print("No Supabase client — check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return
    path = LATEST_WITH_COT_CSV
    if not os.path.isfile(path):
        print(f"Missing {path}")
        return
    rows = build_all_signal_rows(path)
    if not rows:
        print("No rows built from master CSV")
        return
    for i in range(0, len(rows), CHUNK):
        chunk = rows[i : i + CHUNK]
        try:
            client.table("signals").upsert(chunk, on_conflict="date,pair").execute()
            print(f"[Backfill] Upserted rows {i}–{i + len(chunk)}")
        except Exception as e:
            print(f"[Backfill] Error at chunk {i}: {e}")
            log_pipeline_error("backfill_supabase", str(e), notes=f"offset {i}")
            return
    print("[Backfill] Complete")


if __name__ == "__main__":
    backfill_signals()
