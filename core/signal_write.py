# core/signal_write.py
# Dual-write: Supabase signals upsert + optional pipeline_errors logging (CSV unchanged — pipelines own CSV).

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from config import TODAY
from core.paths import LATEST_WITH_COT_CSV
from core.supabase_client import supabase

logger = logging.getLogger(__name__)


def log_pipeline_error(
    source: str,
    message: str,
    *,
    pair: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    if supabase is None:
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
        supabase.table("pipeline_errors").insert(payload).execute()
    except Exception as e:
        logger.warning("pipeline_errors insert failed: %s", e)


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
        out["rate_diff_2y"] = _nf(row, "US_DE_2Y_spread")
        out["rate_diff_10y"] = _nf(row, "US_DE_10Y_spread")
        out["cot_lev_money_net"] = _ni(row, "EUR_lev_net")
        out["cot_asset_mgr_net"] = _ni(row, "EUR_assetmgr_net")
        out["cot_percentile"] = _nf(row, "EUR_lev_percentile")
        out["realized_vol_20d"] = _nf(row, "EURUSD_vol30")
        out["cross_asset_dxy"] = _nf(row, "DXY")
        out["cross_asset_oil"] = _nf(row, "Brent")
    elif pair == "USDJPY":
        out["rate_diff_2y"] = _nf(row, "US_JP_2Y_spread")
        out["rate_diff_10y"] = _nf(row, "US_JP_10Y_spread")
        out["cot_lev_money_net"] = _ni(row, "JPY_lev_net")
        out["cot_asset_mgr_net"] = _ni(row, "JPY_assetmgr_net")
        out["cot_percentile"] = _nf(row, "JPY_lev_percentile")
        out["realized_vol_20d"] = _nf(row, "USDJPY_vol30")
        out["cross_asset_dxy"] = _nf(row, "DXY")
        out["cross_asset_oil"] = _nf(row, "Brent")
    elif pair == "USDINR":
        out["rate_diff_2y"] = _nf(row, "US_IN_policy_spread")
        out["rate_diff_10y"] = _nf(row, "US_IN_10Y_spread")
        out["realized_vol_20d"] = _nf(row, "USDINR_vol30")
        out["cross_asset_dxy"] = _nf(row, "DXY")
        out["cross_asset_oil"] = _nf(row, "Brent")
    # strip keys with None for cleaner upsert (Supabase accepts nulls too)
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


def sync_signals_from_master_csv(
    master_path: str = LATEST_WITH_COT_CSV,
    as_of: Optional[str] = None,
) -> bool:
    """Upsert latest bar for EUR/USD, USD/JPY, USD/INR into signals. Returns True if remote write attempted OK."""
    if supabase is None:
        logger.debug("sync_signals_from_master_csv: no supabase client")
        return False
    rows = build_signal_rows_for_latest_master(master_path, as_of)
    if not rows:
        log_pipeline_error("signal_write", "no rows built from master CSV", notes=master_path)
        return False
    try:
        supabase.table("signals").upsert(rows, on_conflict="date,pair").execute()
        return True
    except Exception as e:
        log_pipeline_error("signal_write", str(e), notes="signals upsert")
        logger.warning("signals upsert failed: %s", e)
        return False
