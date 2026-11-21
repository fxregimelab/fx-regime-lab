"""Pure request-time freshness checks for the private FX research desk."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from src.private_desk.universe import PAIRS as PAIRS

MAX_AGE_SECONDS = 48 * 60 * 60
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def _hold_reason(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _parse_clock(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
        offset = parsed.utcoffset()
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None or offset is None:
        return None
    try:
        return parsed.astimezone(UTC)
    except (OverflowError, ValueError):
        return None


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or _DATE_PATTERN.fullmatch(value) is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _expected_completed_bar_date(now_utc: datetime) -> date:
    expected = now_utc.date() - timedelta(days=1)
    while expected.weekday() >= 5:
        expected -= timedelta(days=1)
    return expected


def _weekday_lag(observed: date, expected: date) -> int:
    """Count weekdays in (observed, expected] without walking a large date span."""
    if observed >= expected:
        return 0
    span = (expected - observed).days
    full_weeks, remainder = divmod(span, 7)
    lag = full_weeks * 5
    start_ordinal = observed.toordinal() + full_weeks * 7
    for day_offset in range(1, remainder + 1):
        if date.fromordinal(start_ordinal + day_offset).weekday() < 5:
            lag += 1
    return lag


def assess_readiness(report: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    """Assess saved report and date-only daily-bar freshness without side effects."""
    if not isinstance(now, datetime):
        raise TypeError("now must be an offset-aware datetime")
    try:
        offset = now.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise ValueError("now must be an offset-aware datetime") from exc
    if now.tzinfo is None or offset is None:
        raise ValueError("now must be an offset-aware datetime")
    try:
        now_utc = now.astimezone(UTC)
        expected = _expected_completed_bar_date(now_utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError("now must allow a previous UTC calendar day") from exc
    global_reasons: list[dict[str, str]] = []

    if not isinstance(report, dict):
        source: dict[str, Any] = {}
        global_reasons.append(_hold_reason("INVALID_REPORT", "Report must be an object."))
    else:
        source = report

    if source.get("schema_version") != "private-fx-v1":
        global_reasons.append(
            _hold_reason("INVALID_SCHEMA", "Report schema must be private-fx-v1.")
        )

    universe = source.get("universe")
    if not isinstance(universe, list) or universe != list(PAIRS):
        global_reasons.append(
            _hold_reason(
                "INVALID_UNIVERSE",
                "Report universe must contain the eight private-desk pairs in canonical order.",
            )
        )

    report_clock = _parse_clock(source.get("generated_at"))
    report_age_seconds: float | None = None
    if report_clock is None:
        global_reasons.append(
            _hold_reason("INVALID_REPORT_CLOCK", "generated_at must be an offset-aware timestamp.")
        )
    else:
        report_age_seconds = (now_utc - report_clock).total_seconds()
        if report_age_seconds < 0:
            global_reasons.append(
                _hold_reason("FUTURE_REPORT_CLOCK", "generated_at cannot be later than checked_at.")
            )
        elif report_age_seconds > MAX_AGE_SECONDS:
            global_reasons.append(
                _hold_reason("STALE_REPORT", "Report age exceeds the 48-hour limit.")
            )

    context_clock = _parse_clock(source.get("current_context_updated_at"))
    context_age_seconds: float | None = None
    if context_clock is None:
        global_reasons.append(
            _hold_reason(
                "INVALID_CONTEXT_CLOCK",
                "current_context_updated_at must be an offset-aware timestamp.",
            )
        )
    else:
        context_age_seconds = (now_utc - context_clock).total_seconds()
        if context_age_seconds < 0:
            global_reasons.append(
                _hold_reason(
                    "FUTURE_CONTEXT_CLOCK",
                    "current_context_updated_at cannot be later than checked_at.",
                )
            )
        elif context_age_seconds > MAX_AGE_SECONDS:
            global_reasons.append(
                _hold_reason("STALE_CONTEXT", "Current context age exceeds the 48-hour limit.")
            )

    rows = source.get("pair_reports")
    rows_by_pair: dict[str, list[dict[str, Any]]] = {pair: [] for pair in PAIRS}
    foreign_rows = False
    malformed_rows = False
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                malformed_rows = True
                continue
            pair = row.get("pair")
            if not isinstance(pair, str) or pair not in rows_by_pair:
                foreign_rows = True
                continue
            rows_by_pair[pair].append(row)
    else:
        malformed_rows = True

    row_counts = {pair: len(pair_rows) for pair, pair_rows in rows_by_pair.items()}
    if (
        not isinstance(rows, list)
        or len(rows) != len(PAIRS)
        or malformed_rows
        or foreign_rows
        or any(count != 1 for count in row_counts.values())
    ):
        global_reasons.append(
            _hold_reason(
                "INVALID_PAIR_REPORTS",
                "Pair reports must contain exactly one object for each private-desk pair.",
            )
        )

    pair_checks: list[dict[str, Any]] = []
    current_pairs = 0
    for pair in PAIRS:
        pair_reasons: list[dict[str, str]] = []
        pair_rows = rows_by_pair[pair]
        as_of_text: str | None = None
        last_bar_text: str | None = None
        observed: date | None = None

        if len(pair_rows) == 0:
            pair_reasons.append(
                _hold_reason("MISSING_PAIR_ROW", f"{pair} report row is missing.")
            )
        elif len(pair_rows) > 1:
            pair_reasons.append(
                _hold_reason("DUPLICATE_PAIR_ROW", f"{pair} has more than one report row.")
            )
        else:
            row = pair_rows[0]
            coverage = row.get("data_coverage")
            candidate = row.get("candidate")
            if not isinstance(coverage, dict) or coverage.get("status") != "VALID":
                pair_reasons.append(
                    _hold_reason(
                        "INVALID_DATA_COVERAGE",
                        f"{pair} daily data coverage is missing or unavailable.",
                    )
                )
            if not isinstance(coverage, dict) or coverage.get("interval") != "1d":
                pair_reasons.append(
                    _hold_reason("INVALID_INTERVAL", f"{pair} interval must be 1d.")
                )

            as_of_value = candidate.get("as_of") if isinstance(candidate, dict) else None
            last_bar_value = coverage.get("last_bar") if isinstance(coverage, dict) else None
            as_of = _parse_date(as_of_value)
            last_bar = _parse_date(last_bar_value)
            as_of_text = as_of.isoformat() if as_of is not None else None
            last_bar_text = last_bar.isoformat() if last_bar is not None else None
            if as_of is None:
                pair_reasons.append(
                    _hold_reason(
                        "INVALID_AS_OF_DATE", f"{pair} candidate as_of must be a canonical date."
                    )
                )
            if last_bar is None:
                pair_reasons.append(
                    _hold_reason(
                        "INVALID_LAST_BAR_DATE",
                        f"{pair} data_coverage.last_bar must be a canonical date.",
                    )
                )
            if as_of is not None and last_bar is not None:
                if as_of != last_bar:
                    pair_reasons.append(
                        _hold_reason(
                            "BAR_DATE_MISMATCH",
                            f"{pair} candidate as_of and last_bar must agree.",
                        )
                    )
                else:
                    observed = as_of
                    if observed > expected:
                        pair_reasons.append(
                            _hold_reason(
                                "INCOMPLETE_BAR_DATE",
                                f"{pair} bar date is later than the completed daily cutoff.",
                            )
                        )
                    elif observed < expected:
                        pair_reasons.append(
                            _hold_reason(
                                "STALE_BAR_DATE",
                                f"{pair} bar date is older than the completed daily cutoff.",
                            )
                        )

        lag = _weekday_lag(observed, expected) if observed is not None else None
        pair_status = "HOLD" if pair_reasons else "CURRENT"
        if pair_status == "CURRENT":
            current_pairs += 1
        pair_checks.append(
            {
                "pair": pair,
                "status": pair_status,
                "reasons": pair_reasons,
                "as_of": as_of_text,
                "last_bar": last_bar_text,
                "weekday_lag": lag,
            }
        )

    global_hold = bool(global_reasons)
    if global_hold or current_pairs == 0:
        status = "HOLD"
    elif current_pairs == len(PAIRS):
        status = "CURRENT"
    else:
        status = "PARTIAL"

    return {
        "method": "private-readiness-v1",
        "checked_at": now_utc.isoformat(),
        "status": status,
        "global_hold": global_hold,
        "report_age_seconds": report_age_seconds,
        "context_age_seconds": context_age_seconds,
        "expected_completed_bar_date": expected.isoformat(),
        "reasons": global_reasons,
        "pair_checks": pair_checks,
    }
