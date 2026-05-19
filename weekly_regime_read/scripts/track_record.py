#!/usr/bin/env python3
"""
Phase C (Accountability) — Weekly Regime Read Track Record Builder.

Connects to Supabase, queries ``validation_log`` and ``regime_calls``,
builds a scorecard of live/confirmed/awaiting/invalidated/revised signals,
and writes a JSON artifact for the weekly-post pipeline.

Usage::

    export SUPABASE_URL=https://...
    export SUPABASE_SERVICE_ROLE_KEY=...
    python weekly_regime_read/scripts/track_record.py

Output::

    weekly_regime_read/output/track_record_YYYYMMDD.json
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from postgrest.exceptions import APIError
from supabase import Client, create_client

logger = logging.getLogger("track_record")

# ── Paths ──
ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Status constants ──
STATUS_CONFIRMED = "Confirmed"
STATUS_AWAITING = "Awaiting"
STATUS_INVALIDATED = "Invalidated"
STATUS_REVISED = "Revised"

STATUS_EMOJI = {
    STATUS_CONFIRMED: "[OK]",
    STATUS_AWAITING: "[WAIT]",
    STATUS_INVALIDATED: "[FAIL]",
    STATUS_REVISED: "[REV]",
}


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------

# Fallback credentials (same as data_fetcher.py)
_DEFAULT_SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://weaaacohvzzgkgxzpaee.supabase.co",
)
_DEFAULT_SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndlYWFhY29odnp6Z2tneHpwYWVlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTMxNjEzMSwiZXhwIjoyMDkwODkyMTMxfQ.rL_WtoH5CXFbb4P0Jdj_ZJoCtyearfCskwYVZHI4_Ys",
)


def _client() -> Client:
    url = os.environ.get("SUPABASE_URL") or _DEFAULT_SUPABASE_URL
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or _DEFAULT_SUPABASE_KEY
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment."
        )
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _today() -> date:
    return date.today()


def _iso(d: date) -> str:
    return d.isoformat()


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def fetch_recent_validation_log(days: int = 30) -> list[dict[str, Any]]:
    """Fetch ``validation_log`` rows from the last *days* calendar days."""
    cutoff = _today() - timedelta(days=days)
    client = _client()

    select_cols = (
        "id,date,call_date,pair,predicted_direction,predicted_regime,confidence,"
        "actual_direction,actual_direction_t5,actual_direction_t20,"
        "actual_return_1d,actual_return_5d,actual_return_20d,"
        "correct_1d,correct_5d,correct_20d,correct_t5,correct_t20,"
        "log_return_t5_bps,log_return_t20_bps,pnl_bps,"
        "brier_score_t5,brier_score_t20,notes,is_superseded"
    )

    q = (
        client.table("validation_log")
        .select(select_cols)
        .gte("date", _iso(cutoff))
        .order("date", desc=True)
    )

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


def fetch_regime_calls(days: int = 30) -> list[dict[str, Any]]:
    """Fetch ``regime_calls`` from the last *days* calendar days."""
    cutoff = _today() - timedelta(days=days)
    client = _client()

    select_cols = (
        "id,date,pair,regime,confidence,signal_composite,rate_signal,"
        "cot_signal,vol_signal,rr_signal,oi_signal,primary_driver,"
        "predicted_direction,stop_level,special_signal_value,special_signal_label,"
        "created_at"
    )

    q = (
        client.table("regime_calls")
        .select(select_cols)
        .gte("date", _iso(cutoff))
        .order("date", desc=True)
    )

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


# ---------------------------------------------------------------------------
# Bulk price loader
# ---------------------------------------------------------------------------

def load_price_cache(pairs: set[str], start: date) -> dict[str, list[dict[str, Any]]]:
    """Fetch all historical OHLC bars for *pairs* from *start* to today.

    Returns a dict ``{pair: [bar, ...]}`` ordered by date ascending.
    This batches the work into one paginated query per pair, avoiding
    the N+1 API storm that happens when every signal fetches prices
    individually.
    """
    cache: dict[str, list[dict[str, Any]]] = {}
    end = _today()
    client = _client()

    for pair in pairs:
        bars: list[dict[str, Any]] = []
        page_size = 1000
        page = 0
        while True:
            q = (
                client.table("historical_prices")
                .select("date,pair,open,high,low,close")
                .eq("pair", pair)
                .gte("date", _iso(start))
                .lte("date", _iso(end))
                .order("date", desc=False)
            )
            res = q.range(page * page_size, (page + 1) * page_size - 1).execute()
            rows = cast(list[dict[str, Any]], res.data or [])
            if not rows:
                break
            bars.extend(rows)
            if len(rows) < page_size:
                break
            page += 1
        cache[pair] = bars
        logger.info("  Cached %4d bars for %s", len(bars), pair)

    return cache


def get_bar_for_date(bars: list[dict[str, Any]], target: date) -> dict[str, Any] | None:
    """Return the bar whose date == *target*, or ``None``."""
    iso = _iso(target)
    for bar in bars:
        if str(bar.get("date"))[:10] == iso:
            return bar
    return None


def get_latest_bar(bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the last bar in the list (assumes ascending order)."""
    return bars[-1] if bars else None


