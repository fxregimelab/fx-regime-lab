# vol_pipeline.py
# Phase 3 — CME CVOL EOD implied-vol integration for EUR/USD and USD/JPY.
#
# Writes data/vol_latest.csv (CSV fallback, always) and Supabase `signals`
# table columns implied_vol_30d, vol_skew, atm_vol. USD/INR has no listed CME
# FX options product, so it stays NULL here — the composite falls back to
# realized_vol_20d percentile in pipeline.merge_main (INR branch).

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import List

import pandas as pd
import requests

from config import CME_CVOL_BASE, CME_CVOL_PRODUCTS
from core.paths import DATA_DIR
from core.signal_write import log_pipeline_error
from core.supabase_client import get_client


"""
CME CVOL implied volatility Pipeline.

Execution context:
- Called by run.py as STEP 4 (vol)
- Depends on: inr_pipeline.py
- Outputs: Supabase signals table (vol signals) + data/vol_latest.csv
- Next step: oi_pipeline.py
- Blocking: YES (hard-coded in run.py STEPS) — main() must ALWAYS sys.exit(0)

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""


_VOL_LATEST_CSV = os.path.join(DATA_DIR, "vol_latest.csv")


def _fetch_cvol(pair: str, product: str, api_key: str) -> pd.DataFrame:
    """Fetch 1Y of CVOL EOD data for a single product. Returns empty on failure."""
    end = datetime.today().strftime("%Y%m%d")
    start = (datetime.today() - timedelta(days=365)).strftime("%Y%m%d")
    url = f"{CME_CVOL_BASE}/{product}/{start}/{end}"
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=30,
        )
        r.raise_for_status()
        js = r.json()
    except Exception as e:
        log_pipeline_error("vol_pipeline", f"{product} fetch: {e}", pair=pair, notes="cvol_http")
        return pd.DataFrame()

    data = js.get("data") if isinstance(js, dict) else js
    if not data:
        return pd.DataFrame()
    try:
        df = pd.DataFrame(data)
    except Exception as e:
        log_pipeline_error("vol_pipeline", f"{product} parse: {e}", pair=pair, notes="cvol_parse")
        return pd.DataFrame()

    # Expected CVOL EOD columns: date, cvol, atm_vol, up_var, dn_var, skew
    if "date" not in df.columns:
        log_pipeline_error("vol_pipeline", f"{product} missing 'date' column", pair=pair)
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["date"])

    out = pd.DataFrame({"date": df["date"], "pair": pair})
    # implied_vol_30d → prefer explicit "cvol" field; fall back to atm_vol
    if "cvol" in df.columns:
        out["implied_vol_30d"] = pd.to_numeric(df["cvol"], errors="coerce")
    elif "atm_vol" in df.columns:
        out["implied_vol_30d"] = pd.to_numeric(df["atm_vol"], errors="coerce")
    else:
        out["implied_vol_30d"] = pd.NA
    # vol_skew: up_var minus dn_var (positive = upside wings richer)
    if "up_var" in df.columns and "dn_var" in df.columns:
        out["vol_skew"] = (
            pd.to_numeric(df["up_var"], errors="coerce")
            - pd.to_numeric(df["dn_var"], errors="coerce")
        )
    elif "skew" in df.columns:
        out["vol_skew"] = pd.to_numeric(df["skew"], errors="coerce")
    else:
        out["vol_skew"] = pd.NA
    if "atm_vol" in df.columns:
        out["atm_vol"] = pd.to_numeric(df["atm_vol"], errors="coerce")
    else:
        out["atm_vol"] = pd.NA
    return out.dropna(subset=["implied_vol_30d"], how="all")


def _write_csv(out: pd.DataFrame) -> None:
    """Always overwrite data/vol_latest.csv so merge_main picks up fresh data."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = _VOL_LATEST_CSV + ".tmp"
    out.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, _VOL_LATEST_CSV)
    print(f"  vol_pipeline: wrote {_VOL_LATEST_CSV} ({len(out)} rows)")


def _upsert_signals(out: pd.DataFrame) -> None:
    """Upsert last 260 rows per pair to Supabase signals on (date, pair)."""
    cli = get_client()
    if cli is None:
        print("  vol_pipeline: Supabase client unavailable — CSV only")
        return
    try:
        for pair, grp in out.groupby("pair"):
            rows: List[dict] = (
                grp.sort_values("date")
                .tail(260)
                .where(pd.notna(grp), None)
                .to_dict("records")
            )
            # Drop NaN/NA values per row to avoid Supabase JSON error
            cleaned = []
            for r in rows:
                cleaned.append(
                    {k: v for k, v in r.items() if v is not None and not (isinstance(v, float) and pd.isna(v))}
                )
            if cleaned:
                cli.table("signals").upsert(cleaned, on_conflict="date,pair").execute()
                print(f"  vol_pipeline: upserted {len(cleaned)} rows for {pair}")
    except Exception as e:
        log_pipeline_error("vol_pipeline", str(e), notes="signals upsert")


def main() -> None:
    print("  vol_pipeline: CME CVOL EOD integration (Phase 3)")
    api_key = os.environ.get("CME_API_KEY", "").strip()
    if not api_key:
        print("  vol_pipeline: CME_API_KEY not set — writing empty vol_latest.csv")
        _write_csv(pd.DataFrame(columns=["date", "pair", "implied_vol_30d", "vol_skew", "atm_vol"]))
        return

    frames = []
    for pair, product in CME_CVOL_PRODUCTS.items():
        df = _fetch_cvol(pair, product, api_key)
        if df.empty:
            print(f"  vol_pipeline: no CVOL data for {pair} ({product})")
            continue
        frames.append(df)

    if not frames:
        print("  vol_pipeline: no CVOL frames — writing empty CSV")
        _write_csv(pd.DataFrame(columns=["date", "pair", "implied_vol_30d", "vol_skew", "atm_vol"]))
        return

    out = pd.concat(frames, ignore_index=True)
    _write_csv(out)
    _upsert_signals(out)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"  vol_pipeline: unexpected error — {e}")
        try:
            log_pipeline_error("vol_pipeline", str(e), notes="main")
        except Exception:
            pass
    sys.exit(0)
