"""Supabase writes and reads used by the pipeline (service role)."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date
from functools import lru_cache
from typing import Any, cast

from supabase import Client, create_client

from src.types import DeskOpenCardRow, RegimeCall, SignalRow


@lru_cache(maxsize=1)
def _client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not (key and str(key).strip()):
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment "
            "(Prefect: deployment job_variables.env, or local .env). "
            f"SUPABASE_URL set: {bool(url)}, SUPABASE_SERVICE_ROLE_KEY set: {bool(key)}."
        )
    return create_client(url, key)


def fetch_universe_registry() -> list[dict[str, Any]]:
    """All rows from ``universe`` (ordered by pair). Service-role read."""

    res = (
        _client()
        .table("universe")
        .select("pair,class,spot_ticker,yield_base,yield_quote,cot_ticker")
        .order("pair")
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def _date_iso(d: date | str) -> str:
    if isinstance(d, date):
        return d.isoformat()
    return str(d)[:10]


def write_signal_row(row: SignalRow) -> None:
    """Upsert signal row with all available metrics."""
    payload: dict[str, Any] = {
        "pair": row.pair,
        "date": _date_iso(row.date),
        "rate_diff_2y": row.rate_diff_2y,
        "rate_diff_10y": row.rate_diff_10y,
        "cot_percentile": row.cot_percentile,
        "realized_vol_20d": row.realized_vol_20d,
        "realized_vol_5d": row.realized_vol_5d,
        "implied_vol_30d": row.implied_vol_30d,
        "spot": row.spot,
        "day_change": row.day_change,
        "day_change_pct": row.day_change_pct,
        "cross_asset_vix": row.cross_asset_vix,
        "cross_asset_dxy": row.cross_asset_dxy,
        "cross_asset_oil": row.cross_asset_oil,
        "cross_asset_us10y": row.cross_asset_us10y,
        "cross_asset_gold": row.cross_asset_gold,
        "cross_asset_copper": row.cross_asset_copper,
        "cross_asset_stoxx": row.cross_asset_stoxx,
        "oi_delta": row.oi_delta,
        "structural_instability": row.structural_instability,
        "breakeven_inflation_10y": row.breakeven_inflation_10y,
        "rate_diff_10y_real": row.rate_diff_10y_real,
        "rate_z_tactical": row.rate_z_tactical,
        "rate_z_structural": row.rate_z_structural,
    }
    _client().table("signals").upsert(payload, on_conflict="pair,date").execute()


def write_regime_call(call: RegimeCall) -> None:
    payload: dict[str, Any] = asdict(call)
    payload["date"] = _date_iso(call.date)
    _client().table("regime_calls").upsert(payload, on_conflict="pair,date").execute()


def _desk_open_card_payload(card: DeskOpenCardRow) -> dict[str, Any]:
    payload: dict[str, Any] = asdict(card)
    payload["date"] = _date_iso(card.date)
    return payload


def write_desk_open_card(card: DeskOpenCardRow) -> None:
    _client().table("desk_open_cards").upsert(
        _desk_open_card_payload(card), on_conflict="pair,date"
    ).execute()


def write_desk_open_cards_bulk(cards: Sequence[DeskOpenCardRow]) -> None:
    if not cards:
        return
    rows = [_desk_open_card_payload(c) for c in cards]
    _client().table("desk_open_cards").upsert(rows, on_conflict="pair,date").execute()


def get_desk_open_cards_for_date(date_str: str) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("desk_open_cards")
        .select("*")
        .eq("date", str(date_str)[:10])
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def get_rpc_g10_correlation_matrix() -> dict[str, dict[str, float]]:
    """Pairwise return correlations from Postgres (symmetric half-matrix JSON)."""

    res = _client().rpc("get_g10_correlation_matrix", {}).execute()
    raw = res.data
    if raw is None:
        return {}
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        return {}
    return _parse_corr_matrix_json(raw)


def _parse_corr_matrix_json(obj: dict[str, Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for k, v in obj.items():
        if not isinstance(v, dict):
            continue
        inner: dict[str, float] = {}
        for k2, v2 in v.items():
            if v2 is None:
                continue
            try:
                inner[str(k2)] = float(v2)
            except (TypeError, ValueError):
                continue
        if inner:
            out[str(k)] = inner
    return out


def get_latest_desk_open_card(pair: str) -> dict[str, Any] | None:
    res = (
        _client()
        .table("desk_open_cards")
        .select("*")
        .eq("pair", pair)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return rows[0] if rows else None


def update_desk_open_card_flags(
    pair: str,
    date_str: str,
    *,
    invalidation_triggered: bool | None = None,
    telemetry_status: str | None = None,
) -> None:
    payload: dict[str, Any] = {}
    if invalidation_triggered is not None:
        payload["invalidation_triggered"] = invalidation_triggered
    if telemetry_status is not None:
        payload["telemetry_status"] = telemetry_status
    if not payload:
        return
    (
        _client()
        .table("desk_open_cards")
        .update(payload)
        .eq("pair", pair)
        .eq("date", date_str)
        .execute()
    )


def update_desk_open_card_telemetry_audit(
    pair: str, date_str: str, telemetry_audit_patch: Mapping[str, Any]
) -> None:
    current = (
        _client()
        .table("desk_open_cards")
        .select("telemetry_audit")
        .eq("pair", pair)
        .eq("date", date_str)
        .maybe_single()
        .execute()
    )
    current_row = cast(dict[str, Any] | None, current.data if current is not None else None)
    existing = (
        cast(dict[str, Any], current_row.get("telemetry_audit"))
        if current_row and isinstance(current_row.get("telemetry_audit"), dict)
        else {}
    )
    merged = {**existing, **dict(telemetry_audit_patch)}
    (
        _client()
        .table("desk_open_cards")
        .update({"telemetry_audit": merged})
        .eq("pair", pair)
        .eq("date", date_str)
        .execute()
    )


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


def write_brief_log(
    date_str: str,
    brief_text: str,
    macro_context: str,
    *,
    dollar_dominance: float | None = None,
    idiosyncratic_outlier: str | None = None,
    sentiment_json: Mapping[str, Any] | None = None,
) -> None:
    """Upsert unified daily summary into `brief_log` (systemic + sentiment pre-baked for UI)."""
    payload: dict[str, Any] = {
        "date": date_str,
        "brief_text": brief_text,
        "macro_context": macro_context or None,
        "dollar_dominance": float(dollar_dominance) if dollar_dominance is not None else None,
        "idiosyncratic_outlier": idiosyncratic_outlier,
        "sentiment_json": dict(sentiment_json) if sentiment_json is not None else None,
    }
    _client().table("brief_log").upsert(payload, on_conflict="date").execute()


def get_rpc_calculate_dual_correlation(pair: str, lookback: int) -> float | None:
    """Pearson corr: pair log-returns vs mean of other G10 log-returns (Gamma SQL)."""

    res = (
        _client()
        .rpc(
            "calculate_dual_correlation",
            {"p_pair": pair, "p_lookback": int(lookback)},
        )
        .execute()
    )
    raw: Any = res.data
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)) and len(raw) > 0:
        raw = raw[0]
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None


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


def get_historical_signals(pair: str, limit: int = 1260) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("signals")
        .select(
            "date,rate_diff_2y,rate_diff_10y,breakeven_inflation_10y,"
            "cot_percentile,realized_vol_5d,realized_vol_20d,oi_delta,spot,cross_asset_us10y",
        )
        .eq("pair", pair)
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def delete_pipeline_data_for_date(date_str: str) -> None:
    """Remove pipeline-owned rows for one calendar date (SRE rollback; service role)."""

    d = str(date_str)[:10]
    client = _client()
    tables_eq_date: tuple[tuple[str, str], ...] = (
        ("signals", "date"),
        ("regime_calls", "date"),
        ("brief_log", "date"),
        ("historical_prices", "date"),
        ("strategy_ledger", "date"),
        ("desk_open_cards", "date"),
    )
    for table, col in tables_eq_date:
        client.table(table).delete().eq(col, d).execute()
    client.table("research_analogs").delete().eq("as_of_date", d).execute()


def get_historical_regime_calls(pair: str, limit: int = 5000) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("regime_calls")
        .select("date,regime,signal_composite")
        .eq("pair", pair)
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return list(reversed(rows))


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


def write_historical_macro_surprises(rows: list[Mapping[str, Any]]) -> None:
    """Batch upsert historical release rows (consensus vs actual)."""
    if not rows:
        return
    payload_rows: list[dict[str, Any]] = []
    for r in rows:
        row = cast(dict[str, Any], dict(r))
        if isinstance(row.get("date"), date):
            row["date"] = _date_iso(row["date"])
        payload_rows.append(row)
    (
        _client()
        .table("historical_macro_surprises")
        .upsert(payload_rows, on_conflict="event_name,date")
        .execute()
    )


def fetch_event_aliases() -> list[dict[str, Any]]:
    res = (
        _client()
        .table("event_aliases")
        .select("canonical_name,alias_name")
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def get_historical_macro_surprises(event_name: str) -> list[dict[str, Any]]:
    from src.analysis.event_name_normalize import expand_event_names_for_query

    names = expand_event_names_for_query(event_name)
    res = (
        _client()
        .table("historical_macro_surprises")
        .select("date,event_name,surprise_direction,surprise_bps")
        .in_("event_name", names)
        .order("date", desc=True)
        .limit(10000)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return list(reversed(rows))


def get_historical_macro_surprises_date_universe(limit: int = 50000) -> list[dict[str, Any]]:
    """All (date, event_name) rows for pure-date filtering (multi-release days)."""
    res = (
        _client()
        .table("historical_macro_surprises")
        .select("date,event_name")
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return list(reversed(rows))


def write_historical_prices(rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        return
    payload_rows = [cast(dict[str, Any], dict(r)) for r in rows]
    _client().table("historical_prices").upsert(payload_rows, on_conflict="pair,date").execute()


def get_rpc_historical_analogs(
    pair: str,
    as_of_date: str,
    current_trend: float,
    current_comp: float,
    *,
    limit_rows: int = 3,
) -> list[dict[str, Any]]:
    """Run ``match_historical_analogs`` in Postgres (no deep history fetch in Python)."""

    res = _client().rpc(
        "match_historical_analogs",
        {
            "target_pair": pair,
            "as_of_date": as_of_date,
            "current_trend": current_trend,
            "current_comp": current_comp,
            "limit_rows": limit_rows,
        },
    ).execute()
    return cast(list[dict[str, Any]], res.data or [])


def get_historical_prices(pair: str, limit: int = 10000) -> list[dict[str, Any]]:
    """Return the latest ``limit`` rows for the pair, oldest-first (for time-series walks)."""
    res = (
        _client()
        .table("historical_prices")
        .select("date,pair,open,high,low,close,volume")
        .eq("pair", pair)
        .order("date", desc=True)
        .limit(limit)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return list(reversed(rows))


def write_research_analogs(rows: list[Mapping[str, Any]]) -> None:
    if not rows:
        return
    payload_rows = [cast(dict[str, Any], dict(r)) for r in rows]
    (
        _client()
        .table("research_analogs")
        .upsert(payload_rows, on_conflict="pair,as_of_date,rank")
        .execute()
    )


def get_latest_research_analogs(pair: str, as_of_date: str) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("research_analogs")
        .select(
            "as_of_date,pair,rank,match_date,match_score,forward_30d_return,regime_stability,context_label,current_trend_5d,matched_trend_5d,current_composite",
        )
        .eq("pair", pair)
        .eq("as_of_date", as_of_date)
        .order("rank", desc=False)
        .limit(3)
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def write_event_risk_matrices(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    payload_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = cast(dict[str, Any], dict(row))
        if isinstance(payload.get("date"), date):
            payload["date"] = _date_iso(payload["date"])
        payload_rows.append(payload)
    (
        _client()
        .table("event_risk_matrices")
        .upsert(payload_rows, on_conflict="date,pair,event_name")
        .execute()
    )


def get_event_risk_matrix(date_str: str, pair: str, event_name: str) -> dict[str, Any] | None:
    res = (
        _client()
        .table("event_risk_matrices")
        .select(
            "date,pair,event_name,active_regime,sample_size,median_mie_multiplier,"
            "beat_median_return,miss_median_return,inline_median_return,asymmetry_ratio,"
            "asymmetry_direction,t1_exhaustion_p2_5,t1_exhaustion_p16,t1_exhaustion_p84,"
            "t1_exhaustion_p97_5,t1_tail_risk_p95,t1_tail_risk_p05",
        )
        .eq("date", date_str)
        .eq("pair", pair)
        .eq("event_name", event_name)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return rows[0] if rows else None


def get_strategy_ledger_entry(
    ledger_date: date | str,
    pair: str,
    regime: str,
    primary_driver: str,
) -> dict[str, Any] | None:
    iso = _date_iso(ledger_date)
    res = (
        _client()
        .table("strategy_ledger")
        .select("*")
        .eq("date", iso)
        .eq("pair", pair)
        .eq("regime", regime)
        .eq("primary_driver", primary_driver)
        .maybe_single()
        .execute()
    )
    if res is None:
        return None
    raw = res.data
    if not isinstance(raw, dict):
        return None
    return cast(dict[str, Any], raw)


def write_ledger_entry(row: dict[str, Any]) -> None:
    payload = cast(dict[str, Any], dict(row))
    if isinstance(payload.get("date"), date):
        payload["date"] = _date_iso(payload["date"])
    (
        _client()
        .table("strategy_ledger")
        .upsert(payload, on_conflict="date,pair,regime,primary_driver")
        .execute()
    )


def get_open_ledger_entries(pair: str) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("strategy_ledger")
        .select("*")
        .eq("pair", pair)
        .is_("t5_hit", "null")
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def update_ledger_entries(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    payload_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = cast(dict[str, Any], dict(row))
        if isinstance(payload.get("date"), date):
            payload["date"] = _date_iso(payload["date"])
        payload_rows.append(payload)
    (
        _client()
        .table("strategy_ledger")
        .upsert(payload_rows, on_conflict="date,pair,regime,primary_driver")
        .execute()
    )


def write_research_memo(
    *,
    date_str: str,
    title: str,
    raw_content: str,
    ai_thesis_summary: list[str],
    link_url: str,
) -> None:
    payload: dict[str, Any] = {
        "date": str(date_str)[:10],
        "title": title,
        "raw_content": raw_content,
        "ai_thesis_summary": ai_thesis_summary,
        "link_url": link_url,
    }
    _client().table("research_memos").upsert(payload, on_conflict="link_url").execute()


def get_latest_research_memo_thesis_bullets() -> list[str]:
    """Latest memo thesis only (daily desk briefs must not load raw_content)."""

    res = (
        _client()
        .table("research_memos")
        .select("ai_thesis_summary")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    if not rows:
        return []
    raw = rows[0].get("ai_thesis_summary")
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
    return out[:5]