def get_bars_from_date(bars: list[dict[str, Any]], start: date) -> list[dict[str, Any]]:
    """Return bars with date >= *start*."""
    iso = _iso(start)
    out: list[dict[str, Any]] = []
    for bar in bars:
        if str(bar.get("date"))[:10] >= iso:
            out.append(bar)
    return out


# ---------------------------------------------------------------------------
# Threshold / stop-level logic
# ---------------------------------------------------------------------------

def stop_level_crossed(call: dict[str, Any], bars: list[dict[str, Any]]) -> bool:
    """Return ``True`` if price ever traded through the call's stop_level.

    For a BULLISH call the stop is a lower bound (triggered if ``low <= stop``).
    For a BEARISH call the stop is an upper bound (triggered if ``high >= stop``).
    """
    stop_raw = call.get("stop_level")
    if stop_raw is None or not bars:
        return False

    try:
        stop_px = float(stop_raw)
    except (TypeError, ValueError):
        return False

    direction = str(
        call.get("rate_signal") or call.get("predicted_direction") or ""
    ).strip().upper()

    for bar in bars:
        high = float(bar.get("high") or bar.get("close") or 0)
        low = float(bar.get("low") or bar.get("close") or 0)
        if direction == "BULLISH" and low <= stop_px:
            return True
        if direction == "BEARISH" and high >= stop_px:
            return True
    return False


# ---------------------------------------------------------------------------
# Status resolution
# ---------------------------------------------------------------------------

def _is_resolved(validation: dict[str, Any]) -> bool:
    """Return ``True`` if the validation row has a definitive outcome."""
    if validation.get("correct_t5") is not None:
        return True
    if validation.get("correct_5d") is not None:
        return True
    if validation.get("correct_1d") is not None:
        return True
    actual = str(validation.get("actual_direction") or "").strip().upper()
    if actual and actual != "NEUTRAL":
        return True
    actual_t5 = str(validation.get("actual_direction_t5") or "").strip().upper()
    if actual_t5 and actual_t5 != "NEUTRAL":
        return True
    return False


def _status_from_validation(validation: dict[str, Any]) -> str:
    """Map a validation row to one of the four canonical statuses."""
    if validation.get("correct_t5") is True:
        return STATUS_CONFIRMED
    if validation.get("correct_t5") is False:
        return STATUS_INVALIDATED

    if validation.get("correct_5d") is True:
        return STATUS_CONFIRMED
    if validation.get("correct_5d") is False:
        return STATUS_INVALIDATED

    if validation.get("correct_1d") is True:
        return STATUS_CONFIRMED
    if validation.get("correct_1d") is False:
        return STATUS_INVALIDATED

    pred = str(validation.get("predicted_direction") or "").strip().upper()
    for actual_key in ("actual_direction_t5", "actual_direction"):
        actual = str(validation.get(actual_key) or "").strip().upper()
        if actual:
            if actual == "NEUTRAL":
                return STATUS_AWAITING
            if pred and actual == pred:
                return STATUS_CONFIRMED
            if pred and actual != pred:
                return STATUS_INVALIDATED

    return STATUS_AWAITING


def determine_status(
    call: dict[str, Any],
    validation: dict[str, Any] | None,
    newer_calls: list[dict[str, Any]],
) -> str:
    """Determine the signal status.

    Priority:
    1. Explicit superseded flag → Revised
    2. Newer call for same pair with different direction → Revised (if unresolved)
    3. Validation data → Confirmed / Invalidated / Awaiting
    4. No validation yet → Awaiting
    """
    if validation and validation.get("is_superseded"):
        return STATUS_REVISED

    call_date = str(call.get("date"))[:10]
    pair = str(call.get("pair"))
    pred = str(
        call.get("predicted_direction") or call.get("rate_signal") or ""
    ).strip().upper()

    for nc in newer_calls:
        nc_date = str(nc.get("date"))[:10]
        nc_pair = str(nc.get("pair"))
        if nc_pair == pair and nc_date > call_date:
            nc_pred = str(
                nc.get("predicted_direction") or nc.get("rate_signal") or ""
            ).strip().upper()
            if nc_pred and nc_pred != pred and not _is_resolved(validation or {}):
                return STATUS_REVISED

    if validation is not None:
        return _status_from_validation(validation)

    return STATUS_AWAITING


