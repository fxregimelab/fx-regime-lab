"""
@agent_context: Primary database interface for Supabase, handling all
authenticated writes and service-role reads for the pipeline.
@allowed_imports: [json, os, collections.abc, dataclasses, datetime,
    functools, typing, supabase, src.types]
@forbidden_imports: [src.ai, src.regime, src.signals]
@obsidian_link: [[Infrastructure#Supabase Persistence]]
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import date
from functools import lru_cache
from typing import Any, cast

from postgrest.exceptions import APIError
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
        "volume_rvol": row.volume_rvol,
        "structural_instability": row.structural_instability,
        "breakeven_inflation_10y": row.breakeven_inflation_10y,
        "rate_diff_10y_real": row.rate_diff_10y_real,
        "rate_z_tactical": row.rate_z_tactical,
        "rate_z_structural": row.rate_z_structural,
        "z_blended": row.z_blended,
        "realized_vol_rank": row.realized_vol_rank,
        "skew_alignment": row.skew_alignment,
        "risk_reversal_25d": row.risk_reversal_25d,
        "fpi_flow": row.fpi_flow,
        "cot_net_pos": row.cot_net_pos,
        "cot_asset_mgr_net": row.cot_asset_mgr_net,
        "cot_lev_money_net": row.cot_lev_money_net,
        "ecb_balance_sheet": row.ecb_balance_sheet,
        "bund_btp_spread": row.bund_btp_spread,
        "boj_policy_rate": row.boj_policy_rate,
        "india_vix": row.india_vix,
        "inr_forward_premium": row.inr_forward_premium,
    }
    _client().table("signals").upsert(payload, on_conflict="pair,date").execute()


def compute_write_hash(inputs: dict[str, Any]) -> str:
    """Return SHA-256 hex digest of sorted JSON-serialized inputs.

    Used for tamper-evident regime call verification.
    """
    canonical = json.dumps(inputs, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_regime_call(
    call: RegimeCall,
    *,
    correlation_id: str | None = None,
    write_hash: str | None = None,
) -> int | str | None:
    """Insert a regime call row.  Returns the existing or new row id.

    Uses INSERT with conflict detection rather than upsert so that the
    immutable trigger (which blocks UPDATE) never fires on re-runs.
    """
    payload: dict[str, Any] = asdict(call)
    payload["date"] = _date_iso(call.date)
    if correlation_id is not None:
        payload["correlation_id"] = correlation_id
    if write_hash is not None:
        payload["write_hash"] = write_hash
    client = _client()

    # Check for existing row first — avoids immutable-trigger UPDATE error
    existing = (
        client.table("regime_calls")
        .select("id")
        .eq("pair", call.pair)
        .eq("date", payload["date"])
        .maybe_single()
        .execute()
    )
    if existing and existing.data:
        row = cast(dict[str, Any], existing.data)
        return row.get("id")

    res = client.table("regime_calls").insert(payload).execute()
    rows = cast(list[dict[str, Any]], res.data or [])
    return rows[0].get("id") if rows else None


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


# Module-level cache: True = modern schema (call_date exists),
# False = legacy schema (call_date missing), None = not yet probed.
_has_call_date: bool | None = None


def get_validation_log_entry(call_date: date | str, pair: str) -> dict[str, Any] | None:
    """Fetch existing validation_log row for a given call_date + pair.

    Falls back to ``date`` when ``call_date`` column is not yet migrated.
    Probes the schema once and caches the result to avoid repeated failed
    queries.
    """
    global _has_call_date
    iso = _date_iso(call_date)
    client = _client()

    if _has_call_date is not False:
        try:
            res = (
                client.table("validation_log")
                .select("*")
                .eq("call_date", iso)
                .eq("pair", pair)
                .maybe_single()
                .execute()
            )
            if res is not None:
                raw = res.data
                if isinstance(raw, dict):
                    _has_call_date = True
                    return cast(dict[str, Any], raw)
        except APIError as exc:
            msg = str(getattr(exc, "message", "")) or str(exc)
            if "column validation_log.call_date does not exist" in msg:
                _has_call_date = False
            else:
                raise

    # Legacy schema fallback
    res = (
        client.table("validation_log")
        .select("*")
        .eq("date", iso)
        .eq("pair", pair)
        .maybe_single()
        .execute()
    )
    if res is not None:
        raw = res.data
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)
    return None


def write_validation_row(row: Mapping[str, Any]) -> None:
    """Insert or update validation_log row.

    Uses ``call_id`` as the conflict key when available (preferred for
    idempotency).  Falls back to ``call_date, pair`` or ``date, pair``
    depending on schema maturity.

    Guard: if the existing row already has T+5 data (non-null
    ``log_return_t5_bps``), the T+5 fields in *payload* are stripped so
    the immutable validation trigger is not violated.

    If no unique constraint exists for upsert, falls back to manual
    select-then-insert/update to avoid silent failures.
    """
    payload = cast(dict[str, Any], dict(row))
    client = _client()

    call_id = payload.get("call_id")
    call_date = payload.get("call_date")
    pair = payload.get("pair")
    date_val = call_date or payload.get("date")

    # ── Guard against overwriting validated T+5 data ────────────────
    existing_id: int | None = None
    if call_id is not None:
        try:
            existing = (
                client.table("validation_log")
                .select("id,log_return_t5_bps")
                .eq("call_id", call_id)
                .maybe_single()
                .execute()
            )
            if existing is not None and existing.data is not None:
                raw = existing.data
                if isinstance(raw, dict):
                    if raw.get("log_return_t5_bps") is not None:
                        for key in (
                            "log_return_t5_bps",
                            "correct_t5",
                            "brier_score_t5",
                            "actual_direction_t5",
                            "actual_return_5d",
                            "correct_5d",
                            "brier_5d",
                        ):
                            payload.pop(key, None)
                    existing_id = raw.get("id")
        except APIError:
            pass  # Schema may not have call_id yet

    # If no existing row by call_id, try by date+pair
    if existing_id is None and pair is not None and date_val is not None:
        try:
            res = (
                client.table("validation_log")
                .select("id,log_return_t5_bps")
                .eq("pair", pair)
                .eq("date", date_val)
                .maybe_single()
                .execute()
            )
            if res is not None and res.data is not None:
                raw = res.data
                if isinstance(raw, dict):
                    if raw.get("log_return_t5_bps") is not None:
                        for key in (
                            "log_return_t5_bps",
                            "correct_t5",
                            "brier_score_t5",
                            "actual_direction_t5",
                            "actual_return_5d",
                            "correct_5d",
                            "brier_5d",
                        ):
                            payload.pop(key, None)
                    existing_id = raw.get("id")
        except APIError:
            pass

    # ── Write: upsert preferred, manual update/insert fallback ──────
    _upsert_validation_log(payload, existing_id)


def _upsert_validation_log(payload: dict[str, Any], existing_id: int | None) -> None:
    """Attempt upsert; if unique constraint missing, fall back to update/insert."""
    client = _client()

    # Prefer update when we know the row id
    if existing_id is not None:
        try:
            update_payload = {k: v for k, v in payload.items() if k != "id"}
            client.table("validation_log").update(update_payload).eq("id", existing_id).execute()
            return
        except APIError as exc:
            msg = str(getattr(exc, "message", "")) or str(exc)
            if "Could not find the '" in msg and "' column of 'validation_log'" in msg:
                col_match = msg.split("Could not find the '")[1].split("'")[0]
                update_payload.pop(col_match, None)
                (
                    client.table("validation_log")
                    .update(update_payload)
                    .eq("id", existing_id)
                    .execute()
                )
                return
            raise

    # Try upsert first
    conflict_key = "pair,date"
    if payload.get("call_id") is not None:
        conflict_key = "call_id"
    elif payload.get("call_date") is not None:
        conflict_key = "pair,call_date"

    for _attempt in range(10):
        try:
            client.table("validation_log").upsert(payload, on_conflict=conflict_key).execute()
            return
        except APIError as exc:
            msg = str(getattr(exc, "message", "")) or str(exc)

            if "Could not find the '" in msg and "' column of 'validation_log'" in msg:
                col_match = msg.split("Could not find the '")[1].split("'")[0]
                payload.pop(col_match, None)
                continue

            if "no unique or exclusion constraint matching the ON CONFLICT" in msg:
                # No upsert possible — fall back to plain insert
                # (duplicates are unlikely because we checked for existing rows above)
                try:
                    client.table("validation_log").insert(payload).execute()
                    return
                except APIError as exc2:
                    msg2 = str(getattr(exc2, "message", "")) or str(exc2)
                    if "Could not find the '" in msg2 and "' column of 'validation_log'" in msg2:
                        col_match2 = msg2.split("Could not find the '")[1].split("'")[0]
                        payload.pop(col_match2, None)
                        continue
                    if "duplicate key value violates unique constraint" in msg2:
                        return  # Row already exists
                    raise

            if (
                "column validation_log.call_date does not exist" in msg
                and "pair,date" not in conflict_key
            ):
                payload.pop("call_date", None)
                conflict_key = "pair,date"
                continue

            raise


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
    pair_regimes: Mapping[str, str] | None = None,
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
    if pair_regimes is not None:
        payload["pair_regimes"] = dict(pair_regimes)
        for pair, regime in pair_regimes.items():
            col = f"{pair.lower()}_regime"
            if col in {
                "eurusd_regime", "usdjpy_regime", "usdinr_regime",
                "gbpusd_regime", "audusd_regime", "usdcad_regime", "usdchf_regime",
            }:
                payload[col] = regime
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
    _client().rpc(
        "increment_ai_usage",
        {"p_date": date_str, "p_purpose": purpose, "p_model": model}
    ).execute()


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


def delete_pipeline_data_for_date(date_str: str, *, force: bool = False) -> None:
    """Remove pipeline-owned rows for one calendar date (SRE rollback; service role).

    Args:
        date_str: Calendar date to purge (YYYY-MM-DD).
        force: If False, raises an exception because the ledger is immutable.
            If True, performs the deletion after logging to audit_log.
    """
    if not force:
        raise RuntimeError(
            "Immutable ledger: historical data deletion requires force=True. "
            "Pass force=True only in genuine emergency situations."
        )

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

    # Log to audit_log before deleting
    for table, col in tables_eq_date:
        rows = client.table(table).select("*").eq(col, d).execute()
        for row in cast(list[dict[str, Any]], rows.data or []):
            _log_audit(operation="DELETE", table_name=table, old_value=row)
        client.table(table).delete().eq(col, d).execute()

    analog_rows = client.table("research_analogs").select("*").eq("as_of_date", d).execute()
    for row in cast(list[dict[str, Any]], analog_rows.data or []):
        _log_audit(operation="DELETE", table_name="research_analogs", old_value=row)
    client.table("research_analogs").delete().eq("as_of_date", d).execute()


def write_pipeline_error(
    step: str,
    error_type: str,
    message: str,
    traceback_str: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Log a structured pipeline exception to ``pipeline_errors``."""
    payload: dict[str, Any] = {
        "step": step,
        "error_type": error_type,
        "message": message,
    }
    if traceback_str is not None:
        payload["traceback"] = traceback_str
    if correlation_id is not None:
        payload["correlation_id"] = correlation_id
    try:
        _client().table("pipeline_errors").insert(payload).execute()
    except Exception:
        pass


