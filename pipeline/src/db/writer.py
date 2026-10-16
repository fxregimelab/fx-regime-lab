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
import logging
import os
from collections.abc import Mapping, Sequence
from datetime import date
from functools import lru_cache
from typing import Any, cast

from postgrest.exceptions import APIError
from postgrest.types import CountMethod
from supabase import Client, create_client

from src.db.repositories.desk_card import DeskCardRepository
from src.db.repositories.regime_call import RegimeCallRepository
from src.db.repositories.signal import SignalRepository
from src.db.repositories.validation_log import ValidationLogRepository
from src.types import DeskOpenCardRow, RegimeCall, SignalRow

logger = logging.getLogger(__name__)

_validation_log_repo: ValidationLogRepository | None = None
_regime_call_repo: RegimeCallRepository | None = None
_signal_repo: SignalRepository | None = None
_desk_card_repo: DeskCardRepository | None = None


def _validation_log() -> ValidationLogRepository:
    global _validation_log_repo
    if _validation_log_repo is None:
        _validation_log_repo = ValidationLogRepository(lambda: _client())
    return _validation_log_repo


def _regime_call() -> RegimeCallRepository:
    global _regime_call_repo
    if _regime_call_repo is None:
        _regime_call_repo = RegimeCallRepository(lambda: _client())
    return _regime_call_repo


def _signal() -> SignalRepository:
    global _signal_repo
    if _signal_repo is None:
        _signal_repo = SignalRepository(lambda: _client())
    return _signal_repo


def _desk_card() -> DeskCardRepository:
    global _desk_card_repo
    if _desk_card_repo is None:
        _desk_card_repo = DeskCardRepository(lambda: _client())
    return _desk_card_repo


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
    _signal().write_signal_row(row)


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
    return _regime_call().write_regime_call(
        call, correlation_id=correlation_id, write_hash=write_hash
    )


def write_desk_open_card(card: DeskOpenCardRow) -> None:
    _desk_card().write_desk_open_card(card)


def write_desk_open_cards_bulk(cards: Sequence[DeskOpenCardRow]) -> None:
    _desk_card().write_desk_open_cards_bulk(cards)


def write_call_rationale(rows: list[dict[str, Any]]) -> None:
    """Bulk upsert call_rationale rows on call_id. Graceful if table missing."""
    if not rows:
        return
    try:
        _client().table("call_rationale").upsert(rows, on_conflict="call_id").execute()
    except APIError as exc:
        msg = str(getattr(exc, "message", "")) or str(exc)
        if 'relation "call_rationale" does not exist' in msg:
            logger.warning("call_rationale write skipped (table does not exist)")
            return
        raise


def get_desk_open_cards_for_date(date_str: str) -> list[dict[str, Any]]:
    return _desk_card().get_desk_open_cards_for_date(date_str)


def get_rpc_fx_correlation_matrix() -> dict[str, dict[str, float]]:
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
    return _desk_card().get_latest_desk_open_card(pair)


def update_desk_open_card_flags(
    pair: str,
    date_str: str,
    *,
    invalidation_triggered: bool | None = None,
    telemetry_status: str | None = None,
) -> None:
    _desk_card().update_desk_open_card_flags(
        pair,
        date_str,
        invalidation_triggered=invalidation_triggered,
        telemetry_status=telemetry_status,
    )


def update_desk_open_card_telemetry_audit(
    pair: str, date_str: str, telemetry_audit_patch: Mapping[str, Any]
) -> None:
    _desk_card().update_desk_open_card_telemetry_audit(
        pair, date_str, telemetry_audit_patch
    )


def get_validation_log_entry(call_date: date | str, pair: str) -> dict[str, Any] | None:
    """Fetch the current (non-superseded) validation_log row for a call + pair.

    Falls back to ``date`` when ``call_date`` column is not yet migrated.
    Probes the schema once and caches the result to avoid repeated failed
    queries.
    """
    return _validation_log().get_validation_log_entry(call_date, pair)


def write_validation_row(row: Mapping[str, Any]) -> None:
    """Insert a validation_log row, versioning if materially different.

    The validation_log is an append-only ledger. If a current
    (non-superseded) row already exists for the same call and the new
    payload is materially different, the existing row is marked
    ``is_superseded = true`` and the new row is inserted. If the payload
    is identical, the write is skipped.
    """
    _validation_log().write_validation_row(row)


def supersede_validation_row(row_id: str | int) -> None:
    """Mark a single validation_log row as superseded (append-only cleanup).

    Use for test rows or data-quality repairs that should no longer be the
    current version for their (date, pair) key.
    """
    _validation_log().supersede_validation_row(row_id)


def update_validation_log_row(
    row_id: str | int, updates: Mapping[str, Any]
) -> None:
    """In-place update of derived fields on a validation_log row.

    This is intentionally **not** a versioning write: it is used for bulk
    corrections of derived/calculated fields (cost, net return, net
    correctness) when the underlying source spot price and prediction are
    unchanged.
    """
    _validation_log().update_validation_log_row(row_id, updates)


