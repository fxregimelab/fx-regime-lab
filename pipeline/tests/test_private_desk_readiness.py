"""Pure readiness checks for private-desk report and date-only daily cohorts."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from src.private_desk.readiness import PAIRS, assess_readiness


def _expected_date(now: datetime) -> str:
    candidate = now.astimezone(UTC).date() - timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate.isoformat()


def _report(now: datetime, *, bar_date: str | None = None) -> dict[str, Any]:
    observed = bar_date or _expected_date(now)
    return {
        "schema_version": "private-fx-v1",
        "generated_at": now.isoformat(),
        "current_context_updated_at": now.isoformat(),
        "universe": list(PAIRS),
        "pair_reports": [
            {
                "pair": pair,
                "data_coverage": {
                    "status": "VALID",
                    "interval": "1d",
                    "last_bar": observed,
                },
                "candidate": {
                    "status": "ABSTAIN",
                    "as_of": observed,
                    "probability": None,
                },
            }
            for pair in PAIRS
        ],
    }


def _codes(reasons: list[dict[str, str]]) -> set[str]:
    return {reason["code"] for reason in reasons}


def _pair(result: dict[str, Any], pair: str = "EURUSD") -> dict[str, Any]:
    return next(check for check in result["pair_checks"] if check["pair"] == pair)


def test_current_report_is_json_safe_and_does_not_mutate_input() -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    report = _report(now)
    before = deepcopy(report)

    result = assess_readiness(report, now=now)

    assert result == {
        "method": "private-readiness-v1",
        "checked_at": "2026-10-01T12:00:00+00:00",
        "status": "CURRENT",
        "global_hold": False,
        "report_age_seconds": 0.0,
        "context_age_seconds": 0.0,
        "expected_completed_bar_date": "2026-09-30",
        "reasons": [],
        "pair_checks": [
            {
                "pair": pair,
                "status": "CURRENT",
                "reasons": [],
                "as_of": "2026-09-30",
                "last_bar": "2026-09-30",
                "weekday_lag": 0,
            }
            for pair in PAIRS
        ],
    }
    assert report == before
    json.dumps(result, allow_nan=False)


def test_exactly_48_hours_and_non_utc_offsets_are_accepted() -> None:
    now = datetime(2026, 10, 5, 8, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    report = _report(now)
    boundary = now.astimezone(UTC) - timedelta(hours=48)
    report["generated_at"] = boundary.astimezone(timezone(timedelta(hours=-4))).isoformat()
    report["current_context_updated_at"] = boundary.isoformat()

    result = assess_readiness(report, now=now)

    assert result["status"] == "CURRENT"
    assert result["report_age_seconds"] == 172800.0
    assert result["context_age_seconds"] == 172800.0
    assert result["checked_at"] == "2026-10-05T02:30:00+00:00"
    assert result["expected_completed_bar_date"] == "2026-10-02"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("generated_at", None, "INVALID_REPORT_CLOCK"),
        ("generated_at", "2026-10-01", "INVALID_REPORT_CLOCK"),
        ("generated_at", "not-a-clock", "INVALID_REPORT_CLOCK"),
        ("generated_at", "2026-10-01T12:00:01+00:00", "FUTURE_REPORT_CLOCK"),
        ("current_context_updated_at", None, "INVALID_CONTEXT_CLOCK"),
        ("current_context_updated_at", "2026-10-01T12:00:00", "INVALID_CONTEXT_CLOCK"),
        (
            "current_context_updated_at",
            "2026-10-01T12:00:01+00:00",
            "FUTURE_CONTEXT_CLOCK",
        ),
    ],
)
def test_invalid_and_future_global_clocks_fail_closed(
    field: str, value: object, code: str
) -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    report = _report(now)
    report[field] = value

    result = assess_readiness(report, now=now)

    assert result["status"] == "HOLD"
    assert result["global_hold"] is True
    assert code in _codes(result["reasons"])
    age_field = "report_age_seconds" if field == "generated_at" else "context_age_seconds"
    assert result[age_field] is None or result[age_field] < 0


@pytest.mark.parametrize(
    ("field", "code"),
    [("generated_at", "STALE_REPORT"), ("current_context_updated_at", "STALE_CONTEXT")],
)
def test_global_clock_older_than_48_hours_holds(field: str, code: str) -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    report = _report(now)
    report[field] = (now - timedelta(hours=48, microseconds=1)).isoformat()

    result = assess_readiness(report, now=now)

    assert result["status"] == "HOLD"
    assert result["global_hold"] is True
    assert code in _codes(result["reasons"])


def test_fresh_context_cannot_rescue_stale_report_or_stale_prices() -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    report = _report(now, bar_date="2026-09-29")
    report["generated_at"] = (now - timedelta(hours=49)).isoformat()
    report["current_context_updated_at"] = now.isoformat()

    result = assess_readiness(report, now=now)

    assert result["status"] == "HOLD"
    assert result["global_hold"] is True
    assert "STALE_REPORT" in _codes(result["reasons"])
    assert all("STALE_BAR_DATE" in _codes(check["reasons"]) for check in result["pair_checks"])


@pytest.mark.parametrize(
    "change",
    [
        lambda report: report.update(schema_version="wrong"),
        lambda report: report.update(universe=list(reversed(PAIRS))),
        lambda report: report.update(universe=[*PAIRS, "USDJPY"]),
        lambda report: report.update(pair_reports="not-a-list"),
        lambda report: report["pair_reports"].pop(),
        lambda report: report["pair_reports"].append(report["pair_reports"][0].copy()),
        lambda report: report["pair_reports"][0].update(pair="USDJPY"),
        lambda report: report["pair_reports"].__setitem__(0, None),
    ],
)
def test_schema_universe_and_exact_row_failures_are_global(change: Any) -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    report = _report(now)
    change(report)

    result = assess_readiness(report, now=now)

    assert result["status"] == "HOLD"
    assert result["global_hold"] is True
    assert result["reasons"]


@pytest.mark.parametrize("bad_report", [None, [], "report", 7, True])
def test_unexpected_top_level_types_return_a_sanitized_global_hold(bad_report: Any) -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)

    result = assess_readiness(bad_report, now=now)

    assert result["status"] == "HOLD"
    assert result["global_hold"] is True
    assert "INVALID_REPORT" in _codes(result["reasons"])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    ("mutate", "codes"),
    [
        (
            lambda row: row.update(data_coverage=None),
            {"INVALID_DATA_COVERAGE", "INVALID_INTERVAL", "INVALID_LAST_BAR_DATE"},
        ),
        (
            lambda row: row["data_coverage"].update(status="UNAVAILABLE"),
            {"INVALID_DATA_COVERAGE"},
        ),
        (lambda row: row["data_coverage"].update(interval="1h"), {"INVALID_INTERVAL"}),
        (lambda row: row.update(candidate=[]), {"INVALID_AS_OF_DATE"}),
        (lambda row: row["candidate"].update(as_of=20260930), {"INVALID_AS_OF_DATE"}),
        (
            lambda row: row["candidate"].update(as_of="2026-9-30"),
            {"INVALID_AS_OF_DATE"},
        ),
        (
            lambda row: row["data_coverage"].update(last_bar="2026-02-30"),
            {"INVALID_LAST_BAR_DATE"},
        ),
        (
            lambda row: row["data_coverage"].update(last_bar="2026-09-29"),
            {"BAR_DATE_MISMATCH"},
        ),
    ],
)
def test_pair_field_failures_hold_only_the_affected_pair(mutate: Any, codes: set[str]) -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    report = _report(now)
    mutate(report["pair_reports"][0])

    result = assess_readiness(report, now=now)

    assert result["status"] == "PARTIAL"
    assert result["global_hold"] is False
    assert result["reasons"] == []
    assert codes <= _codes(_pair(result)["reasons"])
    if "INVALID_AS_OF_DATE" in codes:
        assert _pair(result)["as_of"] is None
    if "INVALID_LAST_BAR_DATE" in codes:
        assert _pair(result)["last_bar"] is None
    assert all(check["status"] == "CURRENT" for check in result["pair_checks"][1:])


@pytest.mark.parametrize(
    ("bar_date", "code", "lag"),
    [
        ("2026-09-29", "STALE_BAR_DATE", 1),
        ("2026-09-25", "STALE_BAR_DATE", 3),
        ("2026-10-01", "INCOMPLETE_BAR_DATE", 0),
        ("2026-10-03", "INCOMPLETE_BAR_DATE", 0),
    ],
)
def test_stale_and_incomplete_dates_are_pair_scoped(
    bar_date: str, code: str, lag: int
) -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    report = _report(now)
    row = report["pair_reports"][0]
    row["candidate"]["as_of"] = bar_date
    row["data_coverage"]["last_bar"] = bar_date

    result = assess_readiness(report, now=now)

    check = _pair(result)
    assert result["status"] == "PARTIAL"
    assert result["global_hold"] is False
    assert code in _codes(check["reasons"])
    assert check["weekday_lag"] == lag


def test_all_stale_pairs_hold_without_a_global_structure_hold() -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    report = _report(now, bar_date="2026-09-29")

    result = assess_readiness(report, now=now)

    assert result["status"] == "HOLD"
    assert result["global_hold"] is False
    assert result["reasons"] == []
    assert all(check["status"] == "HOLD" for check in result["pair_checks"])


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 10, 3, 12, tzinfo=UTC), "2026-10-02"),
        (datetime(2026, 10, 4, 12, tzinfo=UTC), "2026-10-02"),
        (datetime(2026, 10, 5, 12, tzinfo=UTC), "2026-10-02"),
        (datetime(2026, 10, 6, 12, tzinfo=UTC), "2026-10-05"),
    ],
)
def test_completed_daily_cutoff_walks_back_over_weekends(
    now: datetime, expected: str
) -> None:
    result = assess_readiness(_report(now), now=now)

    assert result["status"] == "CURRENT"
    assert result["expected_completed_bar_date"] == expected


def test_giant_date_span_computes_weekday_lag_without_day_by_day_iteration() -> None:
    now = datetime(9999, 12, 31, 12, tzinfo=UTC)
    report = _report(now)
    row = report["pair_reports"][0]
    row["candidate"]["as_of"] = "0001-01-01"
    row["data_coverage"]["last_bar"] = "0001-01-01"

    result = assess_readiness(report, now=now)

    assert result["status"] == "PARTIAL"
    assert _pair(result)["weekday_lag"] == 2_608_613


def test_abstention_and_other_research_fields_are_ignored_and_preserved() -> None:
    now = datetime(2026, 10, 1, 12, tzinfo=UTC)
    report = _report(now)
    report["pair_reports"][0]["candidate"].update(
        status="ABSTAIN", direction="SELL", probability=0.99, expected_r=9.0
    )
    before = deepcopy(report)

    result = assess_readiness(report, now=now)

    assert result["status"] == "CURRENT"
    assert report == before
    assert "candidate" not in result


@pytest.mark.parametrize("bad_now", ["2026-10-01T12:00:00Z", None, 0])
def test_non_datetime_decision_clock_is_rejected(bad_now: Any) -> None:
    with pytest.raises(TypeError, match="offset-aware"):
        assess_readiness({}, now=bad_now)


def test_naive_decision_clock_is_rejected() -> None:
    with pytest.raises(ValueError, match="offset-aware"):
        assess_readiness({}, now=datetime(2026, 10, 1, 12))


def test_decision_clock_must_allow_a_previous_utc_day() -> None:
    with pytest.raises(ValueError, match="previous UTC"):
        assess_readiness({}, now=datetime.min.replace(tzinfo=UTC))