def _log_audit(
    operation: str,
    table_name: str,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    row_id: Any | None = None,
    correlation_id: str | None = None,
) -> None:
    """Write a single row to ``audit_log``.  Silently ignores errors."""
    payload: dict[str, Any] = {
        "operation": operation,
        "table_name": table_name,
        "old_value": old_value,
        "new_value": new_value,
        "correlation_id": correlation_id,
    }
    if row_id is not None:
        payload["row_id"] = row_id
    try:
        _client().table("audit_log").insert(payload).execute()
    except Exception:
        pass


def get_historical_regime_calls(pair: str, limit: int = 5000) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("regime_calls")
        .select("id,date,regime,signal_composite,rate_signal,confidence")
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


def write_historical_prices(
    rows: Sequence[Mapping[str, Any]],
    *,
    source: str | None = None,
) -> None:
    """Upsert historical price rows.  Adds ``source`` and ``fetch_timestamp`` when provided.

    Gracefully handles missing columns (schema not yet migrated) by stripping
    unknown fields and retrying — identical to the ``validation_log`` strategy.
    """
    if not rows:
        return
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    payload_rows: list[dict[str, Any]] = []
    for r in rows:
        row = cast(dict[str, Any], dict(r))
        if source is not None:
            row["source"] = source
            row["fetch_timestamp"] = now
        payload_rows.append(row)

    client = _client()
    max_retries = 10
    for _attempt in range(max_retries):
        try:
            (
                client.table("historical_prices")
                .upsert(payload_rows, on_conflict="pair,date")
                .execute()
            )
            return
        except APIError as exc:
            msg = str(getattr(exc, "message", "")) or str(exc)
            if "Could not find the '" in msg and "' column of 'historical_prices'" in msg:
                col_match = msg.split("Could not find the '")[1].split("'")[0]
                for row in payload_rows:
                    row.pop(col_match, None)
                continue
            raise


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