# ---------------------------------------------------------------------------
# P&L / points computation
# ---------------------------------------------------------------------------

def _bps_from_validation(validation: dict[str, Any] | None) -> float | None:
    """Extract basis-point return from a validation row, trying several keys."""
    if validation is None:
        return None

    if validation.get("pnl_bps") is not None:
        return float(validation["pnl_bps"])

    if validation.get("log_return_t5_bps") is not None:
        return float(validation["log_return_t5_bps"])

    if validation.get("log_return_t20_bps") is not None:
        return float(validation["log_return_t20_bps"])

    if validation.get("actual_return_5d") is not None:
        return float(validation["actual_return_5d"]) * 10_000.0

    if validation.get("actual_return_1d") is not None:
        return float(validation["actual_return_1d"]) * 10_000.0

    return None


def compute_bps(
    call: dict[str, Any],
    validation: dict[str, Any] | None,
    price_cache: dict[str, list[dict[str, Any]]],
) -> float | None:
    """Return basis points since the call date.

    Prefers validated returns when available, otherwise computes from the
    latest cached historical price vs the entry price on the call date.
    """
    validated = _bps_from_validation(validation)
    if validated is not None:
        return validated

    pair = str(call.get("pair"))
    call_date = date.fromisoformat(str(call.get("date"))[:10])
    bars = price_cache.get(pair, [])

    entry_bar = get_bar_for_date(bars, call_date)
    if entry_bar is None:
        # Try nearest earlier bar
        for bar in reversed(bars):
            if str(bar.get("date"))[:10] <= _iso(call_date):
                entry_bar = bar
                break

    if entry_bar is None or entry_bar.get("close") is None:
        return None

    entry_close = float(entry_bar["close"])
    if entry_close == 0:
        return None

    latest_bar = get_latest_bar(bars)
    if latest_bar is None or latest_bar.get("close") is None:
        return None

    latest_close = float(latest_bar["close"])
    return (latest_close - entry_close) / entry_close * 10_000.0


def format_pips(bps: float | None, pair: str) -> str:
    """Pretty-print basis points as pips/points."""
    if bps is None:
        return "—"

    approx_pips = bps / 100.0
    pip_unit = "pip" if abs(approx_pips) < 2 else "pips"

    if "JPY" in pair.upper():
        return f"{bps:+.0f} bps ({approx_pips:+.2f} {pip_unit})"
    if "INR" in pair.upper():
        return f"{bps:+.0f} bps ({approx_pips:+.2f} paise)"
    return f"{bps:+.0f} bps ({approx_pips:+.2f} {pip_unit})"


# ---------------------------------------------------------------------------
# Scorecard builder
# ---------------------------------------------------------------------------

