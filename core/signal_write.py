# core/signal_write.py
# Dual-write: Supabase signals upsert (primary) + pipeline_errors; CSV remains on disk via pipelines.

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from config import TODAY
from core.paths import LATEST_WITH_COT_CSV, SUPABASE_SYNC_SIDECAR
from core.supabase_client import get_client

logger = logging.getLogger(__name__)

CHUNK_SIZE = 100


def log_pipeline_error(
    source: str,
    message: str,
    *,
    pair: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    cli = get_client()
    if cli is None:
        return
    payload: Dict[str, Any] = {
        "date": TODAY,
        "source": source[:50],
        "error_message": message[:8000],
    }
    if pair:
        payload["pair"] = pair[:10]
    if notes:
        payload["notes"] = notes[:2000]
    try:
        cli.table("pipeline_errors").insert(payload).execute()
    except Exception as e:
        print(f"[pipeline_errors] insert failed: {e}", flush=True)
        logger.warning("pipeline_errors insert failed: %s", e)


def _write_supabase_sidecar(status: str, rows_written: int) -> None:
    """Subprocess → parent (run.py) bridge for pipeline_status.json merge."""
    payload = {
        "supabase_write_status": status,
        "supabase_rows_written": int(rows_written),
        "last_supabase_write": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        os.makedirs(os.path.dirname(SUPABASE_SYNC_SIDECAR), exist_ok=True)
        tmp = SUPABASE_SYNC_SIDECAR + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, SUPABASE_SYNC_SIDECAR)
    except OSError as e:
        logger.warning("supabase sidecar write failed: %s", e)


def _nf(row: pd.Series, col: str) -> Optional[float]:
    if col not in row.index:
        return None
    v = row[col]
    if pd.isna(v):
        return None
    return float(v)


def _ni(row: pd.Series, col: str) -> Optional[int]:
    if col not in row.index:
        return None
    v = row[col]
    if pd.isna(v):
        return None
    return int(round(float(v)))


def _row_to_signal(pair: str, row: pd.Series, as_of: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"date": as_of, "pair": pair}
    if pair == "EURUSD":
        out["spot"] = _nf(row, "EURUSD")
        out["rate_diff_2y"] = _nf(row, "US_DE_2Y_spread")
        out["rate_diff_10y"] = _nf(row, "US_DE_10Y_spread")
        out["cot_lev_money_net"] = _ni(row, "EUR_lev_net")
        out["cot_asset_mgr_net"] = _ni(row, "EUR_assetmgr_net")
        out["cot_percentile"] = _nf(row, "EUR_lev_percentile")
        out["realized_vol_20d"] = _nf(row, "EURUSD_vol30")
        out["cross_asset_dxy"] = _nf(row, "DXY")
        out["cross_asset_oil"] = _nf(row, "Brent")
    elif pair == "USDJPY":
        out["spot"] = _nf(row, "USDJPY")
        out["rate_diff_2y"] = _nf(row, "US_JP_2Y_spread")
        out["rate_diff_10y"] = _nf(row, "US_JP_10Y_spread")
        out["cot_lev_money_net"] = _ni(row, "JPY_lev_net")
        out["cot_asset_mgr_net"] = _ni(row, "JPY_assetmgr_net")
        out["cot_percentile"] = _nf(row, "JPY_lev_percentile")
        out["realized_vol_20d"] = _nf(row, "USDJPY_vol30")
        out["cross_asset_dxy"] = _nf(row, "DXY")
        out["cross_asset_oil"] = _nf(row, "Brent")
    elif pair == "USDINR":
        out["spot"] = _nf(row, "USDINR")
        out["rate_diff_2y"] = _nf(row, "US_IN_policy_spread")
        out["rate_diff_10y"] = _nf(row, "US_IN_10Y_spread")
        out["realized_vol_20d"] = _nf(row, "USDINR_vol30")
        out["cross_asset_dxy"] = _nf(row, "DXY")
        out["cross_asset_oil"] = _nf(row, "Brent")
    else:
        return out
    vix = _nf(row, "VIX")
    if vix is not None:
        out["cross_asset_vix"] = vix
    z2 = _nf(row, "US_DE_2Y_spread_zscore")
    z10 = _nf(row, "US_DE_10Y_spread_zscore")
    zj2 = _nf(row, "US_JP_2Y_spread_zscore")
    zj10 = _nf(row, "US_JP_10Y_spread_zscore")
    zi2 = _nf(row, "US_IN_policy_spread_zscore")
    zi10 = _nf(row, "US_IN_10Y_spread_zscore")
    if pair == "EURUSD" and z2 is not None:
        out["rate_diff_zscore"] = z2
    elif pair == "EURUSD" and z10 is not None:
        out["rate_diff_zscore"] = z10
    elif pair == "USDJPY" and zj2 is not None:
        out["rate_diff_zscore"] = zj2
    elif pair == "USDJPY" and zj10 is not None:
        out["rate_diff_zscore"] = zj10
    elif pair == "USDINR" and zi2 is not None:
        out["rate_diff_zscore"] = zi2
    elif pair == "USDINR" and zi10 is not None:
        out["rate_diff_zscore"] = zi10
    rv5 = _nf(row, "EURUSD_vol5") if pair == "EURUSD" else _nf(row, "USDJPY_vol5") if pair == "USDJPY" else _nf(row, "USDINR_vol5")
    if rv5 is not None:
        out["realized_vol_5d"] = rv5
    return {k: v for k, v in out.items() if v is not None or k in ("date", "pair")}


def build_signal_rows_for_latest_master(
    master_path: str = LATEST_WITH_COT_CSV,
    as_of: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not os.path.exists(master_path):
        return []
    as_of = as_of or TODAY
    df = pd.read_csv(master_path, index_col=0, parse_dates=True)
    sub = df.dropna(subset=["EURUSD", "USDJPY"], how="any")
    if sub.empty:
        return []
    row = sub.iloc[-1]
    rows = [_row_to_signal("EURUSD", row, as_of), _row_to_signal("USDJPY", row, as_of)]
    if "USDINR" in row.index and pd.notna(row["USDINR"]):
        rows.append(_row_to_signal("USDINR", row, as_of))
    return rows


def build_all_signal_rows(master_path: str = LATEST_WITH_COT_CSV) -> List[Dict[str, Any]]:
    if not os.path.exists(master_path):
        return []
    df = pd.read_csv(master_path, index_col=0, parse_dates=True)
    sub = df.dropna(subset=["EURUSD", "USDJPY"], how="any")
    out: List[Dict[str, Any]] = []
    for idx, row in sub.iterrows():
        as_of = pd.Timestamp(idx).strftime("%Y-%m-%d")
        out.append(_row_to_signal("EURUSD", row, as_of))
        out.append(_row_to_signal("USDJPY", row, as_of))
        if "USDINR" in row.index and pd.notna(row["USDINR"]):
            out.append(_row_to_signal("USDINR", row, as_of))
    return out


def sync_signals_from_master_csv(
    master_path: str = LATEST_WITH_COT_CSV,
    as_of: Optional[str] = None,
) -> bool:
    """Upsert latest calendar day (3 pairs) into signals. Kept for narrow sync calls."""
    cli = get_client()
    if cli is None:
        _write_supabase_sidecar("skipped", 0)
        return False
    rows = build_signal_rows_for_latest_master(master_path, as_of)
    if not rows:
        log_pipeline_error("signal_write", "no rows built from master CSV", notes=master_path)
        _write_supabase_sidecar("failed", 0)
        return False
    try:
        cli.table("signals").upsert(rows, on_conflict="date,pair").execute()
        print(f"[Supabase] Wrote {len(rows)} signal rows", flush=True)
        _write_supabase_sidecar("ok", len(rows))
        return True
    except Exception as e:
        log_pipeline_error("signal_write", str(e), notes="signals upsert")
        logger.warning("signals upsert failed: %s", e)
        _write_supabase_sidecar("failed", 0)
        return False


def sync_all_signals_from_master_csv(
    master_path: str = LATEST_WITH_COT_CSV,
) -> bool:
    """Batch-upsert full merged master history into signals (CI + backfill)."""
    cli = get_client()
    if cli is None:
        _write_supabase_sidecar("skipped", 0)
        return False
    rows = build_all_signal_rows(master_path)
    if not rows:
        log_pipeline_error("signal_write", "no rows built for full sync", notes=master_path)
        _write_supabase_sidecar("failed", 0)
        return False
    n = 0
    try:
        for i in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[i : i + CHUNK_SIZE]
            cli.table("signals").upsert(chunk, on_conflict="date,pair").execute()
            n += len(chunk)
        print(f"[Supabase] Wrote {n} signal rows", flush=True)
        _write_supabase_sidecar("ok", n)
        return True
    except Exception as e:
        log_pipeline_error("signal_write", str(e), notes="signals full upsert")
        logger.warning("signals full upsert failed: %s", e)
        _write_supabase_sidecar("failed", n)
        return False
