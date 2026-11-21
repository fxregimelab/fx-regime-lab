"""Source-bound price context for manual technical analysis, without trade qualification."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.private_desk.engine import _window_has_gap, validate_bars
from src.private_desk.universe import PAIRS, UNIVERSE_VERSION

METHOD = "private-bias-context-v1"
IDENTITY_VERSION = "private-bias-observation-v1"
DIAGNOSTIC_HORIZON = 5
MODE = "MANUAL_BIAS_CONTEXT"
LIMITS = [
    "Observed price context, not a continuation/reversal forecast or a trade instruction.",
    "No consolidated total OTC FX volume; no confirmed Wyckoff phase or order flow.",
    "Policy levels and current AI scenarios do not establish fundamental directional support.",
    "Probability, forecast expectancy and positive-skew or power-law qualification are unavailable.",
    "Provider daily reconstruction; source gaps remain visible and are not interpolated.",
]


def _source_bars(meta: dict[str, Any], pair: str, state_dir: Path) -> list[dict[str, Any]]:
    path = Path(meta["capture_path"]).resolve()
    if not path.is_relative_to(state_dir.resolve()):
        raise ValueError("SOURCE_PATH_INVALID")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != meta.get("sha256"):
        raise ValueError("SOURCE_HASH_MISMATCH")
    capture = json.loads(raw)
    if any(value.get("pair") != pair or value.get("interval") != "1d" for value in (meta, capture)):
        raise ValueError("SOURCE_IDENTITY_MISMATCH")
    received = _received(meta)
    if _received(capture.get("metadata", {})) != received:
        raise ValueError("RECEIPT_CLOCK_INVALID")
    return capture["bars"]


def _received(meta: dict[str, Any]) -> datetime:
    value = datetime.fromisoformat(meta.get("received_at", meta.get("retrieved_at", "")).replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("RECEIPT_CLOCK_INVALID")
    return value.astimezone(UTC)


def describe_bias(
    pair: str, bars: list[dict[str, Any]], meta: dict[str, Any], *, as_of: str | None
) -> dict[str, Any]:
    """Describe only completed observations at the explicit, immutable cutoff."""
    if pair not in PAIRS or meta.get("pair") != pair or meta.get("interval") != "1d":
        raise ValueError("SOURCE_IDENTITY_MISMATCH")
    received = _received(meta)
    clean = validate_bars(bars)
    if any(len(b["time"]) != 10 or date.fromisoformat(b["time"]).weekday() > 4 for b in clean):
        raise ValueError("BAR_SCHEMA_INVALID")
    completed = [b for b in clean if b["time"] < received.date().isoformat()]
    cutoff = as_of if as_of is not None else (completed[-1]["time"] if completed else None)
    if cutoff is not None:
        parsed = date.fromisoformat(cutoff)
        if parsed.weekday() > 4 or parsed >= received.date():
            raise ValueError("CUTOFF_NOT_COMPLETED")
    available = [b for b in completed if cutoff is not None and b["time"] <= cutoff]

    def window(count: int) -> list[dict[str, Any]]:
        if len(available) < count or available[-1]["time"] != cutoff:
            return []
        result = available[-count:]
        return [] if _window_has_gap(result, 0, len(result) - 1, check_calendar=True) else result

    short, long = window(6), window(21)
    move5 = short[-1]["close"] / short[0]["close"] - 1 if short else None
    move20 = long[-1]["close"] / long[0]["close"] - 1 if long else None
    efficiency = position = None
    if long:
        distance = sum(abs(b["close"] - a["close"]) for a, b in zip(long, long[1:], strict=False))
        efficiency = abs(long[-1]["close"] - long[0]["close"]) / distance if distance else 0.0
        lo, hi = min(b["low"] for b in long[1:]), max(b["high"] for b in long[1:])
        position = (long[-1]["close"] - lo) / (hi - lo) if hi > lo else None
    status, phase, bias, direction = "UNAVAILABLE", "UNAVAILABLE", None, None
    continuation = reversal = "UNAVAILABLE"
    evidence: list[str] = []
    if move5 is not None:
        status = "SHORT_TERM_ONLY"
        bias = "BULLISH" if move5 > 0 else "BEARISH" if move5 < 0 else "MIXED"
        direction = "BUY" if move5 > 0 else "SELL" if move5 < 0 else None
        evidence.append("Five-day observed close change is available.")
    if move5 is not None and move20 is not None and efficiency is not None:
        status, bias, direction = "DESCRIPTIVE_AVAILABLE", "MIXED", None
        continuation = reversal = "NO_DEFINED_WATCH"
        if move5 * move20 > 0 and efficiency >= 0.30:
            phase = "TREND_UP" if move20 > 0 else "TREND_DOWN"
            bias, direction = ("BULLISH", "BUY") if move20 > 0 else ("BEARISH", "SELL")
            continuation = "WATCH"
            evidence.append("Five- and twenty-day moves agree; observed path efficiency is at least 0.30.")
        elif move5 * move20 < 0:
            phase, reversal = "TRANSITION", "WATCH"
            evidence.append("Five- and twenty-day moves conflict; investigate a possible transition.")
        else:
            phase = "RANGE"
            evidence.append("The fixed descriptive trend condition is not met.")
    return {
        "method": METHOD,
        "pair": pair,
        "as_of": cutoff,
        "source_metadata": dict(meta),
        "completed_before_utc_date": received.date().isoformat(),
        "status": status,
        "technical_bias": bias,
        "direction": direction,
        "price_phase": phase,
        "continuation_watch": continuation,
        "reversal_watch": reversal,
        "observations": {
            "five_day_close_change": move5,
            "twenty_day_close_change": move20,
            "path_efficiency_20": efficiency,
            "range_position_20": position,
        },
        "component_availability": {
            "five_day": "AVAILABLE" if short else "UNAVAILABLE_WINDOW",
            "twenty_day": "AVAILABLE" if long else "UNAVAILABLE_WINDOW",
            "range_position": "AVAILABLE" if position is not None else "UNAVAILABLE_WINDOW_OR_ZERO_RANGE",
        },
        "evidence": evidence,
        "fundamental_directional_relation": "UNAVAILABLE",
        "volume_confirmation": "UNAVAILABLE_TOTAL_OTC_VOLUME",
        "wyckoff_phase": "UNCONFIRMED",
        "probability": None,
        "forecast_expectancy": None,
        "forecast_qualification": "UNQUALIFIED",
        "return_tail_qualification": "UNQUALIFIED",
        "limitations": LIMITS,
    }


def brief_for_row(row: dict[str, Any], state_dir: Path) -> dict[str, Any]:
    meta = row.get("source_metadata", {})
    as_of = row.get("candidate", {}).get("as_of")
    try:
        return describe_bias(row["pair"], _source_bars(meta, row["pair"], state_dir), meta, as_of=as_of)
    except (OSError, KeyError, TypeError, ValueError, OverflowError):
        return {
            "method": METHOD, "pair": row["pair"], "as_of": as_of,
            "source_metadata": dict(meta), "status": "UNAVAILABLE",
            "technical_bias": None, "direction": None, "price_phase": "UNAVAILABLE",
            "continuation_watch": "UNAVAILABLE", "reversal_watch": "UNAVAILABLE",
            "observations": {}, "component_availability": {},
            "evidence": ["Original daily source or explicit cutoff did not pass validation."],
            "fundamental_directional_relation": "UNAVAILABLE",
            "volume_confirmation": "UNAVAILABLE_TOTAL_OTC_VOLUME",
            "wyckoff_phase": "UNCONFIRMED", "probability": None, "forecast_expectancy": None,
            "forecast_qualification": "UNQUALIFIED", "return_tail_qualification": "UNQUALIFIED",
            "limitations": LIMITS,
        }


def attach_bias_context(report: dict[str, Any], state_dir: Path) -> None:
    if report.get("universe_version") != UNIVERSE_VERSION:
        return
    report["desk_mode"] = MODE
    report["bias_context"] = {
        "method": METHOD, "diagnostic_holding_days": DIAGNOSTIC_HORIZON,
        "purpose": "Support or challenge manual technical analysis; owner chooses entries and exits.",
        "qualification": "DESCRIPTIVE_NOT_FORECAST", "limitations": LIMITS,
    }
    for row in report["pair_reports"]:
        row["bias_brief"] = brief_for_row(row, state_dir)


def verify_bias_context(report: dict[str, Any], state_dir: Path) -> None:
    if report.get("desk_mode") != MODE:
        if any("bias_brief" in row for row in report.get("pair_reports", [])):
            raise ValueError("Bias briefs require the explicit desk mode")
        return
    copy = json.loads(json.dumps(report))
    attach_bias_context(copy, state_dir)
    if copy["bias_context"] != report.get("bias_context") or any(
        row.get("bias_brief") != copy["pair_reports"][index]["bias_brief"]
        for index, row in enumerate(report["pair_reports"])
    ):
        raise ValueError("Bias context does not replay from its original daily source")


def publish_bias(state_dir: Path) -> dict[str, Any]:
    """Append a new owner-mode report, preserving the exact parent and all research."""
    from src.private_desk.journal import _put
    from src.private_desk.report import _publish_report, atomic_json, detach_current_review

    target = state_dir / "report.json"
    parent = target.read_bytes()
    parent_hash = hashlib.sha256(parent).hexdigest()
    _put(state_dir / "bias" / ("parent-" + parent_hash + ".json"), parent)
    report = json.loads(parent)
    attach_bias_context(report, state_dir)
    verify_bias_context(report, state_dir)
    detach_current_review(report, reason="Manual bias context was added; previous AI was not revalidated.")
    report["bias_publication"] = {
        "created_at": datetime.now(UTC).isoformat(), "parent_report_sha256": parent_hash,
        "method": METHOD, "network_or_model_call": False,
    }
    if target.read_bytes() != parent:
        raise ValueError("Report changed during bias publication")
    artifact = state_dir / "reports" / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-bias-" + uuid4().hex + ".json")
    atomic_json(artifact, report)
    _publish_report(state_dir, artifact, report)
    return report
