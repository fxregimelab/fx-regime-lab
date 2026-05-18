"""
Backfill desk_open_cards from existing regime_calls + signals data.

This script generates desk_open_card rows for the latest available date
by computing all required fields from the existing pipeline output tables.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from supabase import create_client


def _client() -> Any:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


def get_latest_regime_call_date() -> str | None:
    res = _client().table("regime_calls").select("date").order("date", desc=True).limit(1).execute()
    rows = res.data or []
    return rows[0]["date"] if rows else None


def get_regime_calls_for_date(date_str: str) -> list[dict[str, Any]]:
    res = _client().table("regime_calls").select("*").eq("date", date_str).execute()
    return res.data or []


def get_signals_for_date(date_str: str) -> list[dict[str, Any]]:
    res = _client().table("signals").select("*").eq("date", date_str).execute()
    return res.data or []


def get_regime_history(pair: str, as_of: str, limit: int = 90) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("regime_calls")
        .select("date,regime")
        .eq("pair", pair)
        .lte("date", as_of)
        .order("date", desc=False)
        .limit(limit)
        .execute()
    )
    return res.data or []


def compute_regime_age(pair: str, current_regime: str, as_of: str) -> int:
    history = get_regime_history(pair, as_of)
    age = 0
    for row in reversed(history):
        if row["regime"] == current_regime:
            age += 1
        else:
            break
    return max(1, age)


def compute_dominance_array(call: dict[str, Any]) -> list[dict[str, Any]]:
    """Build dominance array from signal decomposition."""
    signals = []
    weights = {
        "rate_signal": 0.40,
        "cot_signal": 0.30,
        "vol_signal": 0.20,
        "oi_signal": 0.10,
    }
    for key, weight in weights.items():
        val = call.get(key)
        if val:
            signals.append({
                "signal_family": key.replace("_signal", "").upper(),
                "dominance_score": weight,
                "direction": str(val).upper(),
                "beta": 0.0,
            })
    # Sort by weight descending
    signals.sort(key=lambda x: x["dominance_score"], reverse=True)
    # Add rank
    for i, s in enumerate(signals):
        s["rank"] = i + 1
    return signals


def compute_markov_probabilities(current_regime: str) -> dict[str, float]:
    """Simplified Markov transition probabilities."""
    regimes = ["RISK_ON_DOLLAR_OFF", "RISK_OFF_DOLLAR_ON", "NEUTRAL",
               "INR_NEUTRAL__VOL_EXPANDING", "INR_RISK_OFF__DOLLAR_ON"]
    probs = {}
    for r in regimes:
        if r == current_regime:
            probs[r] = 0.65
        else:
            probs[r] = 0.35 / (len(regimes) - 1)
    return probs


def compute_telemetry_audit(call: dict[str, Any], sig: dict[str, Any]) -> dict[str, Any]:
    """Build telemetry audit from available data."""
    return {
        "dqs": call.get("data_quality_score"),
        "stress": call.get("stress_level"),
        "composite": call.get("signal_composite"),
        "rate_z_tactical": sig.get("rate_z_tactical") if sig else None,
        "rate_z_structural": sig.get("rate_z_structural") if sig else None,
        "rvol_20d": sig.get("realized_vol_20d") if sig else None,
        "rvol_5d": sig.get("realized_vol_5d") if sig else None,
        "skew": sig.get("skew_alignment") if sig else None,
        "human_grounding_active": False,
    }


def compute_pain_index(call: dict[str, Any], sig: dict[str, Any]) -> float:
    """Estimate pain index from volatility and signal divergence."""
    rvol = sig.get("realized_vol_20d") if sig else None
    if rvol is None:
        return 0.5
    # Higher vol = higher pain, capped at 1.0
    base = min(float(rvol) / 20.0, 1.0)
    # Add stress modifier
    stress = call.get("stress_level", "GREEN")
    multiplier = {"GREEN": 0.8, "YELLOW": 1.0, "RED": 1.3}.get(stress, 1.0)
    return round(min(base * multiplier, 1.0), 3)


def compute_apex_score(call: dict[str, Any]) -> float:
    """Compute apex score from confidence and signal strength."""
    confidence = call.get("confidence", 0.5) or 0.5
    composite = abs(call.get("signal_composite", 0.0) or 0.0)
    dqs = call.get("data_quality_score", 0.5) or 0.5
    # Weighted combination
    score = (confidence * 0.4 + composite * 0.35 + dqs * 0.25)
    return round(min(score, 1.0), 4)


def build_desk_card(
    call: dict[str, Any], sig: dict[str, Any] | None, date_str: str
) -> dict[str, Any]:
    pair = call["pair"]
    regime = call["regime"]
    regime_age = compute_regime_age(pair, regime, date_str)
    dominance_array = compute_dominance_array(call)
    pain_index = compute_pain_index(call, sig)
    markov = compute_markov_probabilities(regime)
    telemetry = compute_telemetry_audit(call, sig)
    apex = compute_apex_score(call)

    return {
        "date": date_str,
        "pair": pair,
        "structural_regime": regime,
        "dominance_array": dominance_array,
        "pain_index": pain_index,
        "markov_probabilities": markov,
        "ai_brief": None,
        "telemetry_audit": telemetry,
        "invalidation_triggered": False,
        "telemetry_status": "ONLINE",
        "global_rank": None,  # Set after sorting
        "apex_score": apex,
        "regime_age": regime_age,
    }


def backfill_desk_open_cards(target_date: str | None = None) -> None:
    if target_date is None:
        target_date = get_latest_regime_call_date()
    if not target_date:
        print("No regime_calls found — nothing to backfill.")
        return

    print(f"Backfilling desk_open_cards for {target_date}...")

    calls = get_regime_calls_for_date(target_date)
    signals = get_signals_for_date(target_date)
    sig_by_pair = {s["pair"]: s for s in signals}

    if not calls:
        print(f"No regime_calls for {target_date}.")
        return

    cards: list[dict[str, Any]] = []
    for call in calls:
        sig = sig_by_pair.get(call["pair"])
        card = build_desk_card(call, sig, target_date)
        cards.append(card)

    # Rank by apex_score descending
    cards.sort(key=lambda c: c["apex_score"], reverse=True)
    for i, card in enumerate(cards):
        card["global_rank"] = i + 1

    # Write to DB
    client = _client()
    client.table("desk_open_cards").upsert(cards, on_conflict="pair,date").execute()

    print(f"Wrote {len(cards)} desk_open_cards for {target_date}.")
    for c in cards:
        print(
            f"  #{c['global_rank']} {c['pair']}: {c['structural_regime']} "
            f"(apex={c['apex_score']}, age={c['regime_age']})"
        )


if __name__ == "__main__":
    date_override = sys.argv[1] if len(sys.argv) > 1 else None
    backfill_desk_open_cards(date_override)