def get_historical_price_for_date(pair: str, date_str: str) -> dict[str, Any] | None:
    """Return a single historical price row for ``pair`` on ``date_str``.

    Prefers ``close``; falls back to the latest available price on or before
    ``date_str`` when an exact match is missing (forward-fill for weekends).
    """
    client = _client()
    # Exact match first
    res = (
        client.table("historical_prices")
        .select("date,pair,open,high,low,close,volume")
        .eq("pair", pair)
        .eq("date", str(date_str)[:10])
        .maybe_single()
        .execute()
    )
    if res is not None:
        raw = res.data
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)

    # Fallback: nearest earlier date (weekend / holiday gap)
    res = (
        client.table("historical_prices")
        .select("date,pair,open,high,low,close,volume")
        .eq("pair", pair)
        .lte("date", str(date_str)[:10])
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if res is not None:
        raw = res.data
        if isinstance(raw, list) and raw:
            return cast(dict[str, Any], raw[0])
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)
    return None


def get_unvalidated_regime_calls(limit: int | None = None) -> list[dict[str, Any]]:
    """Return regime_calls rows lacking a validation_log entry with brier_score_t5.

    Ordered by date ascending (oldest first) so backfill proceeds chronologically.
    """
    query = (
        _client()
        .table("regime_calls")
        .select("id,date,pair,regime,rate_signal,confidence")
        .order("date", desc=False)
    )
    if limit is not None:
        query = query.limit(limit)

    res = query.execute()
    calls = cast(list[dict[str, Any]], res.data or [])

    # Filter out calls that already have validation_log entries with brier_score_t5
    unvalidated: list[dict[str, Any]] = []
    for call in calls:
        call_id = call.get("id")
        call_date = str(call.get("date"))[:10]
        pair = str(call.get("pair"))

        # Check validation_log by call_id when available
        has_validation = False
        if call_id is not None:
            try:
                vres = (
                    _client()
                    .table("validation_log")
                    .select("brier_score_t5")
                    .eq("call_id", call_id)
                    .not_.is_("brier_score_t5", "null")
                    .maybe_single()
                    .execute()
                )
                if vres is not None and vres.data is not None:
                    has_validation = True
            except Exception:
                pass

        # Fallback: check by date + pair
        if not has_validation:
            try:
                vres = (
                    _client()
                    .table("validation_log")
                    .select("brier_score_t5")
                    .eq("date", call_date)
                    .eq("pair", pair)
                    .not_.is_("brier_score_t5", "null")
                    .maybe_single()
                    .execute()
                )
                if vres is not None and vres.data is not None:
                    has_validation = True
            except Exception:
                pass

        if not has_validation:
            unvalidated.append(call)

    return unvalidated


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


