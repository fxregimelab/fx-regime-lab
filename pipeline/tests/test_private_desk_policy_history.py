"""Definition, missingness, causal windows and immutable source controls, without network."""

import csv
import hashlib
import io
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import requests

from src.private_desk import policy_history as m
from src.private_desk.report import atomic_json

RECEIPT = "2026-10-01T00:00:00+00:00"


def spec(
    currency: str = "EUR", start: str = "2024-09-09", end: str = "2024-09-27"
) -> dict[str, str]:
    return {"currency": currency, "start": start, "end": end}


def csv_body(currency: str, observations: list[tuple[str, str]], **changes: str) -> bytes:
    # Synthetic rows match the reviewed schema, but are never represented as live evidence.
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=m.HEADER)
    writer.writeheader()
    for day, value in observations:
        row = dict.fromkeys(m.HEADER, "")
        row.update(
            FREQ="D",
            REF_AREA=m.AREAS[currency],
            UNIT_MEASURE="368",
            UNIT_MULT="0",
            COMPILATION=m.COMPILATION[currency],
            DECIMALS="4",
            SOURCE_REF=m.SOURCES[currency],
            TITLE=(
                "Central bank policy rates - Japan - Daily - End of period"
                if currency == "JPY" else "Central bank policy rates - synthetic test"
            ),
            TIME_PERIOD=day,
            OBS_VALUE=value,
            OBS_STATUS="M" if value == "NaN" else "A",
            OBS_CONF="F",
        )
        row.update(changes)
        writer.writerow(row)
    return output.getvalue().encode()


def panel(currency: str, observations: list[tuple[str, str]]) -> dict[str, Any]:
    parsed = m.parse_policy_history(csv_body(currency, observations), spec(currency), RECEIPT)
    return {**parsed, "sha256": "test-only-" + currency}


def observations(value: str = "3") -> list[tuple[str, str]]:
    return [(f"2024-09-{day:02}", value) for day in range(9, 28)]


