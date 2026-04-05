# Run once from repo root after Supabase schema is confirmed:
#   python scripts/backfill_supabase.py
#   python scripts/backfill_cot.py
#   python scripts/backfill_inr.py
# These are safe to re-run (upsert, not insert).
# After running, verify row counts in Supabase dashboard.
#
# INR-specific columns (FPI, RBI reserves, etc.) live on the merged master after
# inr_pipeline.py. This script upserts the same `signals` rows as backfill_supabase
# so USDINR rate_diff_* and vol fields are populated where present.
"""Backfill `signals` including USD/INR fields from merged master (same as backfill_supabase)."""

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