def research_memo_exists(link_url: str) -> bool:
    """Return True if a research_memo with this link_url already exists."""
    res = (
        _client()
        .table("research_memos")
        .select("id")
        .eq("link_url", link_url)
        .maybe_single()
        .execute()
    )
    return res is not None and res.data is not None


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


# ---------------------------------------------------------------------------
# Round 3 Phase 2 — Aggregate stats read/write
# ---------------------------------------------------------------------------


def _normalize_validation_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a legacy validation_log row to the modern schema.

    Legacy schema stores returns as decimals (``actual_return_5d``) and
    correctness in ``correct_5d``.  Modern schema uses bps
    (``log_return_t5_bps``) and horizon-specific keys.  This helper maps
    the legacy fields so that ``aggregate.py`` can consume either schema.
    """
    out = dict(row)

    # Map legacy 5d fields → modern T+5 fields
    ret_5d = row.get("actual_return_5d")
    if ret_5d is not None and "log_return_t5_bps" not in row:
        out["log_return_t5_bps"] = float(ret_5d) * 10_000.0

    corr_5d = row.get("correct_5d")
    if corr_5d is not None and "correct_t5" not in row:
        out["correct_t5"] = bool(corr_5d)

    if "actual_direction" in row and "actual_direction_t5" not in row:
        out["actual_direction_t5"] = row["actual_direction"]

    # Compute Brier score on-the-fly if missing but we have confidence + correctness
    conf = row.get("confidence")
    if conf is not None and "brier_score_t5" not in row:
        if out.get("correct_t5") is True:
            out["brier_score_t5"] = (float(conf) - 1.0) ** 2
        elif out.get("correct_t5") is False:
            out["brier_score_t5"] = float(conf) ** 2

    # Legacy schema has no separate T+20 columns — leave them absent
    return out


def get_validation_log_for_stats(
    pair_filter: str | None = None,
    lookback_days: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch validation rows for aggregate statistics.

    Returns rows with T+5/T+20 horizons populated (non-superseded only).
    If ``lookback_days`` is set, filter to calls within that window.

    Automatically adapts to both the **legacy** schema (pre-migration) and
    the **modern** schema (post-migration).
    """
    modern_select = (
        "pair,predicted_direction,confidence,date,"
        "actual_direction_t5,log_return_t5_bps,correct_t5,brier_score_t5,"
        "actual_direction_t20,log_return_t20_bps,correct_t20,brier_score_t20"
    )
    legacy_select = (
        "pair,predicted_direction,confidence,date,"
        "actual_direction,actual_return_1d,actual_return_5d,"
        "correct_1d,correct_5d"
    )

    def _build_query(select: str, include_superseded_filter: bool) -> Any:
        q = _client().table("validation_log").select(select)
        if include_superseded_filter:
            q = q.eq("is_superseded", False)
        if pair_filter:
            q = q.eq("pair", pair_filter)
        if lookback_days is not None and lookback_days > 0:
            cutoff = date.today() - __import__("datetime").timedelta(days=lookback_days)
            q = q.gte("date", cutoff.isoformat())
        return q

    def _fetch_all(q: Any) -> list[dict[str, Any]]:
        """Paginate through Supabase's 1000-row default limit."""
        all_rows: list[dict[str, Any]] = []
        page_size = 1000
        page = 0
        while True:
            res = q.range(page * page_size, (page + 1) * page_size - 1).execute()
            rows = cast(list[dict[str, Any]], res.data or [])
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < page_size:
                break
            page += 1
        return all_rows

    # Attempt modern schema first
    try:
        q = _build_query(modern_select, include_superseded_filter=True)
        return _fetch_all(q)
    except APIError as exc:
        msg = str(getattr(exc, "message", "")) or str(exc)
        if "column validation_log." in msg:
            # One or more modern columns are missing → fall back to legacy schema
            try:
                q = _build_query(legacy_select, include_superseded_filter=False)
                rows = _fetch_all(q)
            except APIError as exc2:
                msg2 = str(getattr(exc2, "message", "")) or str(exc2)
                if "is_superseded" in msg2:
                    q = _build_query(legacy_select, include_superseded_filter=False)
                    rows = _fetch_all(q)
                else:
                    raise
            return [_normalize_validation_row(r) for r in rows]
        raise


