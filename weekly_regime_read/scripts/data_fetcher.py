#!/usr/bin/env python3
"""
weekly_regime_read/scripts/data_fetcher.py
==========================================
Phase A — Data ingestion for the Weekly Regime Read.

Fetches the latest regime state, 30-day history sparklines, macro events,
and cross-asset context from Supabase + local CSV fallbacks.
Produces a single ``writer_data_YYYYMMDD.json`` consumed by the writer
and chart-generation pipeline.

Usage::
    python data_fetcher.py [--output-dir weekly_regime_read/output]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PAIRS = ["EURUSD", "USDJPY", "USDINR"]
HISTORY_DAYS = 30
MACRO_FORWARD_DAYS = 14

LOCAL_CSV_PATHS = {
    "latest": Path("data/latest.csv"),
    "latest_with_cot": Path("data/latest_with_cot.csv"),
    "cot_latest": Path("data/cot_latest.csv"),
    "inr_latest": Path("data/inr_latest.csv"),
}

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://weaaacohvzzgkgxzpaee.supabase.co",
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndlYWFhY29odnp6Z2tneHpwYWVlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTMxNjEzMSwiZXhwIjoyMDkwODkyMTMxfQ.rL_WtoH5CXFbb4P0Jdj_ZJoCtyearfCskwYVZHI4_Ys",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------
def create_supabase_client() -> Client:
    """Create a Supabase client using env vars or hard-coded fallback."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------
