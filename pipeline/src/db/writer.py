"""Supabase writes and reads used by the pipeline (service role)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict
from datetime import date
from functools import lru_cache
from typing import Any, cast

from supabase import Client, create_client

from src.types import RegimeCall, SignalRow


@lru_cache(maxsize=1)
def _client() -> Client:
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


def _date_iso(d: date | str) -> str:
    if isinstance(d, date):
        return d.isoformat()
    return str(d)[:10]


def write_signal_row(row: SignalRow) -> None:
    """Upsert columns that exist on the live `signals` table (no day_change / day_change_pct)."""
    payload: dict[str, Any] = {
        "pair": row.pair,
        "date": _date_iso(row.date),
        "rate_diff_2y": row.rate_diff_2y,
        "cot_percentile": row.cot_percentile,
        "realized_vol_20d": row.realized_vol_20d,
        "realized_vol_5d": row.realized_vol_5d,
        "implied_vol_30d": row.implied_vol_30d,
        "spot": row.spot,
    }
    _client().table("signals").upsert(payload, on_conflict="pair,date").execute()


def write_regime_call(call: RegimeCall) -> None:
    payload: dict[str, Any] = asdict(call)
    payload["date"] = _date_iso(call.date)
    _client().table("regime_calls").upsert(payload, on_conflict="pair,date").execute()


def write_validation_row(row: Mapping[str, Any]) -> None:
    payload = cast(dict[str, Any], dict(row))
    _client().table("validation_log").upsert(payload, on_conflict="pair,date").execute()


def write_brief(
    date_str: str,
    pair: str,
    regime: str,
    confidence: float,
    composite: float,
    analysis: str,
    primary_driver: str,
) -> None:
    payload = cast(
        dict[str, Any],
        {
            "date": date_str,
            "pair": pair,
            "regime": regime,
            "confidence": confidence,
            "composite": composite,
            "analysis": analysis,
            "primary_driver": primary_driver or None,
        },
    )
    _client().table("brief").upsert(payload, on_conflict="pair,date").execute()


def write_macro_events(events: list[dict[str, Any]]) -> None:
    for event in events:
        ev = cast(dict[str, Any], dict(event))
        if isinstance(ev.get("date"), date):
            ev["date"] = _date_iso(ev["date"])
        _client().table("macro_events").upsert(ev, on_conflict="date,event").execute()


def write_ai_request(date_str: str, purpose: str, model: str) -> None:
    row = cast(
        dict[str, Any],
        {"date": date_str, "request_count": 1, "purpose": purpose, "model": model},
    )
    _client().table("ai_usage_log").insert(row).execute()


def get_ai_request_count_today(date_str: str) -> int:
    res = _client().table("ai_usage_log").select("request_count").eq("date", date_str).execute()
    rows = cast(list[dict[str, Any]], res.data or [])
    if not rows:
        return 0
    return int(sum(int(r.get("request_count", 0)) for r in rows))


def get_latest_regime_call(pair: str) -> dict[str, Any] | None:
    res = (
        _client()
        .table("regime_calls")
        .select("*")
        .eq("pair", pair)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    data = cast(list[dict[str, Any]], res.data or [])
    return data[0] if data else None


def get_brief_for_date(pair: str, date_str: str) -> str | None:
    res = (
        _client()
        .table("brief")
        .select("analysis")
        .eq("pair", pair)
        .eq("date", date_str)
        .execute()
    )
    data = cast(list[dict[str, Any]], res.data or [])
    return str(data[0]["analysis"]) if data else None


def get_signal_for_pair_date(pair: str, date_str: str) -> dict[str, Any] | None:
    res = (
        _client()
        .table("signals")
        .select("*")
        .eq("pair", pair)
        .eq("date", date_str)
        .execute()
    )
    data = cast(list[dict[str, Any]], res.data or [])
    return data[0] if data else None


def update_macro_event_ai_brief(date_str: str, event: str, ai_brief: str) -> None:
    (
        _client()
        .table("macro_events")
        .update({"ai_brief": ai_brief})
        .eq("date", date_str)
        .eq("event", event)
        .execute()
    )


def list_high_impact_events_needing_brief(start_iso: str, end_iso: str) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("macro_events")
        .select("*")
        .eq("impact", "HIGH")
        .gte("date", start_iso)
        .lte("date", end_iso)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return [r for r in rows if r.get("ai_brief") in (None, "")]
