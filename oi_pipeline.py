# oi_pipeline.py
# Phase 4 — CME daily Volume/OI report scrape for EUR/USD (6E) and USD/JPY (6J).
#
# Writes:
#   data/oi_history.csv   — append-only rolling OI ledger (used to compute deltas)
#   data/oi_latest.csv    — sidecar picked up by pipeline.merge_main()
#   Supabase signals.{oi_delta, oi_price_alignment}
#
# Never raises into run.py — main() always sys.exit(0).

from __future__ import annotations

import io
import os
import sys
from datetime import datetime, timedelta
from typing import List

import numpy as np
import pandas as pd
import requests

from config import CME_OI_URL, CME_OI_PRODUCT_IDS, OI_NOISE, PX_NOISE
from core.paths import DATA_DIR, LATEST_WITH_COT_CSV
from core.signal_write import log_pipeline_error
from core.supabase_client import get_client


"""
CME FX open interest Pipeline.

Execution context:
- Called by run.py as STEP 5 (oi)
- Depends on: vol_pipeline.py
- Outputs: Supabase signals table (OI signals) + data/oi_latest.csv
- Next step: rr_pipeline.py
- Blocking: YES — pipeline halts on failure, so main() must ALWAYS sys.exit(0)

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""


_OI_HISTORY_CSV = os.path.join(DATA_DIR, "oi_history.csv")
_OI_LATEST_CSV = os.path.join(DATA_DIR, "oi_latest.csv")


def _fetch_oi_report(trade_date: datetime) -> pd.DataFrame:
    """Download CME Volume/OI report for a trade date. Empty on any failure."""
    params = {
        "tradeDate": trade_date.strftime("%Y%m%d"),
        "reportType": "VOLUME_OI",
        "productIds": ",".join(CME_OI_PRODUCT_IDS.values()),
    }
    try:
        r = requests.get(
            CME_OI_URL,
            params=params,
            timeout=30,
            headers={"User-Agent": "fxregimelab/1.0"},
        )
        r.raise_for_status()
        text = r.text
    except Exception as e:
        log_pipeline_error("oi_pipeline", f"fetch {trade_date.date()}: {e}", notes="cme_oi_http")
        return pd.DataFrame()
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        log_pipeline_error("oi_pipeline", f"parse {trade_date.date()}: {e}", notes="cme_oi_csv")
        return pd.DataFrame()
    return df


def _normalise_oi_frame(raw: pd.DataFrame, trade_date: datetime) -> pd.DataFrame:
    """Return columns (date, pair, oi_total, close) from a CME report frame."""
    if raw is None or raw.empty:
        return pd.DataFrame()
    # CME report headers vary; pick whichever common aliases are present
    col_pair = next((c for c in raw.columns if str(c).strip().lower() in ("productcode", "product code", "product")), None)
    col_oi = next((c for c in raw.columns if "oi" in str(c).lower() and "total" in str(c).lower()), None)
    if col_oi is None:
        col_oi = next((c for c in raw.columns if str(c).strip().lower() in ("open interest", "openinterest", "oi")), None)
    col_close = next((c for c in raw.columns if str(c).strip().lower() in ("settle", "settlement", "close")), None)
    if col_pair is None or col_oi is None:
        return pd.DataFrame()
    # Map CME product codes (6E / 6J) back to canonical pair strings
    reverse = {v: k for k, v in CME_OI_PRODUCT_IDS.items()}
    df = pd.DataFrame({
        "pair_code": raw[col_pair].astype(str).str.strip(),
        "oi_total": pd.to_numeric(raw[col_oi], errors="coerce"),
        "close": pd.to_numeric(raw[col_close], errors="coerce") if col_close else np.nan,
    })
    df = df[df["pair_code"].isin(reverse.keys())]
    df["pair"] = df["pair_code"].map(reverse)
    df["date"] = trade_date.strftime("%Y-%m-%d")
    return df.groupby(["date", "pair"], as_index=False).agg({
        "oi_total": "sum",
        "close": "mean",
    })


def _classify_alignment(oi_delta, oi_prev, px_delta, close_prev) -> str:
    """Noise-filtered alignment label: confirming / diverging / neutral."""
    try:
        if pd.isna(oi_delta) or pd.isna(oi_prev) or oi_prev == 0:
            return "neutral"
        if abs(oi_delta) / max(abs(oi_prev), 1) < OI_NOISE:
            return "neutral"
        if pd.isna(px_delta) or pd.isna(close_prev) or close_prev == 0:
            return "neutral"
        if abs(px_delta) / max(abs(close_prev), 1e-9) < PX_NOISE:
            return "neutral"
        # OI rising with price: confirming. OI rising with price falling: diverging.
        # OI falling: opposite (unwind against or with price).
        if np.sign(oi_delta) == np.sign(px_delta):
            return "confirming"
        return "diverging"
    except Exception:
        return "neutral"


def _fill_close_from_master(df: pd.DataFrame) -> pd.DataFrame:
    """Backfill missing close prices from data/latest_with_cot.csv."""
    if df.empty:
        return df
    if not os.path.exists(LATEST_WITH_COT_CSV):
        return df
    try:
        master = pd.read_csv(LATEST_WITH_COT_CSV, index_col=0, parse_dates=True)
    except Exception:
        return df
    for pair in df["pair"].unique():
        col = pair if pair in master.columns else None
        if not col:
            continue
        for i, r in df[df["pair"] == pair].iterrows():
            if pd.notna(r["close"]):
                continue
            ts = pd.Timestamp(r["date"])
            if ts in master.index and pd.notna(master.at[ts, col]):
                df.at[i, "close"] = float(master.at[ts, col])
    return df


def _load_history() -> pd.DataFrame:
    if not os.path.exists(_OI_HISTORY_CSV):
        return pd.DataFrame(columns=["date", "pair", "oi_total", "close"])
    try:
        return pd.read_csv(_OI_HISTORY_CSV)
    except Exception:
        return pd.DataFrame(columns=["date", "pair", "oi_total", "close"])


def _write_csv(path: str, df: pd.DataFrame) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, path)


def _upsert_signals(df: pd.DataFrame) -> None:
    cli = get_client()
    if cli is None:
        print("  oi_pipeline: Supabase client unavailable — CSV only")
        return
    rows: List[dict] = []
    for _, r in df.iterrows():
        row = {"date": r["date"], "pair": r["pair"]}
        if pd.notna(r.get("oi_delta")):
            row["oi_delta"] = float(r["oi_delta"])
        align = r.get("oi_price_alignment")
        if isinstance(align, str) and align:
            row["oi_price_alignment"] = align
        if len(row) > 2:
            rows.append(row)
    if not rows:
        return
    try:
        cli.table("signals").upsert(rows, on_conflict="date,pair").execute()
        print(f"  oi_pipeline: upserted {len(rows)} OI rows to signals")
    except Exception as e:
        log_pipeline_error("oi_pipeline", str(e), notes="signals upsert")


def main() -> None:
    print("  oi_pipeline: CME Volume/OI daily report (Phase 4)")

    # CME publishes T+1; attempt today, then step back up to 2 days
    raw = pd.DataFrame()
    report_date = None
    for lag in (0, 1, 2):
        dt = datetime.today() - timedelta(days=lag)
        if dt.weekday() >= 5:  # skip weekends
            continue
        r = _fetch_oi_report(dt)
        if not r.empty:
            raw = r
            report_date = dt
            break

    if raw.empty or report_date is None:
        print("  oi_pipeline: no OI report available within T+2 window")
        # still write an empty sidecar so merge_main does not carry stale data
        _write_csv(_OI_LATEST_CSV, pd.DataFrame(columns=[
            "date", "pair", "oi_total", "close", "oi_delta", "px_delta", "oi_price_alignment",
        ]))
        return

    today_rows = _normalise_oi_frame(raw, report_date)
    if today_rows.empty:
        print("  oi_pipeline: report parsed but no recognised products")
        _write_csv(_OI_LATEST_CSV, pd.DataFrame(columns=[
            "date", "pair", "oi_total", "close", "oi_delta", "px_delta", "oi_price_alignment",
        ]))
        return

    today_rows = _fill_close_from_master(today_rows)

    # Append to history, de-dup on (date, pair), sort chronologically
    history = _load_history()
    merged = pd.concat([history, today_rows], ignore_index=True)
    merged = merged.drop_duplicates(subset=["date", "pair"], keep="last")
    merged = merged.sort_values(["pair", "date"]).reset_index(drop=True)

    merged["oi_delta"] = merged.groupby("pair")["oi_total"].diff()
    merged["px_delta"] = merged.groupby("pair")["close"].diff()
    merged["oi_prev"] = merged.groupby("pair")["oi_total"].shift(1)
    merged["close_prev"] = merged.groupby("pair")["close"].shift(1)
    merged["oi_price_alignment"] = merged.apply(
        lambda r: _classify_alignment(r["oi_delta"], r["oi_prev"], r["px_delta"], r["close_prev"]),
        axis=1,
    )

    out = merged.drop(columns=["oi_prev", "close_prev"])
    _write_csv(_OI_HISTORY_CSV, out)
    # Sidecar written for merge_main: latest ~60 rows per pair is plenty
    latest = out.groupby("pair").tail(60)
    _write_csv(_OI_LATEST_CSV, latest)
    print(f"  oi_pipeline: wrote {_OI_LATEST_CSV} ({len(latest)} rows across {latest['pair'].nunique()} pairs)")

    _upsert_signals(latest)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"  oi_pipeline: unexpected error — {e}")
        try:
            log_pipeline_error("oi_pipeline", str(e), notes="main")
        except Exception:
            pass
    sys.exit(0)