def write_validation_stats(row: Mapping[str, Any]) -> None:
    """Upsert aggregate stats into ``validation_stats`` on (as_of_date, pair)."""
    payload = cast(dict[str, Any], dict(row))
    _client().table("validation_stats").upsert(
        payload, on_conflict="as_of_date,pair"
    ).execute()


def get_latest_validation_stats_per_pair() -> list[dict[str, Any]]:
    """Fetch the most recent validation_stats row for each pair.

    Uses a simple window-function approach via RPC when available,
    otherwise falls back to fetching the latest 50 rows and de-duping.
    """
    client = _client()
    # Fallback: fetch latest rows and take first per pair
    res = (
        client.table("validation_stats")
        .select(
            "as_of_date,pair,t5_rolling_90d_accuracy,t5_win_rate,"
            "t5_mean_brier,t5_brier_skill,t5_sharpe_like"
        )
        .order("as_of_date", desc=True)
        .limit(200)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        pair = str(r.get("pair", ""))
        if pair and pair not in seen:
            seen.add(pair)
            out.append(r)
    return out


def write_pipeline_run(row: Mapping[str, Any]) -> None:
    """Upsert a pipeline health snapshot into ``pipeline_runs`` on date."""
    payload = cast(dict[str, Any], dict(row))
    _client().table("pipeline_runs").upsert(
        payload, on_conflict="date"
    ).execute()


def get_pipeline_runs_for_dates(start_iso: str, end_iso: str) -> list[dict[str, Any]]:
    """Fetch pipeline_runs rows in a date range, oldest first."""
    res = (
        _client()
        .table("pipeline_runs")
        .select("*")
        .gte("date", start_iso)
        .lte("date", end_iso)
        .order("date", desc=False)
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])