def fetch_latest_regime_calls(client: Client) -> dict[str, dict[str, Any]]:
    """Fetch the most recent regime_calls row for each of the three pairs."""
    out: dict[str, dict[str, Any]] = {}
    for pair in PAIRS:
        res = (
            client.table("regime_calls")
            .select("*")
            .eq("pair", pair)
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if rows:
            out[pair] = rows[0]
        else:
            logger.warning("No regime_calls found for %s", pair)
            out[pair] = {}
    return out


def fetch_30day_history(client: Client, pair: str) -> dict[str, Any]:
    """
    Fetch ~30 days of history for sparklines.

    Returns a dict with:
    - ``dates``: ISO date strings (oldest → newest)
    - ``spot``: spot prices from signals
    - ``composite``: signal_composite from regime_calls
    - ``confidence``: confidence from regime_calls
    - ``rate_diff_10y``: 10Y rate differential from signals
    - ``cot_percentile``: COT percentile from signals
    - ``realized_vol_20d``: 20D realized vol from signals
    """
    cutoff = (date.today() - timedelta(days=HISTORY_DAYS + 5)).isoformat()

    # Signals history
    sig_res = (
        client.table("signals")
        .select(
            "date,spot,rate_diff_10y,cot_percentile,realized_vol_20d,implied_vol_30d,"
            "day_change_pct,cross_asset_vix,cross_asset_dxy,cross_asset_oil,cross_asset_gold"
        )
        .eq("pair", pair)
        .gte("date", cutoff)
        .order("date", desc=False)
        .limit(HISTORY_DAYS)
        .execute()
    )
    sig_rows: list[dict[str, Any]] = sig_res.data or []

    # Regime calls history (for composite + confidence)
    rc_res = (
        client.table("regime_calls")
        .select("date,signal_composite,confidence,regime,predicted_direction,directional_bias")
        .eq("pair", pair)
        .gte("date", cutoff)
        .order("date", desc=False)
        .limit(HISTORY_DAYS)
        .execute()
    )
    rc_rows: list[dict[str, Any]] = rc_res.data or []

    # Merge on date
    rc_by_date = {str(r["date"]): r for r in rc_rows}

    history: dict[str, Any] = {
        "dates": [],
        "spot": [],
        "composite": [],
        "confidence": [],
        "regime": [],
        "rate_diff_10y": [],
        "cot_percentile": [],
        "realized_vol_20d": [],
        "implied_vol_30d": [],
        "day_change_pct": [],
    }

    for sr in sig_rows:
        d = str(sr.get("date", ""))
        rc = rc_by_date.get(d, {})
        history["dates"].append(d)
        history["spot"].append(_to_float(sr.get("spot")))
        history["composite"].append(_to_float(rc.get("signal_composite")))
        history["confidence"].append(_to_float(rc.get("confidence")))
        history["regime"].append(rc.get("regime"))
        history["rate_diff_10y"].append(_to_float(sr.get("rate_diff_10y")))
        history["cot_percentile"].append(_to_float(sr.get("cot_percentile")))
        history["realized_vol_20d"].append(_to_float(sr.get("realized_vol_20d")))
        history["implied_vol_30d"].append(_to_float(sr.get("implied_vol_30d")))
        history["day_change_pct"].append(_to_float(sr.get("day_change_pct")))

    return history


def fetch_macro_events(client: Client, forward_days: int = MACRO_FORWARD_DAYS) -> list[dict[str, Any]]:
    """Fetch macro events for the next ``forward_days`` days."""
    today = date.today().isoformat()
    end = (date.today() + timedelta(days=forward_days)).isoformat()

    res = (
        client.table("macro_events")
        .select("date,event,impact,pairs,category,ai_brief")
        .gte("date", today)
        .lte("date", end)
        .order("date", desc=False)
        .execute()
    )
    rows: list[dict[str, Any]] = res.data or []

    # Deduplicate on (date, event)
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for r in rows:
        key = (str(r.get("date", "")), str(r.get("event", "")))
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    return deduped


# ---------------------------------------------------------------------------
# Local CSV helpers
# ---------------------------------------------------------------------------
def _read_csv_tail(path: Path, n: int = 3) -> pd.DataFrame | None:
    """Read the last ``n`` rows of a CSV, returning None if missing."""
    if not path.exists():
        logger.warning("CSV not found: %s", path)
        return None
    try:
        df = pd.read_csv(path)
        if df.empty:
            return None
        return df.tail(n)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read %s: %s", path, exc)
        return None


def read_cross_asset_context() -> dict[str, Any]:
    """
    Extract cross-asset telemetry from local CSV fallbacks.

    Prefers ``latest_with_cot.csv`` (has VIX) and falls back to
    ``latest.csv`` for DXY / Brent / Gold.
    """
    out: dict[str, Any] = {
        "source": "csv_fallback",
        "DXY": None,
        "VIX": None,
        "Brent": None,
        "Gold": None,
        "US_10Y": None,
        "US_DE_10Y_spread": None,
        "US_JP_10Y_spread": None,
        "US_IN_10Y_spread": None,
    }

    # Primary: latest_with_cot.csv
    df_cot = _read_csv_tail(LOCAL_CSV_PATHS["latest_with_cot"], n=1)
    if df_cot is not None and not df_cot.empty:
        row = df_cot.iloc[-1]
        out["DXY"] = _to_float(row.get("DXY"))
        out["VIX"] = _to_float(row.get("VIX"))
        out["Brent"] = _to_float(row.get("Brent"))
        out["Gold"] = _to_float(row.get("Gold"))
        out["US_10Y"] = _to_float(row.get("US_10Y"))
        out["US_DE_10Y_spread"] = _to_float(row.get("US_DE_10Y_spread"))
        out["US_JP_10Y_spread"] = _to_float(row.get("US_JP_10Y_spread"))
        out["US_IN_10Y_spread"] = _to_float(row.get("US_IN_10Y_spread"))
        out["source"] = "latest_with_cot.csv"

    # Fallback: latest.csv (no VIX)
    if out.get("DXY") is None:
        df_latest = _read_csv_tail(LOCAL_CSV_PATHS["latest"], n=1)
        if df_latest is not None and not df_latest.empty:
            row = df_latest.iloc[-1]
            out["DXY"] = _to_float(row.get("DXY"))
            out["Brent"] = _to_float(row.get("Brent"))
            out["Gold"] = _to_float(row.get("Gold"))
            out["US_10Y"] = _to_float(row.get("US_10Y"))
            out["US_DE_10Y_spread"] = _to_float(row.get("US_DE_10Y_spread"))
            out["US_JP_10Y_spread"] = _to_float(row.get("US_JP_10Y_spread"))
            out["source"] = "latest.csv"

    # INR-specific from inr_latest.csv
    df_inr = _read_csv_tail(LOCAL_CSV_PATHS["inr_latest"], n=1)
    if df_inr is not None and not df_inr.empty:
        row = df_inr.iloc[-1]
        out["USDINR"] = _to_float(row.get("USDINR"))
        out["IN_10Y"] = _to_float(row.get("IN_10Y"))
        out["FPI_20D_flow"] = _to_float(row.get("FPI_20D_flow"))
        out["FPI_20D_percentile"] = _to_float(row.get("FPI_20D_percentile"))
        out["USDINR_vol30"] = _to_float(row.get("USDINR_vol30"))
        out["USDINR_vol_pct"] = _to_float(row.get("USDINR_vol_pct"))

    return out


def read_pair_components_from_csvs() -> dict[str, dict[str, Any]]:
    """
    Extract component-level data for each pair from local CSVs.

    Returns driver labels, composite scores, and any component breakdowns
    available in the flat CSV files.
    """
    out: dict[str, dict[str, Any]] = {
        "EURUSD": {},
        "USDJPY": {},
        "USDINR": {},
    }

    df_cot = _read_csv_tail(LOCAL_CSV_PATHS["latest_with_cot"], n=1)
    if df_cot is not None and not df_cot.empty:
        row = df_cot.iloc[-1]
        out["EURUSD"]["composite_score"] = _to_float(row.get("eurusd_composite_score"))
        out["EURUSD"]["composite_label"] = row.get("eurusd_composite_label")
        out["EURUSD"]["primary_driver"] = row.get("eur_primary_driver")
        out["USDJPY"]["composite_score"] = _to_float(row.get("usdjpy_composite_score"))
        out["USDJPY"]["composite_label"] = row.get("usdjpy_composite_label")
        out["USDJPY"]["primary_driver"] = row.get("jpy_primary_driver")
        out["USDINR"]["composite_score"] = _to_float(row.get("inr_composite_score"))
        out["USDINR"]["composite_label"] = row.get("inr_composite_label")
        out["USDINR"]["primary_driver"] = row.get("inr_primary_driver")

    return out


def read_pair_supplement_from_csvs() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    Extract supplementary per-pair data from local CSVs.

    Returns a tuple of (pair_supplements, meta) where *pair_supplements* maps
    pair → dict of spot, day_change_pct, rate diffs, vol, COT, etc., and
    *meta* contains ``csv_date`` and ``csv_stale`` flags.
    """
    out: dict[str, dict[str, Any]] = {
        "EURUSD": {},
        "USDJPY": {},
        "USDINR": {},
    }
    meta: dict[str, Any] = {"csv_date": None, "csv_stale": False, "csv_stale_days": None}

    # --- Primary price / rate / vol data: latest_with_cot.csv (preferred) or latest.csv ---
    df_latest = _read_csv_tail(LOCAL_CSV_PATHS["latest_with_cot"], n=1)
    if df_latest is None or df_latest.empty:
        df_latest = _read_csv_tail(LOCAL_CSV_PATHS["latest"], n=1)

    if df_latest is not None and not df_latest.empty:
        row = df_latest.iloc[-1]
        # EURUSD
        out["EURUSD"]["spot"] = _to_float(row.get("EURUSD"))
        out["EURUSD"]["day_change_pct"] = _to_float(row.get("EURUSD_chg_1D"))
        out["EURUSD"]["rate_diff_10y"] = _to_float(row.get("US_DE_10Y_spread"))
        out["EURUSD"]["rate_diff_2y"] = _to_float(row.get("US_DE_2Y_spread"))
        out["EURUSD"]["realized_vol"] = _to_float(row.get("EURUSD_vol30"))
        out["EURUSD"]["vol_rank"] = _to_float(row.get("EURUSD_vol_pct"))
        # USDJPY
        out["USDJPY"]["spot"] = _to_float(row.get("USDJPY"))
        out["USDJPY"]["day_change_pct"] = _to_float(row.get("USDJPY_chg_1D"))
        out["USDJPY"]["rate_diff_10y"] = _to_float(row.get("US_JP_10Y_spread"))
        out["USDJPY"]["rate_diff_2y"] = _to_float(row.get("US_JP_2Y_spread"))
        out["USDJPY"]["realized_vol"] = _to_float(row.get("USDJPY_vol30"))
        out["USDJPY"]["vol_rank"] = _to_float(row.get("USDJPY_vol_pct"))

        # Extract CSV date from first column (usually unnamed index with date)
        first_col = df_latest.columns[0]
        raw_date = row.get(first_col)
        if raw_date is not None and str(raw_date) != "nan":
            meta["csv_date"] = str(raw_date)[:10]

    # --- COT percentiles: cot_latest.csv ---
    df_cot = _read_csv_tail(LOCAL_CSV_PATHS["cot_latest"], n=1)
    if df_cot is not None and not df_cot.empty:
        row = df_cot.iloc[-1]
        # EUR
        out["EURUSD"]["cot_pct"] = _to_float(row.get("EUR_lev_percentile"))
        out["EURUSD"]["cot_net"] = _to_float(row.get("EUR_lev_net"))
        out["EURUSD"]["cot_lev_pct"] = _to_float(row.get("EUR_lev_pct_oi"))
        out["EURUSD"]["cot_amgr_pct"] = _to_float(row.get("EUR_assetmgr_percentile"))
        # JPY
        out["USDJPY"]["cot_pct"] = _to_float(row.get("JPY_lev_percentile"))
        out["USDJPY"]["cot_net"] = _to_float(row.get("JPY_lev_net"))
        out["USDJPY"]["cot_lev_pct"] = _to_float(row.get("JPY_lev_pct_oi"))
        out["USDJPY"]["cot_amgr_pct"] = _to_float(row.get("JPY_assetmgr_percentile"))

        cot_date = row.get("date")
        if cot_date is not None and str(cot_date) != "nan":
            meta["cot_csv_date"] = str(cot_date)[:10]

    # --- INR-specific: inr_latest.csv ---
    df_inr = _read_csv_tail(LOCAL_CSV_PATHS["inr_latest"], n=1)
    if df_inr is not None and not df_inr.empty:
        row = df_inr.iloc[-1]
        out["USDINR"]["spot"] = _to_float(row.get("USDINR"))
        out["USDINR"]["rate_diff_10y"] = _to_float(row.get("US_IN_10Y_spread"))
        out["USDINR"]["rate_diff_2y"] = _to_float(row.get("US_IN_policy_spread"))
        out["USDINR"]["realized_vol"] = _to_float(row.get("USDINR_vol30"))
        out["USDINR"]["vol_rank"] = _to_float(row.get("USDINR_vol_pct"))

        inr_date = row.get("date")
        if inr_date is not None and str(inr_date) != "nan":
            meta["inr_csv_date"] = str(inr_date)[:10]

    # --- Staleness check ---
    today = date.today()
    for key in ("csv_date", "cot_csv_date", "inr_csv_date"):
        csv_date_str = meta.get(key)
        if csv_date_str:
            try:
                csv_dt = datetime.strptime(csv_date_str, "%Y-%m-%d").date()
                days_stale = (today - csv_dt).days
                if days_stale > 7:
                    meta["csv_stale"] = True
                if meta["csv_stale_days"] is None or days_stale > meta["csv_stale_days"]:
                    meta["csv_stale_days"] = days_stale
            except Exception:
                pass

    return out, meta


# ---------------------------------------------------------------------------
# Data-quality helpers
# ---------------------------------------------------------------------------
def compute_data_quality_flags(
    regime_calls: dict[str, dict[str, Any]],
    cross_asset: dict[str, Any],
    csv_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return data-quality telemetry for the writer."""
    flags: dict[str, Any] = {}

    # JP rates missing flag: if US_JP spread is null and we're missing JPY data
    flags["jp_rates_missing"] = cross_asset.get("US_JP_10Y_spread") is None

    # Data freshness: max hours since the latest regime_call date
    max_age_hours: float | None = None
    for pair, rc in regime_calls.items():
        rc_date = rc.get("date")
        if rc_date:
            try:
                rc_dt = datetime.fromisoformat(str(rc_date)).replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - rc_dt).total_seconds() / 3600.0
                if max_age_hours is None or age > max_age_hours:
                    max_age_hours = age
            except Exception:  # noqa: BLE001
                pass
    flags["data_freshness_hours"] = round(max_age_hours, 1) if max_age_hours is not None else None
    flags["stale"] = (
        max_age_hours is not None and max_age_hours > 48
    )

    # CSV staleness
    if csv_meta:
        flags["csv_stale"] = csv_meta.get("csv_stale", False)
        flags["csv_stale_days"] = csv_meta.get("csv_stale_days")
        flags["csv_date"] = csv_meta.get("csv_date")
        flags["cot_csv_date"] = csv_meta.get("cot_csv_date")
        flags["inr_csv_date"] = csv_meta.get("inr_csv_date")

    # Coverage check
    flags["all_pairs_present"] = all(
        rc.get("pair") == pair for pair, rc in regime_calls.items()
    )

    return flags


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def build_pair_data(
    pair: str,
    regime_call: dict[str, Any],
    csv_components: dict[str, Any],
    csv_supplement: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the per-pair payload for the writer JSON."""
    sup = csv_supplement or {}
    return {
        "regime": regime_call.get("regime"),
        "composite": _to_float(regime_call.get("signal_composite")),
        "components": {
            "composite_score": csv_components.get("composite_score"),
            "composite_label": csv_components.get("composite_label"),
        },
        "direction": regime_call.get("predicted_direction"),
        "bias": regime_call.get("directional_bias"),
        "confidence": _to_float(regime_call.get("confidence")),
        "driver": regime_call.get("primary_driver") or csv_components.get("primary_driver"),
        "stop": _to_float(regime_call.get("stop_level")),
        "entry": regime_call.get("entry_timing"),
        "position": regime_call.get("position_size"),
        "conviction": regime_call.get("conviction"),
        "rate_signal": regime_call.get("rate_signal"),
        "cot_signal": regime_call.get("cot_signal"),
        "vol_signal": regime_call.get("vol_signal"),
        "oi_signal": regime_call.get("oi_signal"),
        "rr_signal": regime_call.get("rr_signal"),
        "special_signal_value": _to_float(regime_call.get("special_signal_value")),
        "special_signal_label": regime_call.get("special_signal_label"),
        "stress_level": regime_call.get("stress_level"),
        "data_quality_score": _to_float(regime_call.get("data_quality_score")),
        # Supplementary CSV context
        "spot": sup.get("spot"),
        "day_change_pct": sup.get("day_change_pct"),
        "rate_diff_2y": sup.get("rate_diff_2y"),
        "rate_diff_10y": sup.get("rate_diff_10y"),
        "cot_pct": sup.get("cot_pct"),
        "cot_net": sup.get("cot_net"),
        "cot_lev_pct": sup.get("cot_lev_pct"),
        "cot_amgr_pct": sup.get("cot_amgr_pct"),
        "realized_vol": sup.get("realized_vol"),
        "vol_rank": sup.get("vol_rank"),
    }


def build_writer_data(
    regime_calls: dict[str, dict[str, Any]],
    history: dict[str, dict[str, Any]],
    macro_events: list[dict[str, Any]],
    cross_asset: dict[str, Any],
    csv_components: dict[str, dict[str, Any]],
    csv_supplement: dict[str, dict[str, Any]],
    csv_meta: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the unified writer_data JSON payload."""
    today_iso = date.today().isoformat()

    pairs_payload: dict[str, Any] = {}
    for pair in PAIRS:
        pairs_payload[pair] = build_pair_data(
            pair,
            regime_calls.get(pair, {}),
            csv_components.get(pair, {}),
            csv_supplement.get(pair, {}),
        )

    data_quality = compute_data_quality_flags(regime_calls, cross_asset, csv_meta)

    return {
        "date": today_iso,
        "pairs": pairs_payload,
        "history": history,
        "macro_events": macro_events,
        "cross_asset": cross_asset,
        "data_quality": data_quality,
    }


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def verify_data(data: dict[str, Any]) -> list[str]:
    """
    Check internal consistency of the fetched data.

    Current checks:
    1. Spread direction consistency — the regime directional bias should
       broadly agree with the recent spread movement for EURUSD and USDJPY.

    Returns a list of human-readable error strings (empty if all pass).
    """
    errors: list[str] = []
    pairs = data.get("pairs", {})
    history = data.get("history", {})
    cross_asset = data.get("cross_asset", {})

    # Helper: compute spread change from history (if we have composite history)
    # We use the most recent 2 days of composite as a proxy for momentum,
    # but for spreads we look at cross_asset CSV values and their 1D change.
    # Since cross_asset only has levels, we check regime bias vs spread level.
    # A more robust check: if regime is BULLISH EURUSD, US-DE spread should
    # be compressed (low) or compressing.

    # EURUSD — US-DE 10Y spread
    eurusd = pairs.get("EURUSD", {})
    us_de_spread = cross_asset.get("US_DE_10Y_spread")
    eur_bias = (eurusd.get("bias") or "").upper()
    eur_direction = (eurusd.get("direction") or "").upper()

    if us_de_spread is not None and (eur_bias or eur_direction):
        # High spread = USD positive = EURUSD bearish
        # Low spread = EUR positive = EURUSD bullish
        # We can't judge absolute level without historical mean, so we flag
        # only when the regime is strongly directional AND we have history.
        eur_hist = history.get("EURUSD", {})
        composites = [c for c in eur_hist.get("composite", []) if c is not None]
        if len(composites) >= 2:
            recent_change = composites[-1] - composites[-2]
            # If composite rose (more bullish) but spread also rose (more USD+), flag
            if recent_change > 0.3 and eur_bias in ("LONG", "BULLISH"):
                # Check if spread also widened (we don't have spread history in
                # cross_asset, so we rely on the CSV 1-day change if available)
                pass  # Not enough history for spread — skip strict check

    # A stricter check using CSV 1D changes when available
    # We don't have 1D changes in the cross_asset dict, so we read them directly
    df_cot = _read_csv_tail(LOCAL_CSV_PATHS["latest_with_cot"], n=2)
    if df_cot is not None and len(df_cot) >= 2:
        prev = df_cot.iloc[-2]
        curr = df_cot.iloc[-1]

        # EURUSD vs US-DE spread 1D change
        us_de_prev = _to_float(prev.get("US_DE_10Y_spread"))
        us_de_curr = _to_float(curr.get("US_DE_10Y_spread"))
        if us_de_prev is not None and us_de_curr is not None:
            spread_chg = us_de_curr - us_de_prev
            eur_bias = (pairs.get("EURUSD", {}).get("bias") or "").upper()
            # Widening spread (+) = USD positive = EURUSD should be bearish/short
            if spread_chg > 0.05 and eur_bias in ("LONG", "BULLISH"):
                errors.append(
                    f"SPREAD_CONSISTENCY: EURUSD bias is {eur_bias} but US-DE 10Y spread "
                    f"widened from {us_de_prev:.3f} to {us_de_curr:.3f} (+{spread_chg:.3f} bps). "
                    f"Widening is USD-positive / EUR-negative."
                )
            if spread_chg < -0.05 and eur_bias in ("SHORT", "BEARISH"):
                errors.append(
                    f"SPREAD_CONSISTENCY: EURUSD bias is {eur_bias} but US-DE 10Y spread "
                    f"compressed from {us_de_prev:.3f} to {us_de_curr:.3f} ({spread_chg:.3f} bps). "
                    f"Compression is EUR-positive."
                )

        # USDJPY vs US-JP spread 1D change
        us_jp_prev = _to_float(prev.get("US_JP_10Y_spread"))
        us_jp_curr = _to_float(curr.get("US_JP_10Y_spread"))
        if us_jp_prev is not None and us_jp_curr is not None:
            spread_chg = us_jp_curr - us_jp_prev
            jpy_bias = (pairs.get("USDJPY", {}).get("bias") or "").upper()
            # Widening spread (+) = USD positive = USDJPY should be bullish/long
            if spread_chg > 0.05 and jpy_bias in ("SHORT", "BEARISH"):
                errors.append(
                    f"SPREAD_CONSISTENCY: USDJPY bias is {jpy_bias} but US-JP 10Y spread "
                    f"widened from {us_jp_prev:.3f} to {us_jp_curr:.3f} (+{spread_chg:.3f} bps). "
                    f"Widening is USD-positive / JPY-negative."
                )
            if spread_chg < -0.05 and jpy_bias in ("LONG", "BULLISH"):
                errors.append(
                    f"SPREAD_CONSISTENCY: USDJPY bias is {jpy_bias} but US-JP 10Y spread "
                    f"compressed from {us_jp_prev:.3f} to {us_jp_curr:.3f} ({spread_chg:.3f} bps). "
                    f"Compression is JPY-positive."
                )

    # Check for null-critical fields
    for pair in PAIRS:
        p = pairs.get(pair, {})
        if p.get("regime") is None:
            errors.append(f"MISSING_DATA: {pair} regime is null")
        if p.get("composite") is None:
            errors.append(f"MISSING_DATA: {pair} composite is null")
        if p.get("confidence") is None:
            errors.append(f"MISSING_DATA: {pair} confidence is null")

    return errors


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def write_output(data: dict[str, Any], output_dir: Path) -> Path:
    """Serialize ``data`` to ``writer_data_YYYYMMDD.json`` inside *output_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fname = f"writer_data_{data['date'].replace('-', '')}.json"
    out_path = output_dir / fname
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str, ensure_ascii=False)
    logger.info("Wrote %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch weekly regime read data")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("weekly_regime_read/output"),
        help="Directory to write writer_data_YYYYMMDD.json",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    client = create_supabase_client()

    # 1. Latest regime calls
    logger.info("Fetching latest regime calls for %s", PAIRS)
    regime_calls = fetch_latest_regime_calls(client)

    # 2. 30-day history per pair
    logger.info("Fetching %d-day history per pair", HISTORY_DAYS)
    history: dict[str, Any] = {}
    for pair in PAIRS:
        history[pair] = fetch_30day_history(client, pair)

    # 3. Macro events
    logger.info("Fetching macro events (next %d days)", MACRO_FORWARD_DAYS)
    macro_events = fetch_macro_events(client)

    # 4. Local CSV cross-asset + components + per-pair supplements
    logger.info("Reading local CSV fallbacks")
    cross_asset = read_cross_asset_context()
    csv_components = read_pair_components_from_csvs()
    csv_supplement, csv_meta = read_pair_supplement_from_csvs()
    if csv_meta.get("csv_stale"):
        logger.warning(
            "CSV data is stale by %d days (csv_date=%s, cot_date=%s, inr_date=%s)",
            csv_meta.get("csv_stale_days") or 0,
            csv_meta.get("csv_date"),
            csv_meta.get("cot_csv_date"),
            csv_meta.get("inr_csv_date"),
        )

    # 5. Assemble
    data = build_writer_data(
        regime_calls, history, macro_events, cross_asset, csv_components, csv_supplement, csv_meta
    )

    # 6. Verify
    logger.info("Running data verification")
    errs = verify_data(data)
    if errs:
        logger.warning("Verification found %d issue(s):", len(errs))
        for e in errs:
            logger.warning("  → %s", e)
        data["verification_errors"] = errs
    else:
        logger.info("Verification passed")
        data["verification_errors"] = []

    # 7. Write
    out_path = write_output(data, args.output_dir)
    print(out_path)
    return 0 if not errs else 1


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _to_float(val: Any) -> float | None:
    """Gracefully cast *val* to float, returning None on failure or pandas NA."""
    if val is None:
        return None
    if isinstance(val, float):
        return None if pd.isna(val) else val  # type: ignore[return-value]
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    sys.exit(main())