def saved(root: Path, body: bytes, request: dict[str, str], **overrides: Any) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    token = str(len(list(root.glob("*.bin"))))
    body_path = root / (token + ".bin")
    body_path.write_bytes(body)
    record = {
        "request": request,
        "url": m.policy_request_url(request),
        "http_status": 200,
        "content_type": "text/csv;charset=UTF-8",
        "received_at": RECEIPT,
        "body_complete": True,
        "transport_error": None,
        "capture_path": str(body_path.resolve()),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        **overrides,
    }
    path = root / (token + ".receipt.json")
    path.write_text(json.dumps(record), encoding="utf-8")
    return {
        **record,
        "receipt_file": {
            "capture_path": str(path.resolve()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    }


@pytest.mark.parametrize(
    "policy_spec",
    [
        spec("INR"),
        spec(start="1999-01-01"),
        spec(start="2024-09-28"),
        spec(start="20240909"),
        spec(end="2039-12-01"),
        {**spec(), "url": "https://example.com"},
    ],
)
def test_request_scope_is_bounded(policy_spec: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        m.policy_request_url(policy_spec)


def test_window_limit_is_calendar_years_not_31_times_366_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FutureClock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> "FutureClock":
            return cls(2040, 1, 1, tzinfo=UTC)

    monkeypatch.setattr(m, "datetime", FutureClock)
    assert m.policy_request_url(spec(start="1999-01-05", end="2030-01-05"))
    with pytest.raises(ValueError, match="31 years"):
        m.policy_request_url(spec(start="1999-01-05", end="2030-01-06"))
    assert m.policy_request_url(spec(start="2004-02-29", end="2035-02-28"))
    with pytest.raises(ValueError, match="31 years"):
        m.policy_request_url(spec(start="2004-02-29", end="2035-03-01"))


@pytest.mark.parametrize("currency", list(m.AREAS))
def test_all_reviewed_legs_preserve_missingness_and_receipt_role(currency: str) -> None:
    parsed = m.parse_policy_history(
        csv_body(currency, [("2024-09-09", "-0.25"), ("2024-09-10", "NaN")]),
        spec(currency),
        RECEIPT,
    )
    assert parsed["rows"][0]["value"] == -0.25
    assert parsed["rows"][1]["value"] is None
    assert parsed["rows"][1]["status"] == "M"
    assert parsed["rows"][0]["instrument"]


@pytest.mark.parametrize(
    "changes",
    [
        {"REF_AREA": "US"},
        {"FREQ": "M"},
        {"UNIT_MEASURE": "100"},
        {"UNIT_MULT": "2"},
        {"OBS_STATUS": "E"},
        {"OBS_STATUS": "M"},
        {"OBS_CONF": "C"},
        {"TIME_FORMAT": "P1D"},
        {"OBS_VALUE": "NaN"},
        {"OBS_VALUE": "inf"},
        {"OBS_VALUE": "-11"},
        {"OBS_VALUE": "101"},
        {"COMPILATION": "Changed source definition"},
        {"SOURCE_REF": "Unknown source"},
        {"DECIMALS": "unknown"},
        {"TITLE": ""},
        {"OBS_PRE_BREAK": "NaN"},
    ],
)
def test_schema_status_units_and_definition_drift_reject_whole_leg(changes: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        m.parse_policy_history(csv_body("EUR", [("2024-09-09", "3")], **changes), spec(), RECEIPT)


def test_equal_duplicates_once_conflicts_order_and_outside_dates_reject() -> None:
    equal = [("2024-09-09", "3"), ("2024-09-09", "3")]
    parsed = m.parse_policy_history(csv_body("EUR", equal), spec(), RECEIPT)
    assert len(parsed["rows"]) == 1 and parsed["equal_duplicates"] == 1
    for rows in [
        [("2024-09-09", "3"), ("2024-09-09", "4")],
        [("2024-09-10", "3"), ("2024-09-09", "3")],
        [("2024-09-08", "3")],
    ]:
        with pytest.raises(ValueError):
            m.parse_policy_history(csv_body("EUR", rows), spec(), RECEIPT)


def test_bad_header_body_bound_future_and_non_utc_receipts_reject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = csv_body("EUR", [("2024-09-09", "3")])
    for invalid in [body.replace(b"FREQ", b"FREQUENCY", 1), b"", body + b"malformed\n"]:
        with pytest.raises(ValueError):
            m.parse_policy_history(invalid, spec(), RECEIPT)
    for clock in ["2024-09-01T00:00:00+00:00", "2999-01-01T00:00:00+00:00", "2026-10-01"]:
        with pytest.raises(ValueError):
            m.parse_policy_history(body, spec(), clock)
    monkeypatch.setitem(m.BODY_LIMITS, "EUR", 10)
    with pytest.raises(ValueError, match="bound"):
        m.parse_policy_history(body, spec(), RECEIPT)


@pytest.mark.parametrize(
    ("currency", "before", "after"),
    [
        ("EUR", "2000-06-27", "2000-06-28"),
        ("EUR", "2008-10-14", "2008-10-15"),
        ("EUR", "2024-09-17", "2024-09-18"),
        ("GBP", "2006-08-02", "2006-08-03"),
        ("NZD", "1999-03-16", "1999-03-17"),
        ("CHF", "1999-12-31", "2000-01-01"),
        ("CHF", "2019-06-12", "2019-06-13"),
    ],
)
def test_reviewed_instrument_switches_are_not_rate_changes(
    currency: str, before: str, after: str
) -> None:
    assert m.instrument_at(currency, before) != m.instrument_at(currency, after)


def test_pair_orientation_break_suppression_and_matured_weekday_window() -> None:
    evidence = {"series_audits": [panel("EUR", observations("3")), panel("USD", observations("4"))]}
    result = m.pair_policy_features(evidence, "EURUSD")
    rows = {row["observation_date"]: row for row in result["rows"]}
    assert rows["2024-09-17"]["policy_marker_difference_pp"] == -1
    assert rows["2024-09-17"]["difference_change_5_weekdays_pp"] == 0
    assert rows["2024-09-18"]["change_unavailable_reason"] == "INSTRUMENT_DEFINITION_BREAK"
    assert rows["2024-09-24"]["difference_change_5_weekdays_pp"] is None
    assert rows["2024-09-25"]["difference_change_5_weekdays_pp"] == 0
    assert rows["2024-09-25"]["window_start"] == "2024-09-18"
    assert "2024-09-21" not in rows
    assert result["forecast_qualification"] == "UNQUALIFIED"
    assert all(row["provider_available_at"] is None for row in result["rows"])
    usd_cad = m.pair_policy_features(
        {"series_audits": [panel("USD", observations("4")), panel("CAD", observations("3"))]},
        "USDCAD",
    )
    assert usd_cad["last_numeric"]["policy_marker_difference_pp"] == 1


def test_no_fill_no_future_dependency_and_missing_leg() -> None:
    eur, usd = panel("EUR", observations()), panel("USD", observations("4"))
    missing_day = "2024-09-26"
    usd["rows"] = [row for row in usd["rows"] if row["observation_date"] != missing_day]
    evidence = {"series_audits": [eur, usd]}
    before = m.pair_policy_features(evidence, "EURUSD")
    absent = next(row for row in before["rows"] if row["observation_date"] == missing_day)
    assert absent["policy_marker_difference_pp"] is None
    assert absent["change_unavailable_reason"] == "MISSING_WEEKDAY_OR_VALUE"
    mutated = deepcopy(evidence)
    mutated["series_audits"][0]["rows"][-1]["value"] = 90
    after = m.pair_policy_features(mutated, "EURUSD")
    assert before["rows"][:-1] == after["rows"][:-1]
    missing = m.pair_policy_features({"series_audits": [eur]}, "EURGBP")
    assert missing["status"] == "UNAVAILABLE" and missing["missing_currencies"] == ["GBP"]


def test_pre_break_marker_and_unknown_instrument_suppress_features() -> None:
    base, quote = panel("GBP", observations()), panel("USD", observations("4"))
    base["rows"][-1]["pre_break_value"] = 3
    marked = m.pair_policy_features({"series_audits": [base, quote]}, "GBPUSD")
    assert marked["rows"][-1]["difference_change_5_weekdays_pp"] is None
    base["rows"][-1]["instrument"] = None
    unknown = m.pair_policy_features({"series_audits": [base, quote]}, "GBPUSD")
    assert unknown["rows"][-1]["policy_marker_difference_pp"] is None
    assert unknown["rows"][-1]["change_unavailable_reason"] == "UNKNOWN_INSTRUMENT"


def test_original_hash_replay_and_saved_audit_tampering(tmp_path: Path) -> None:
    record = saved(tmp_path, csv_body("EUR", observations()), spec())
    evidence = m.audit_records(tmp_path, [record])
    atomic_json(tmp_path / "evidence.json", evidence)
    assert m.load_evidence(tmp_path) == evidence
    evidence["series_audits"][0]["rows"][0]["value"] = 9
    atomic_json(tmp_path / "evidence.json", evidence)
    with pytest.raises(ValueError, match="reproduce"):
        m.load_evidence(tmp_path)
    Path(record["capture_path"]).write_bytes(b"changed original")
    with pytest.raises(ValueError, match="hash/length"):
        m.read_receipt(tmp_path, record["receipt_file"])


@pytest.mark.parametrize(
    "overrides",
    [
        {"http_status": 403},
        {"body_complete": False},
        {"content_type": "text/html"},
    ],
)
def test_failed_capture_is_evidence_but_not_a_rate(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    record = saved(tmp_path, csv_body("EUR", observations()), spec(), **overrides)
    result = m.audit_records(tmp_path, [record])
    assert result["captures"] == [record]
    assert result["series_audits"] == [] and result["failures"][0]["currency"] == "EUR"


def test_duplicate_currency_snapshots_fail_instead_of_silent_choice(tmp_path: Path) -> None:
    a = saved(tmp_path, csv_body("EUR", observations()), spec())
    b = saved(tmp_path, csv_body("EUR", observations("4")), spec())
    result = m.audit_records(tmp_path, [a, b])
    assert result["covered_currencies"] == []


def test_capture_cache_preserves_original_and_failed_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def failure(*args: Any, **kwargs: Any) -> Any:
        calls.append(args)
        raise requests.ConnectionError("Test-only private provider details")

    monkeypatch.setattr(requests, "get", failure)
    first = m.capture_policy_history(tmp_path, spec())
    assert first["transport_error"] == "ConnectionError"
    assert first["http_status"] is None and first["bytes"] == 0
    assert m.capture_policy_history(tmp_path, spec()) == first
    assert len(calls) == 1
    second = m.capture_policy_history(tmp_path, spec(), refresh=True)
    assert first["capture_path"] != second["capture_path"]
    assert Path(first["capture_path"]).exists()
    assert len(calls) == 2


def test_cohort_validates_all_requests_before_writes(tmp_path: Path) -> None:
    target = tmp_path / "not-created"
    for specs in [[], [spec(), spec()], [spec(), spec("INR")]]:
        with pytest.raises(ValueError):
            m.capture_cohort(target, specs)
        assert not target.exists()