def get_pipeline_run_for_date(date_str: str) -> dict[str, Any] | None:
    """Fetch a single pipeline_runs row for a date."""
    res = (
        _client()
        .table("pipeline_runs")
        .select("*")
        .eq("date", str(date_str)[:10])
        .maybe_single()
        .execute()
    )
    if res is not None:
        raw = res.data
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)
    return None


def count_signals_for_date(date_str: str) -> int:
    res = (
        _client()
        .table("signals")
        .select("id", count="exact")
        .eq("date", str(date_str)[:10])
        .execute()
    )
    return getattr(res, "count", 0) or 0


def count_regime_calls_for_date(date_str: str) -> int:
    res = (
        _client()
        .table("regime_calls")
        .select("id", count="exact")
        .eq("date", str(date_str)[:10])
        .execute()
    )
    return getattr(res, "count", 0) or 0


def get_regime_calls_dqs_for_date(date_str: str) -> list[float]:
    res = (
        _client()
        .table("regime_calls")
        .select("data_quality_score")
        .eq("date", str(date_str)[:10])
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    scores: list[float] = []
    for r in rows:
        v = r.get("data_quality_score")
        if v is not None:
            try:
                scores.append(float(v))
            except (TypeError, ValueError):
                pass
    return scores


def count_validation_log_for_date(date_str: str) -> int:
    res = (
        _client()
        .table("validation_log")
        .select("id", count="exact")
        .eq("date", str(date_str)[:10])
        .execute()
    )
    return getattr(res, "count", 0) or 0


def brief_log_exists_for_date(date_str: str) -> bool:
    res = (
        _client()
        .table("brief_log")
        .select("id")
        .eq("date", str(date_str)[:10])
        .limit(1)
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    return bool(rows)


def macro_events_with_ai_briefs_for_date(date_str: str) -> tuple[int, int]:
    """Return (total_high_impact_events, events_with_ai_briefs) for date."""
    res = (
        _client()
        .table("macro_events")
        .select("ai_brief")
        .eq("date", str(date_str)[:10])
        .eq("impact", "HIGH")
        .execute()
    )
    rows = cast(list[dict[str, Any]], res.data or [])
    total = len(rows)
    with_brief = sum(1 for r in rows if r.get("ai_brief") not in (None, ""))
    return total, with_brief


def get_pipeline_errors_for_date(date_str: str) -> list[dict[str, Any]]:
    res = (
        _client()
        .table("pipeline_errors")
        .select("step,error_type,message")
        .eq("run_date", str(date_str)[:10])
        .execute()
    )
    return cast(list[dict[str, Any]], res.data or [])
