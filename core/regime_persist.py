# core/regime_persist.py
# Upsert regime_calls + brief_log to Supabase after text brief is built.

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd

from config import TODAY
from core.signal_write import log_pipeline_error
from core.supabase_client import get_client

logger = logging.getLogger(__name__)


def _conf_from_score(score: Optional[float]) -> Optional[float]:
    if score is None or pd.isna(score):
        return None
    return max(0.0, min(1.0, abs(float(score)) / 100.0))


def _sign_word(x: Any, bullish_first: bool = True) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "NEUTRAL"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "NEUTRAL"
    if v > 0:
        return "BULLISH" if bullish_first else "BEARISH"
    if v < 0:
        return "BEARISH" if bullish_first else "BULLISH"
    return "NEUTRAL"


def _rate_signal(row: pd.Series, pair: str) -> str:
    if pair == "EURUSD":
        return _sign_word(row.get("US_DE_2Y_spread_chg_1D"), True)
    if pair == "USDJPY":
        return _sign_word(row.get("US_JP_2Y_spread_chg_1D"), True)
    if pair == "USDINR":
        return _sign_word(row.get("US_IN_10Y_spread_chg_1D"), False)
    return "NEUTRAL"


def _cot_signal(row: pd.Series, pair: str) -> str:
    pct = row.get("EUR_lev_percentile") if pair == "EURUSD" else row.get("JPY_lev_percentile") if pair == "USDJPY" else None
    if pct is None or pd.isna(pct):
        return "NEUTRAL"
    try:
        p = float(pct)
    except (TypeError, ValueError):
        return "NEUTRAL"
    if p >= 80:
        return "BEARISH"
    if p <= 20:
        return "BULLISH"
    return "NEUTRAL"


def _vol_signal(row: pd.Series, pair: str) -> str:
    col = f"{pair}_vol_pct" if pair in ("EURUSD", "USDJPY") else "USDINR_vol_pct"
    if col not in row.index:
        return "NEUTRAL"
    v = row.get(col)
    if v is None or pd.isna(v):
        return "NEUTRAL"
    try:
        p = float(v)
    except (TypeError, ValueError):
        return "NEUTRAL"
    if p >= 80:
        return "BEARISH"
    if p <= 25:
        return "BULLISH"
    return "NEUTRAL"


def _regime_row(
    pair: str,
    regime: str,
    confidence: Optional[float],
    composite: Optional[float],
    primary_driver: str,
    row: pd.Series,
) -> Dict[str, Any]:
    r = regime.strip()[:30] if regime else "UNKNOWN"
    return {
        "date": TODAY,
        "pair": pair,
        "regime": r,
        "confidence": confidence,
        "signal_composite": float(composite) if composite is not None and not pd.isna(composite) else None,
        "primary_driver": primary_driver[:2000] if primary_driver else None,
        "rate_signal": _rate_signal(row, pair),
        "cot_signal": _cot_signal(row, pair),
        "vol_signal": _vol_signal(row, pair),
    }


def persist_regime_calls_and_brief(
    df: pd.DataFrame,
    brief_text: str,
) -> None:
    cli = get_client()
    if cli is None:
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
            row,
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
            row,
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
            row,
        )
    )

    try:
        cli.table("regime_calls").upsert(rows, on_conflict="date,pair").execute()
    except Exception as e:
        log_pipeline_error("regime_persist", str(e), notes="regime_calls upsert")
        logger.warning("regime_calls upsert failed: %s", e)

    macro_context = None
    if brief_text:
        one = brief_text.strip().split("\n")[0].strip()
        sent = re.split(r"(?<=[.!?])\s+", one, maxsplit=1)[0].strip()
        macro_context = sent[:2000] if sent else None

    brief_stub = {
        "date": TODAY,
        "brief_text": (brief_text[:10000] if brief_text else None),
        "eurusd_regime": rows[0]["regime"],
        "usdjpy_regime": rows[1]["regime"],
        "usdinr_regime": rows[2]["regime"],
        "macro_context": macro_context,
    }
    try:
        cli.table("brief_log").upsert([brief_stub], on_conflict="date").execute()
    except Exception as e:
        log_pipeline_error("regime_persist", str(e), notes="brief_log")
        logger.warning("brief_log upsert failed: %s", e)
