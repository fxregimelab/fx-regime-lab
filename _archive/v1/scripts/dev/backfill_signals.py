#!/usr/bin/env python3
"""
Backfill `signals` from local `data/latest_with_cot.csv` into Supabase (batched upserts).

Usage (from repo root):
  python scripts/dev/backfill_signals.py EURUSD 2025-01-01
  python scripts/dev/backfill_signals.py USDJPY 2025-01-01
  python scripts/dev/backfill_signals.py USDINR 2025-01-01

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment.
Logs completion to pipeline_errors with error_message BACKFILL_COMPLETE.
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
os.chdir(_ROOT)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import TODAY  # noqa: E402
from core.paths import DATA_DIR, LATEST_WITH_COT_CSV  # noqa: E402
from core.signal_write import _row_to_signal, log_pipeline_error  # noqa: E402
from core.supabase_client import get_client  # noqa: E402

VALID_PAIRS = frozenset({"EURUSD", "USDJPY", "USDINR"})
BATCH = 100


def _spot_col(pair: str) -> str:
    return {"EURUSD": "EURUSD", "USDJPY": "USDJPY", "USDINR": "USDINR"}[pair]


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill signals table from master CSV")
    p.add_argument("pair", type=str.upper, help="EURUSD | USDJPY | USDINR")
    p.add_argument("start_date", type=str, help="YYYY-MM-DD inclusive")
    args = p.parse_args()
    pair = args.pair.strip().upper()
    if pair not in VALID_PAIRS:
        print(f"Invalid pair {pair!r}; use one of {sorted(VALID_PAIRS)}", file=sys.stderr)
        return 2

    try:
        start = pd.Timestamp(args.start_date)
    except Exception as e:
        print(f"Bad start_date: {e}", file=sys.stderr)
        return 2

    if supabase is None:
        print("Supabase client not configured (set SUPABASE_URL and key).", file=sys.stderr)
        return 1

    path = LATEST_WITH_COT_CSV
    if not os.path.isfile(path):
        alt = os.path.join(DATA_DIR, "latest_with_cot.csv")
        path = alt if os.path.isfile(alt) else path
    if not os.path.isfile(path):
        print(f"Missing master CSV: {path}", file=sys.stderr)
        return 1

    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if df.empty:
        print("Master CSV is empty.", file=sys.stderr)
        return 1

    spot = _spot_col(pair)
    if spot not in df.columns:
        print(f"Column {spot!r} not in master CSV.", file=sys.stderr)
        return 1

    sub = df.loc[df.index >= start].dropna(subset=[spot], how="any")
    rows_out: list[dict] = []
    for idx, row in sub.iterrows():
        as_of = pd.Timestamp(idx).strftime("%Y-%m-%d")
        rows_out.append(_row_to_signal(pair, row, as_of))

    if not rows_out:
        print("No rows in range after filtering; nothing to upsert.")
        log_pipeline_error(
            "backfill_signals",
            "BACKFILL_COMPLETE",
            pair=pair,
            notes=f"start={args.start_date} upserted=0 (no rows)",
        )
        return 0

    for i in range(0, len(rows_out), BATCH):
        batch = rows_out[i : i + BATCH]
        try:
            client.table("signals").upsert(batch, on_conflict="date,pair").execute()
        except Exception as e:
            log_pipeline_error(
                "backfill_signals",
                str(e),
                pair=pair,
                notes=f"batch offset {i}",
            )
            print(f"Upsert failed at offset {i}: {e}", file=sys.stderr)
            return 1

    print(f"Upserted {len(rows_out)} rows for {pair} from {args.start_date} (CSV trading days in range).")
    log_pipeline_error(
        "backfill_signals",
        "BACKFILL_COMPLETE",
        pair=pair,
        notes=f"start={args.start_date} upserted={len(rows_out)} as_of_run={TODAY}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