def build_scorecard(
    validation_rows: list[dict[str, Any]],
    regime_calls: list[dict[str, Any]],
    price_cache: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build the running scorecard table entries."""

    # Index validations by (pair, date)
    validation_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for v in validation_rows:
        key = (str(v.get("pair")), str(v.get("date"))[:10])
        validation_by_key[key] = v

    # Index regime calls by pair for revised-signal detection
    calls_by_pair: dict[str, list[dict[str, Any]]] = {}
    for c in regime_calls:
        pair = str(c.get("pair"))
        calls_by_pair.setdefault(pair, []).append(c)
    for lst in calls_by_pair.values():
        lst.sort(key=lambda x: str(x.get("date")), reverse=True)

    scorecard: list[dict[str, Any]] = []

    for call in regime_calls:
        pair = str(call.get("pair"))
        call_date = str(call.get("date"))[:10]
        key = (pair, call_date)

        validation = validation_by_key.get(key)
        newer_calls = calls_by_pair.get(pair, [])

        status = determine_status(call, validation, newer_calls)
        bps = compute_bps(call, validation, price_cache)
        pips_text = format_pips(bps, pair)

        regime = str(call.get("regime") or "")
        rate_signal = str(call.get("rate_signal") or "")
        primary_driver = str(call.get("primary_driver") or "")

        signal_desc = f"{pair} — {regime}"
        if rate_signal:
            signal_desc += f" ({rate_signal})"
        if primary_driver:
            signal_desc += f" | {primary_driver}"

        # Threshold check (stop_level breach)
        bars = get_bars_from_date(price_cache.get(pair, []), date.fromisoformat(call_date))
        breached = stop_level_crossed(call, bars)

        scorecard.append(
            {
                "signal": signal_desc,
                "pair": pair,
                "date_flagged": call_date,
                "status": status,
                "status_emoji": STATUS_EMOJI[status],
                "pips_since": pips_text,
                "bps_raw": bps,
                "predicted_direction": rate_signal or call.get("predicted_direction"),
                "confidence": call.get("confidence"),
                "stop_level": call.get("stop_level"),
                "special_signal_value": call.get("special_signal_value"),
                "special_signal_label": call.get("special_signal_label"),
                "stop_level_breached": breached,
                "has_validation": validation is not None,
            }
        )

    scorecard.sort(key=lambda x: x["date_flagged"], reverse=True)
    return scorecard


# ---------------------------------------------------------------------------
# Track-record paragraph
# ---------------------------------------------------------------------------

def build_track_record_paragraph(
    last_week_calls: list[dict[str, Any]],
) -> str:
    """Build a paragraph referencing last week's calls (one per pair)."""
    if not last_week_calls:
        return (
            "No directional signals were flagged in the last week. "
            "The framework remains in observation mode, scanning for regime shifts."
        )

    sentences: list[str] = []
    for call in last_week_calls:
        pair = call["pair"]
        display = PAIR_DISPLAY.get(pair, pair)
        outcome = call["outcome"]
        direction = str(call.get("predicted_direction") or "").strip().upper()
        call_text = call.get("call", "")

        if outcome == "confirmed":
            sentences.append(
                f"Last week the framework flagged {display} as {direction.lower()}. "
                f"The signal confirmed. {call_text}."
            )
        elif outcome == "awaiting":
            sentences.append(
                f"Last week the framework flagged {display} as {direction.lower()}. "
                f"The signal remains awaiting resolution. {call_text}. "
                f"The framework will validate once the T+5 horizon closes."
            )
        elif outcome == "invalidated":
            sentences.append(
                f"Last week the framework flagged {display} as {direction.lower()}. "
                f"The signal was invalidated. Price action moved against the predicted direction. "
                f"The framework updates its read and will reflag if conditions rebuild."
            )

    return " ".join(sentences)


# ---------------------------------------------------------------------------
# Markdown table
# ---------------------------------------------------------------------------

def build_markdown_table(scorecard: list[dict[str, Any]]) -> str:
    """Build the running scorecard as a Markdown table."""
    lines = [
        "| Signal | Date Flagged | Status | Pips/Points Since |",
        "|---|---|---|---|",
    ]
    for row in scorecard:
        signal = row["signal"].replace("|", "\\|")
        date_flagged = row["date_flagged"]
        status_text = f"{row['status_emoji']} {row['status']}"
        pips = row["pips_since"]
        lines.append(f"| {signal} | {date_flagged} | {status_text} | {pips} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

def build_summary(scorecard: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(scorecard)
    confirmed = sum(1 for s in scorecard if s["status"] == STATUS_CONFIRMED)
    awaiting = sum(1 for s in scorecard if s["status"] == STATUS_AWAITING)
    invalidated = sum(1 for s in scorecard if s["status"] == STATUS_INVALIDATED)
    revised = sum(1 for s in scorecard if s["status"] == STATUS_REVISED)
    resolved = confirmed + invalidated
    accuracy = (confirmed / resolved * 100.0) if resolved > 0 else None

    return {
        "total_signals": total,
        "confirmed": confirmed,
        "awaiting": awaiting,
        "invalidated": invalidated,
        "revised": revised,
        "resolved": resolved,
        "accuracy_pct": round(accuracy, 2) if accuracy is not None else None,
    }


# ---------------------------------------------------------------------------
# Last-week calls
# ---------------------------------------------------------------------------

PAIR_DISPLAY = {
    "EURUSD": "EUR/USD",
    "USDJPY": "USD/JPY",
    "USDINR": "USD/INR",
}

DIRECTIONAL_STATES = {"BEARISH", "BULLISH", "LONG", "SHORT"}


def build_last_week_calls(
    validation_rows: list[dict[str, Any]],
    regime_calls: list[dict[str, Any]],
    days_back_start: int = 14,
    days_back_end: int = 7,
) -> list[dict[str, Any]]:
    """Build last_week_calls from validation_log entries *days_back_start* to *days_back_end* ago.

    For each pair, picks the most recent directional call in that window and
    reports its outcome (confirmed / invalidated / awaiting).
    """
    window_start = _today() - timedelta(days=days_back_start)
    window_end = _today() - timedelta(days=days_back_end)

    # Index regime_calls by (pair, date)
    regime_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for rc in regime_calls:
        key = (str(rc.get("pair")), str(rc.get("date"))[:10])
        regime_by_key[key] = rc

    # Filter validation rows to the window and directional predictions
    candidates: list[dict[str, Any]] = []
    for v in validation_rows:
        call_date = str(v.get("call_date") or v.get("date"))[:10]
        cd = date.fromisoformat(call_date)
        if not (window_start <= cd <= window_end):
            continue
        pred = str(v.get("predicted_direction") or "").strip().upper()
        if pred not in DIRECTIONAL_STATES:
            continue
        candidates.append(v)

    # Group by pair, keep most recent call_date per pair
    by_pair: dict[str, dict[str, Any]] = {}
    for v in candidates:
        pair = str(v.get("pair"))
        call_date = str(v.get("call_date") or v.get("date"))[:10]
        if pair not in by_pair or call_date > str(by_pair[pair].get("call_date") or by_pair[pair].get("date"))[:10]:
            by_pair[pair] = v

    last_week_calls: list[dict[str, Any]] = []
    for pair in sorted(by_pair.keys()):
        v = by_pair[pair]
        call_date = str(v.get("call_date") or v.get("date"))[:10]

        # Look up regime_call for narrative
        rc = regime_by_key.get((pair, call_date), {})
        regime = str(rc.get("regime") or "neutral")
        composite = rc.get("signal_composite")
        composite_str = f"{composite:.2f}" if composite is not None else "N/A"

        display_pair = PAIR_DISPLAY.get(pair, pair)
        regime_display = regime.lower().replace("_", " ")
        call_text = f"{display_pair} {regime_display} with composite at {composite_str}"

        # Determine outcome
        if v.get("correct_t5") is True or v.get("correct_5d") is True:
            outcome = "confirmed"
        elif v.get("correct_t5") is False or v.get("correct_5d") is False:
            outcome = "invalidated"
        else:
            outcome = "awaiting"

        last_week_calls.append(
            {
                "pair": pair,
                "call": call_text,
                "outcome": outcome,
                "call_date": call_date,
                "predicted_direction": v.get("predicted_direction"),
            }
        )

    return last_week_calls


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    # Windows consoles often default to cp1252; force utf-8 for emoji output
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    today_str = _today().strftime("%Y%m%d")
    output_path = OUTPUT_DIR / f"track_record_{today_str}.json"

    logger.info("Phase C — Track Record Builder")

    logger.info("Fetching validation_log (last 30 days)...")
    validation_rows = fetch_recent_validation_log(days=30)
    logger.info("  → %d rows", len(validation_rows))

    logger.info("Fetching regime_calls (last 30 days)...")
    regime_calls = fetch_regime_calls(days=30)
    logger.info("  → %d rows", len(regime_calls))

    # Determine pairs and earliest date we need prices for
    pairs_needed: set[str] = set()
    earliest = _today()
    for c in regime_calls:
        pairs_needed.add(str(c.get("pair")))
        d = date.fromisoformat(str(c.get("date"))[:10])
        if d < earliest:
            earliest = d

    if pairs_needed:
        logger.info("Bulk-loading prices for %s from %s ...", pairs_needed, earliest)
        price_cache = load_price_cache(pairs_needed, earliest)
    else:
        price_cache = {}

    logger.info("Building scorecard...")
    scorecard = build_scorecard(validation_rows, regime_calls, price_cache)

    logger.info("Building last-week calls...")
    last_week_calls = build_last_week_calls(validation_rows, regime_calls)
    logger.info("  → %d last-week call(s)", len(last_week_calls))

    logger.info("Building track-record paragraph...")
    paragraph = build_track_record_paragraph(last_week_calls)

    logger.info("Building markdown table...")
    markdown_table = build_markdown_table(scorecard)

    summary = build_summary(scorecard)

    payload: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "lookback_validation_days": 30,
        "lookback_regime_days": 30,
        "last_week_days": 7,
        "summary": summary,
        "track_record_paragraph": paragraph,
        "scorecard_markdown": markdown_table,
        "scorecard": scorecard,
        "last_week_calls": last_week_calls,
        "raw_validation_rows": len(validation_rows),
        "raw_regime_calls": len(regime_calls),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Saved → %s", output_path)

    print("\n=== Track Record Paragraph ===\n")
    print(paragraph)
    print("\n=== Scorecard Markdown ===\n")
    print(markdown_table)
    print("\n=== Summary ===\n")
    print(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