def bulk_rewrite_validation_rows(
    old_ids: list[str | int], new_rows: list[dict[str, Any]]
) -> None:
    """Versioned bulk correction of validation_log rows.

    Marks the old rows superseded and inserts the corrected rows in bulk.
    This obeys the append-only ledger rule while avoiding thousands of
    round-trips.
    """
    _validation_log().bulk_rewrite_validation_rows(old_ids, new_rows)


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
    structured_summary: Mapping[str, Any] | None = None,
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
    if structured_summary is not None:
        payload["structured_summary"] = dict(structured_summary)
    if pair_regimes is not None:
        payload["pair_regimes"] = dict(pair_regimes)
        for pair, regime in pair_regimes.items():
            col = f"{pair.lower()}_regime"
            if col in {
                "eurusd_regime", "usdjpy_regime", "usdinr_regime",
            }:
                payload[col] = regime
    _client().table("brief_log").upsert(payload, on_conflict="date").execute()


def get_rpc_calculate_dual_correlation(pair: str, lookback: int) -> float | None:
    """Pearson corr: pair log-returns vs mean of other FX basket log-returns."""

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
    return _regime_call().get_latest_regime_call(pair)


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
    return _signal().get_signal_for_pair_date(pair, date_str)


def get_historical_signals(pair: str, limit: int = 1260) -> list[dict[str, Any]]:
    return _signal().get_historical_signals(pair, limit=limit)


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
    return _regime_call().get_historical_regime_calls(pair, limit=limit)


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


def write_historical_yields(rows: list[dict[str, Any]]) -> None:
    """Bulk upsert historical_yields rows on date,series_id."""
    if not rows:
        return
    _client().table("historical_yields").upsert(
        rows, on_conflict="date,series_id"
    ).execute()


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
    res2 = (
        client.table("historical_prices")
        .select("date,pair,open,high,low,close,volume")
        .eq("pair", pair)
        .lte("date", str(date_str)[:10])
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if res2 is not None:
        raw = res2.data
        if isinstance(raw, list) and raw:
            return cast(dict[str, Any], raw[0])
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)
    return None


def get_unvalidated_regime_calls(limit: int | None = None) -> list[dict[str, Any]]:
    """Return regime_calls rows lacking a current validation_log entry with brier_score_t5.

    Ordered by date ascending (oldest first) so backfill proceeds chronologically.
    Superseded validation_log rows are ignored.
    """
    return _validation_log().get_unvalidated_regime_calls(limit=limit)


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


def write_simulation_results(rows: list[dict[str, Any]]) -> None:
    """Bulk insert simulation_results rows."""
    if not rows:
        return
    _client().table("simulation_results").insert(rows).execute()


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


def bulk_write_backfill_results(
    pair: str,
    results: Sequence[tuple[SignalRow, RegimeCall]],
) -> None:
    """Bulk-persist backfill (signal, call) tuples for a single pair.

    This is a deliberate, audited exception for ``signals`` and
    ``regime_calls``: backfills must first purge stale reconstructed rows
    for the pair before inserting the regenerated history. Triggers are
    disabled for the duration, deletes/inserts are committed per batch, and
    triggers are re-enabled before the function returns.

    ``validation_log`` is intentionally untouched: it is an immutable
    append-only ledger and is never deleted or updated here (the trigger
    that blocks UPDATE/DELETE remains enabled).
    """
    _regime_call().bulk_write_backfill_results(pair, results)


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
    return _validation_log().get_validation_log_for_stats(
        pair_filter=pair_filter, lookback_days=lookback_days
    )


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
    date_str = str(payload.get("date") or "")[:10]
    if date_str:
        _client().table("pipeline_runs").delete().eq("date", date_str).execute()
    _client().table("pipeline_runs").insert(payload).execute()


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
        .select("id", count=CountMethod.exact)
        .eq("date", str(date_str)[:10])
        .execute()
    )
    return getattr(res, "count", 0) or 0


def count_regime_calls_for_date(date_str: str) -> int:
    res = (
        _client()
        .table("regime_calls")
        .select("id", count=CountMethod.exact)
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
    """Count current (non-superseded) validation_log rows for a date."""
    try:
        res = (
            _client()
            .table("validation_log")
            .select("id", count=CountMethod.exact)
            .eq("date", str(date_str)[:10])
            .eq("is_superseded", False)
            .execute()
        )
        return getattr(res, "count", 0) or 0
    except APIError as exc:
        msg = str(getattr(exc, "message", "")) or str(exc)
        if "column validation_log.is_superseded does not exist" in msg:
            res = (
                _client()
                .table("validation_log")
                .select("id", count=CountMethod.exact)
                .eq("date", str(date_str)[:10])
                .execute()
            )
            return getattr(res, "count", 0) or 0
        raise


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
