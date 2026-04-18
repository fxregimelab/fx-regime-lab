#!/usr/bin/env python3
"""
Operator sanity check: last row of data/latest_with_cot.csv vs Supabase signals,
plus optional shape checks for regime_calls, brief_log, validation_log.

Run from repo root:  python scripts/dev/verify_data_supabase_brief.py [--warn-only]

Requires .env with Supabase for remote comparison; CSV-only summary works without keys.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import pandas as pd

from config import TODAY
from core.paths import LATEST_WITH_COT_CSV
from core.signal_write import build_signal_rows_for_latest_master
from core.supabase_client import get_client

PAIRS = ("EURUSD", "USDJPY", "USDINR")
_FLOAT_RTOL = 1e-4
_FLOAT_ATOL = 1e-5


def _close(a: object, b: object) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, str) or isinstance(b, str):
        return str(a).strip() == str(b).strip()
    try:
        fa = float(a)
        fb = float(b)
    except (TypeError, ValueError):
        return a == b
    if math.isnan(fa) and math.isnan(fb):
        return True
    return math.isclose(fa, fb, rel_tol=_FLOAT_RTOL, abs_tol=_FLOAT_ATOL)


def _compare_expected_to_db(
    expected: dict,
    db_row: dict,
    *,
    pair: str,
    warn_only: bool,
) -> list[str]:
    errors: list[str] = []
    for k, ev in expected.items():
        if k in ("date", "pair"):
            continue
        if k not in db_row or db_row[k] is None:
            if ev is None or (isinstance(ev, float) and pd.isna(ev)):
                continue
            errors.append(f"  {pair} missing DB key {k!r} (CSV has value)")
            continue
        dv = db_row[k]
        if not _close(ev, dv):
            errors.append(f"  {pair} {k}: CSV/signal_write={ev!r} vs DB={dv!r}")
    for k in db_row:
        if k in ("id", "created_at", "date", "pair"):
            continue
        if k not in expected and db_row[k] is not None:
            pass  # DB may retain columns from prior writes; not an error
    for msg in errors:
        print(msg)
    if errors and not warn_only:
        return errors
    return []


def _check_regime_brief_validation(cli, _warn_only: bool) -> None:
    if cli is None:
        return
    try:
        r = (
            cli.table("regime_calls")
            .select("pair, date, regime, confidence, primary_driver")
            .order("date", desc=True)
            .limit(3)
            .execute()
        )
        rows = getattr(r, "data", None) or []
        print(f"  regime_calls sample rows: {len(rows)}")
        for row in rows[:3]:
            print(f"    {row}")
        if not rows:
            print("  WARN: regime_calls empty (home cards will show stale/offline)")
    except Exception as e:
        print(f"  regime_calls probe: {e}")
    try:
        r = (
            cli.table("brief_log")
            .select("date, brief_text, eurusd_regime, usdjpy_regime, usdinr_regime, macro_context")
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(r, "data", None) or []
        print(f"  brief_log latest: {'yes' if rows else 'none'}")
    except Exception as e:
        print(f"  brief_log probe: {e}")
    try:
        r = (
            cli.table("validation_log")
            .select("date,pair,correct_1d")
            .order("date", desc=True)
            .limit(5)
            .execute()
        )
        rows = getattr(r, "data", None) or []
        print(f"  validation_log sample: {len(rows)} rows")
    except Exception as e:
        print(f"  validation_log probe: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CSV vs Supabase terminal data check")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Print mismatches but always exit 0",
    )
    args = parser.parse_args()
    warn_only = args.warn_only

    if not os.path.isfile(LATEST_WITH_COT_CSV):
        print(f"ERROR: missing {LATEST_WITH_COT_CSV}")
        return 1

    df = pd.read_csv(LATEST_WITH_COT_CSV, index_col=0, parse_dates=True)
    if df.empty:
        print("ERROR: master CSV has no rows")
        return 1

    last = df.iloc[-1]
    last_date = df.index[-1]
    d = str(last_date.date()) if hasattr(last_date, "date") else str(last_date)[:10]
    print(f"Last row date (index): {last_date}  |  config TODAY: {TODAY}")
    for p in PAIRS:
        v = last.get(p)
        print(f"  {p} spot: {v}")

    cli = get_client()
    if cli is None:
        print("(Supabase client unavailable — skip DB comparison)")
        return 0

    expected_rows = build_signal_rows_for_latest_master(LATEST_WITH_COT_CSV, as_of=d)
    by_pair = {r["pair"]: r for r in expected_rows}

    SIGNAL_SELECT = (
        "date,pair,spot,rate_diff_2y,rate_diff_10y,rate_diff_zscore,"
        "cot_lev_money_net,cot_asset_mgr_net,cot_percentile,"
        "realized_vol_5d,realized_vol_20d,implied_vol_30d,vol_skew,atm_vol,"
        "oi_delta,oi_price_alignment,risk_reversal_25d,"
        "cross_asset_dxy,cross_asset_oil,cross_asset_vix"
    )

    exit_code = 0
    for pair in PAIRS:
        exp = by_pair.get(pair)
        if not exp:
            print(f"  SKIP {pair}: not built from master (missing spot?)")
            continue
        try:
            res = (
                cli.table("signals")
                .select(SIGNAL_SELECT)
                .eq("pair", pair)
                .eq("date", d)
                .limit(1)
                .execute()
            )
            rows = getattr(res, "data", None) or []
            db_row = rows[0] if rows else None
            print(f"  Supabase signals row for {pair} @ {d}: {'found' if db_row else 'NONE'}")
            if not db_row:
                print(f"    ERROR: no signals row for {pair} @ {d}")
                if not warn_only:
                    exit_code = 1
                continue
            errs = _compare_expected_to_db(exp, db_row, pair=pair, warn_only=warn_only)
            if errs and not warn_only:
                exit_code = 1
        except Exception as e:
            print(f"  Supabase query {pair}: {e}")
            if not warn_only:
                exit_code = 1

    print("\n--- regime_calls / brief_log / validation_log (terminal shape) ---")
    _check_regime_brief_validation(cli, warn_only)

    return 0 if warn_only else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
