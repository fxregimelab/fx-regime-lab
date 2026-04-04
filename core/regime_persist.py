# core/regime_persist.py
# Upsert regime_calls + brief_log stub to Supabase after text brief is built.

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from config import TODAY
from core.signal_write import log_pipeline_error
from core.supabase_client import supabase

logger = logging.getLogger(__name__)


def _conf_from_score(score: Optional[float]) -> Optional[float]:
    if score is None or pd.isna(score):
        return None
    return max(0.0, min(1.0, abs(float(score)) / 100.0))


def _regime_row(
    pair: str,
    regime: str,
    confidence: Optional[float],
    composite: Optional[float],
    primary_driver: str,
) -> Dict[str, Any]:
    r = regime.strip()[:30] if regime else "UNKNOWN"
    return {
        "date": TODAY,
        "pair": pair,
        "regime": r,
        "confidence": confidence,
        "signal_composite": float(composite) if composite is not None and not pd.isna(composite) else None,
        "primary_driver": primary_driver[:2000] if primary_driver else None,
    }


def persist_regime_calls_and_brief(
    df: pd.DataFrame,
    brief_text: str,
) -> None:
    if supabase is None:
        return
    sub = df.dropna(subset=["EURUSD", "USDJPY"], how="any")
    if sub.empty:
        return
    row = sub.iloc[-1]

    rows: List[Dict[str, Any]] = []
    eur_lab = row.get("eurusd_composite_label")
    eur_sc = row.get("eurusd_composite_score")
    rows.append(
        _regime_row(
            "EURUSD",
            str(eur_lab) if eur_lab is not None and not pd.isna(eur_lab) else "UNKNOWN",
            _conf_from_score(eur_sc),
            float(eur_sc) if eur_sc is not None and not pd.isna(eur_sc) else None,
            "eurusd_composite",
        )
    )
    jpy_lab = row.get("usdjpy_composite_label")
    jpy_sc = row.get("usdjpy_composite_score")
    rows.append(
        _regime_row(
            "USDJPY",
            str(jpy_lab) if jpy_lab is not None and not pd.isna(jpy_lab) else "UNKNOWN",
            _conf_from_score(jpy_sc),
            float(jpy_sc) if jpy_sc is not None and not pd.isna(jpy_sc) else None,
            "usdjpy_composite",
        )
    )
    inr_lab = row.get("inr_composite_label")
    inr_sc = row.get("inr_composite_score")
    rows.append(
        _regime_row(
            "USDINR",
            str(inr_lab) if inr_lab is not None and not pd.isna(inr_lab) else "DIRECTIONAL_ONLY",
            _conf_from_score(inr_sc),
            float(inr_sc) if inr_sc is not None and not pd.isna(inr_sc) else None,
            "inr_composite",
        )
    )

    try:
        supabase.table("regime_calls").upsert(rows, on_conflict="date,pair").execute()
    except Exception as e:
        log_pipeline_error("regime_persist", str(e), notes="regime_calls upsert")
        logger.warning("regime_calls upsert failed: %s", e)

    brief_stub = {
        "date": TODAY,
        "brief_text": brief_text[:120000] if brief_text else None,
        "eurusd_regime": rows[0]["regime"],
        "usdjpy_regime": rows[1]["regime"],
        "usdinr_regime": rows[2]["regime"],
        "macro_context": None,
    }
    try:
        supabase.table("brief_log").upsert([brief_stub], on_conflict="date").execute()
    except Exception as e:
        log_pipeline_error("regime_persist", str(e), notes="brief_log")
        logger.warning("brief_log upsert failed: %s", e)
