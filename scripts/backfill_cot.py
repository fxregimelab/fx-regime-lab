# Run once from repo root after Supabase schema is confirmed:
#   python scripts/backfill_supabase.py
#   python scripts/backfill_cot.py
#   python scripts/backfill_inr.py
# These are safe to re-run (upsert, not insert).
# After running, verify row counts in Supabase dashboard.
#
# COT positioning is forward-filled onto the daily master in cot_pipeline.py.
# This script uses data/latest_with_cot.csv (not raw cot_latest.csv alone) so each
# trading day gets cot_lev_money_net, cot_asset_mgr_net, cot_percentile on `signals`.
"""Backfill `signals` COT-related columns via merged daily master (same as backfill_supabase)."""

from __future__ import annotations

import os
import runpy
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(_root / ".env", override=True)
except ImportError:
    pass

_dir = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(_dir, "backfill_supabase.py"), run_name="__main__")
