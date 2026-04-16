# vol_pipeline.py
# CBOE FX implied-vol indices (^EVZ, ^JYVIX) via yfinance (wrapped by
# core.utils._yf_safe_download — optional Polygon.io fallback).
#
# ^EVZ   = CBOE EuroCurrency Volatility Index (EUR/USD 30-day IV)
# ^JYVIX = CBOE/CME Yen Volatility Index (USD/JPY 30-day IV)
#
# USD/INR is not covered here — merge_main falls back to realized vol for INR.
#
# Writes data/vol_latest.csv and Supabase `signals.implied_vol_30d`.
# vol_skew and atm_vol are omitted on upsert (NULL in DB).

from __future__ import annotations

import os
import sys
from typing import List

import numpy as np
import pandas as pd

from config import CBOE_VOL_TICKERS, START_DATE, TODAY
from core.paths import DATA_DIR
from core.signal_write import log_pipeline_error
from core.supabase_client import get_client
from core.utils import _yf_safe_download


"""
CBOE FX implied volatility pipeline.

Execution context:
- Called by run.py as STEP 4 (vol)
- Depends on: inr_pipeline.py
- Outputs: Supabase signals (implied_vol_30d) + data/vol_latest.csv
- Next step: oi_pipeline.py
- Blocking: YES — main() must ALWAYS sys.exit(0)

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""

_VOL_LATEST_CSV = os.path.join(DATA_DIR, "vol_latest.csv")
_SIDECAR_COLS = ["date", "pair", "implied_vol_30d", "vol_skew", "atm_vol"]


def _fetch_cboe_vol(pair: str, ticker: str) -> pd.DataFrame:
    """Fetch CBOE FX-vol index via yfinance wrapper. Returns empty frame on failure."""
    raw = _yf_safe_download(
        ticker,
        start=START_DATE,
        end=TODAY,
        interval="1d",
        auto_adjust=True,
    )
    if raw is None or raw.empty:
        log_pipeline_error(
            "vol_pipeline",
            f"{ticker} returned no data",
            pair=pair,
            notes="cboe_empty",
        )
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            close = raw["Close"].iloc[:, 0]
        else:
            close = raw.iloc[:, 0]
    elif "Close" in raw.columns:
        close = raw["Close"]
    else:
        close = raw.iloc[:, 0]

    close = pd.to_numeric(close, errors="coerce").dropna()
    if close.empty:
        log_pipeline_error(
            "vol_pipeline",
            f"{ticker} had no usable Close values",
            pair=pair,
            notes="cboe_no_close",
        )
        return pd.DataFrame()

    idx = pd.to_datetime(close.index).tz_localize(None).normalize()
    out = pd.DataFrame({
        "date": idx.strftime("%Y-%m-%d"),
        "pair": pair,
        "implied_vol_30d": close.values,
        "vol_skew": np.nan,
        "atm_vol": np.nan,
    })
    return out[_SIDECAR_COLS]


def _write_csv(out: pd.DataFrame) -> None:
    """Always overwrite data/vol_latest.csv so merge_main picks up fresh data."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = _VOL_LATEST_CSV + ".tmp"
    out.to_csv(tmp, index=False, encoding="utf-8")
    os.replace(tmp, _VOL_LATEST_CSV)
    print(f"  vol_pipeline: wrote {_VOL_LATEST_CSV} ({len(out)} rows)")


def _upsert_signals(out: pd.DataFrame) -> None:
    """Upsert last 260 rows per pair to Supabase signals on (date, pair).

    vol_skew and atm_vol are NaN — stripped per row so Supabase stores NULL.
    """
    cli = get_client()
    if cli is None:
        print("  vol_pipeline: Supabase client unavailable — CSV only")
        return
    try:
        for pair, grp in out.groupby("pair"):
            raw_rows: List[dict] = (
                grp.sort_values("date").tail(260).to_dict("records")
            )
            cleaned = []
            for r in raw_rows:
                cleaned.append({
                    k: v for k, v in r.items()
                    if v is not None and not (isinstance(v, float) and pd.isna(v))
                })
            if cleaned:
                cli.table("signals").upsert(cleaned, on_conflict="date,pair").execute()
                print(f"  vol_pipeline: upserted {len(cleaned)} rows for {pair}")
    except Exception as e:
        log_pipeline_error("vol_pipeline", str(e), notes="signals upsert")


def main() -> None:
    print("  vol_pipeline: CBOE FX implied-vol via yfinance (^EVZ, ^JYVIX)")

    frames = []
    for pair, ticker in CBOE_VOL_TICKERS.items():
        df = _fetch_cboe_vol(pair, ticker)
        if df.empty:
            print(f"  vol_pipeline: no CBOE vol data for {pair} ({ticker})")
            continue
        frames.append(df)

    if not frames:
        print("  vol_pipeline: no CBOE frames — writing empty CSV")
        _write_csv(pd.DataFrame(columns=_SIDECAR_COLS))
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
