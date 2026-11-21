"""Japan's framework gaps and definition switches must not become policy momentum."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from src.private_desk import policy_history as m
from src.private_desk.report import atomic_json
from tests.test_private_desk_policy_history import RECEIPT, csv_body, saved, spec


@pytest.mark.parametrize(
    "day, expected",
    [
        ("1999-02-11", "BOJ_OVERNIGHT_CALL_TARGET"), ("1999-02-12", None),
        ("2000-08-10", None), ("2000-08-11", "BOJ_OVERNIGHT_CALL_TARGET"),
        ("2001-03-18", "BOJ_OVERNIGHT_CALL_TARGET"), ("2001-03-19", None),
        ("2006-03-08", None), ("2006-03-09", "BOJ_OVERNIGHT_CALL_EFFECTIVELY_ZERO"),
        ("2006-07-14", "BOJ_OVERNIGHT_CALL_TARGET"),
        ("2010-10-05", "BOJ_OVERNIGHT_CALL_TARGET_MIDPOINT"),
        ("2013-04-03", "BOJ_OVERNIGHT_CALL_TARGET_MIDPOINT"), ("2013-04-04", None),
        ("2016-02-16", None), ("2016-09-20", None),
        ("2016-09-21", "BOJ_SHORT_TERM_POLICY_RATE_YCC"),
        ("2024-03-20", "BOJ_SHORT_TERM_POLICY_RATE_YCC"),
        ("2024-03-21", "BOJ_OVERNIGHT_CALL_TARGET_MIDPOINT"),
        ("2024-08-01", "BOJ_OVERNIGHT_CALL_TARGET"),
        ("2026-09-24", "BOJ_OVERNIGHT_CALL_TARGET"),
    ],
)
def test_official_instrument_boundaries(day: str, expected: str | None) -> None:
    assert m.instrument_at("JPY", day) == expected


def pair_features(start: str, end: str, values: dict[str, str]) -> dict[str, Any]:
    days = []
    cursor = date.fromisoformat(start)
    while cursor.isoformat() <= end:
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    series = []
    for currency in ("USD", "JPY"):
        rows = [(day, "4" if currency == "USD" else values[day]) for day in days]
        panel = m.parse_policy_history(
            csv_body(currency, rows), spec(currency, start, end), RECEIPT
        )
        series.append({**panel, "sha256": "fixture-" + currency})
    return m.pair_policy_features({"series_audits": series}, "USDJPY")


def weekdays(start: str, end: str, before: str, after: str, boundary: str) -> dict[str, str]:
    values = {}
    cursor = date.fromisoformat(start)
    while cursor.isoformat() <= end:
        if cursor.weekday() < 5:
            values[cursor.isoformat()] = before if cursor.isoformat() < boundary else after
        cursor += timedelta(days=1)
    return values


def test_point_target_change_is_measurable_without_a_false_instrument_splice() -> None:
    values = weekdays("2001-02-26", "2001-03-05", "0.25", "0.15", "2001-02-28")
    result = pair_features("2001-02-26", "2001-03-05", values)
    last = result["rows"][-1]
    assert last["difference_change_5_weekdays_pp"] == pytest.approx(0.1)
    assert last["change_unavailable_reason"] is None
    assert result["historical_availability"] == "UNKNOWN"
    assert result["forecast_qualification"] == "UNQUALIFIED"


def test_2024_midpoint_keeps_level_but_never_spurious_cross_framework_change() -> None:
    values = weekdays("2024-03-14", "2024-03-28", "-0.1", "0.05", "2024-03-21")
    result = pair_features("2024-03-14", "2024-03-28", values)
    rows = {row["observation_date"]: row for row in result["rows"]}
    for day in ("2024-03-21", "2024-03-22", "2024-03-25", "2024-03-26", "2024-03-27"):
        assert rows[day]["policy_marker_difference_pp"] == pytest.approx(3.95)
        assert rows[day]["difference_change_5_weekdays_pp"] is None
        assert rows[day]["change_unavailable_reason"] == "INSTRUMENT_DEFINITION_BREAK"
    assert rows["2024-03-28"]["difference_change_5_weekdays_pp"] == 0


@pytest.mark.parametrize("day", ["1999-03-01", "2002-01-07", "2016-02-16"])
def test_a_numeric_cell_cannot_fill_an_interval_without_a_rate_target(day: str) -> None:
    value = {day: "0"}
    row = pair_features(day, day, value)["rows"][0]
    assert row["quote_value"] == 0  # Retain a witnessed cell; reject its feature meaning.
    assert row["quote_instrument"] is None
    assert row["policy_marker_difference_pp"] is None
    assert row["difference_change_5_weekdays_pp"] is None


@pytest.mark.parametrize("changes", [{"TITLE": "Japan actual overnight rate"}, {"DECIMALS": "2"}])
def test_japan_title_and_precision_drift_fail_closed(changes: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="title/precision"):
        m.parse_policy_history(
            csv_body("JPY", [("2024-09-09", "0.25")], **changes), spec("JPY"), RECEIPT
        )


def test_versioned_extension_preserves_every_legacy_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    records = [
        saved(tmp_path, csv_body(currency, [("2024-09-09", "1")]), spec(currency))
        for currency in m.LEGACY_CURRENCIES
    ]
    old = m.audit_records(tmp_path, records, method_version=m.LEGACY_METHOD_VERSION)
    assert old["status"] == "RETROSPECTIVE_POLICY_HISTORY"
    atomic_json(tmp_path / "evidence.json", old)
    before = {path: path.read_bytes() for path in tmp_path.glob("*") if path.is_file()}
    assert m.load_evidence(tmp_path) == old

    def capture(root: Path, request: dict[str, str], *, refresh: bool) -> dict[str, Any]:
        assert request["currency"] == "JPY" and not refresh
        return saved(root, csv_body("JPY", [("2024-09-09", "0.25")]), request)

    monkeypatch.setattr(m, "capture_policy_history", capture)
    updated = m.capture_cohort(tmp_path, [spec("JPY")])
    assert updated["method_version"] == m.METHOD_VERSION
    assert updated["status"] == "RETROSPECTIVE_POLICY_HISTORY"
    assert updated["covered_currencies"] == list(m.AREAS)
    assert updated["captures"][:7] == records
    for path, raw in before.items():
        if path.name != "evidence.json":
            assert path.read_bytes() == raw
    assert m.load_evidence(tmp_path) == updated
    assert m.audit_records(tmp_path, records, method_version=m.LEGACY_METHOD_VERSION) == old
    with pytest.raises(ValueError, match="declared method"):
        m.audit_records(tmp_path, updated["captures"], method_version=m.LEGACY_METHOD_VERSION)
    with pytest.raises(ValueError, match="Unknown"):
        m.audit_records(tmp_path, records, method_version="invented")


def test_one_invocation_accepts_all_eight_but_nine_requests_write_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requests = [spec(currency) for currency in m.AREAS]
    with pytest.raises(ValueError, match="eight"):
        m.capture_cohort(tmp_path / "refused", requests + [spec("JPY")])
    assert not (tmp_path / "refused").exists()

    def capture(root: Path, request: dict[str, str], *, refresh: bool) -> dict[str, Any]:
        return saved(root, csv_body(request["currency"], [("2024-09-09", "1")]), request)

    monkeypatch.setattr(m, "capture_policy_history", capture)
    assert m.capture_cohort(tmp_path, requests)["covered_currencies"] == list(m.AREAS)
