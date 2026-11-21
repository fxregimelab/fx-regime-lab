"""Calendar knowledge, original vintage identities and failure boundaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import requests

from src.private_desk import vintage
from src.private_desk.report import atomic_json

SPEC = {"series": "CPIAUCSL", "vintage": "2023-02-14", "start": "2022-12-01", "end": "2023-01-01"}
RECEIVED = "2026-10-01T00:00:00+00:00"


def body(
    spec: dict[str, str] = SPEC, rows: str = "2022-12-01,298.990\n2023-01-01,300.536"
) -> bytes:
    return (
        "observation_date,"
        + spec["series"]
        + "_"
        + spec["vintage"].replace("-", "")
        + "\n"
        + rows
        + "\n"
    ).encode()


class Response:
    def __init__(self, data: bytes, status: int = 200) -> None:
        self.data, self.status_code = data, status

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_args: Any) -> None:
        pass

    def iter_content(self, size: int) -> Any:
        for offset in range(0, len(self.data), size):
            yield self.data[offset : offset + size]


def capture(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    spec: dict[str, str] = SPEC,
    data: bytes | None = None,
    status: int = 200,
) -> dict[str, Any]:
    def get(url: str, **kwargs: Any) -> Response:
        assert url == vintage.request_url(spec)
        assert kwargs == {"stream": True, "allow_redirects": False, "timeout": (10, 30)}
        return Response(data if data is not None else body(spec), status)

    monkeypatch.setattr(requests, "get", get)
    return vintage.capture_snapshot(root, spec, refresh=True)


def test_actual_schema_preserves_period_and_values_without_release_time() -> None:
    rows = vintage.parse_snapshot(body(), SPEC, RECEIVED)
    assert rows[-1] == {"observation_date": "2023-01-01", "value": 300.536}


@pytest.mark.parametrize(
    "replacement",
    [
        b"observation_date,CPIAUCSL",
        b"observation_date,CPIAUCSL_20240213",
        b"observation_date,DGS2_20230214",
        b"DATE,CPIAUCSL_20230214",
        b"observation_date,CPIAUCSL_20230214,other",
    ],
)
def test_current_wrong_vintage_or_transformed_headers_fail(replacement: bytes) -> None:
    wrong = replacement + b"\n2023-01-01,300.356\n"
    with pytest.raises(ValueError, match="header"):
        vintage.parse_snapshot(wrong, SPEC, RECEIVED)


@pytest.mark.parametrize(
    "rows",
    [
        "2023-01-01,nan",
        "2023-01-01,inf",
        "2023-01-01,0",
        "2023-01-01,-2",
        "2023-01-01,abc",
        "20230101,2",
        "2023-01-02T00:00:00Z,2",
        "2022-11-01,2",
        "2023-02-01,2",
        "2023-01-01,2,3",
        "2023-01-01",
        "2023-01-01,.",
        "2023-01-01,2\n2023-01-01,2",
        "2023-01-01,2\n2022-12-01,3",
        "",
    ],
)
def test_invalid_snapshot_rejects_whole_body(rows: str) -> None:
    with pytest.raises(ValueError):
        vintage.parse_snapshot(body(rows=rows), SPEC, RECEIVED)


def test_missing_values_and_negative_yields_are_not_zero_or_repaired() -> None:
    spec = {**SPEC, "series": "DGS2"}
    rows = vintage.parse_snapshot(body(spec, "2022-12-01,-0.1\n2023-01-01,."), spec, RECEIVED)
    assert [row["value"] for row in rows] == [-0.1, None]


def test_future_vintage_receipt_and_body_bound_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="receipt"):
        vintage.parse_snapshot(body(), SPEC, "2023-02-13T23:59:00+00:00")
    with pytest.raises(ValueError, match="UTC"):
        vintage.parse_snapshot(body(), SPEC, "2026-10-01T00:00:00+05:30")
    monkeypatch.setattr(vintage, "MAX_BODY", 20)
    with pytest.raises(ValueError, match="bound"):
        vintage.parse_snapshot(body(), SPEC, RECEIVED)


def test_calendar_control_excludes_later_vintage_and_does_not_invent_clock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_spec = {**SPEC, "vintage": "2023-02-13"}
    old = capture(tmp_path, monkeypatch, old_spec, body(old_spec, "2022-12-01,298.990"))
    first = capture(tmp_path, monkeypatch)
    revised_spec = {**SPEC, "vintage": "2024-02-13"}
    revised = capture(
        tmp_path,
        monkeypatch,
        revised_spec,
        body(revised_spec, "2022-12-01,298.812\n2023-01-01,300.356"),
    )
    records = [revised, first, old]
    before = vintage.as_of_calendar_audit(tmp_path, records, "CPIAUCSL", "2023-02-13")
    assert before["latest_observation"] == {"observation_date": "2022-12-01", "value": 298.990}
    after = vintage.as_of_calendar_audit(tmp_path, records, "CPIAUCSL", "2023-02-14")
    assert after["latest_observation"]["value"] == 300.536
    assert after["release_timing"] == "UNKNOWN"
    assert after["decision_qualification"] == "UNQUALIFIED"
    earliest = vintage.as_of_calendar_audit(tmp_path, records, "CPIAUCSL", "2023-02-12")
    assert earliest["vintage_date"] is None
    assert earliest["latest_observation"] is None
    audit = vintage.audit_records(tmp_path, records)
    change = audit["series_audits"][0]["revisions"][-1]
    assert change["changed_count"] == 2
    assert change["changes"][-1]["earlier"] == 300.536
    assert change["changes"][-1]["later"] == 300.356


def test_equal_duplicate_and_conflicting_same_vintage_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = capture(tmp_path, monkeypatch)
    equal = capture(tmp_path, monkeypatch)
    audit = vintage.audit_records(tmp_path, [first, equal])
    assert audit["series_audits"][0]["snapshot_summaries"][-1]["equal_duplicates"] == 2
    conflicting = capture(tmp_path, monkeypatch, data=body(rows="2023-01-01,301"))
    audit = vintage.audit_records(tmp_path, [first, conflicting])
    assert audit["series_audits"][0]["status"] == "UNAVAILABLE"
    assert audit["series_audits"][0]["snapshot_summaries"] == []
    assert audit["covered_currencies"] == []
    assert audit["status"] == "UNAVAILABLE"


def test_tampered_cache_receipt_body_and_path_fail_without_refetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = capture(tmp_path, monkeypatch)

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        pytest.fail("Cache corruption caused network access")

    monkeypatch.setattr(requests, "get", forbidden)
    assert vintage.capture_snapshot(tmp_path, SPEC) == record
    with pytest.raises(ValueError, match="outside"):
        vintage.read_receipt(tmp_path / "elsewhere", record["receipt_file"])
    with pytest.raises(ValueError, match="receipt hash"):
        vintage.read_receipt(tmp_path, {**record["receipt_file"], "sha256": "0" * 64})
    Path(record["capture_path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash"):
        vintage.capture_snapshot(tmp_path, SPEC)


def test_url_identity_and_saved_audit_tampering_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = capture(tmp_path, monkeypatch)
    saved = vintage.audit_records(tmp_path, [record])
    atomic_json(tmp_path / "evidence.json", saved)
    assert vintage.load_evidence(tmp_path) == saved
    saved["series_audits"][0]["snapshot_summaries"][0]["last_numeric"]["value"] = 700
    atomic_json(tmp_path / "evidence.json", saved)
    with pytest.raises(ValueError, match="reproduce"):
        vintage.load_evidence(tmp_path)
    reference = record["receipt_file"]
    path = Path(reference["capture_path"])
    receipt = json.loads(path.read_text())
    receipt["url"] = "https://fred.stlouisfed.org/current-values.csv"
    atomic_json(path, receipt)
    reference["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="identity"):
        vintage.read_receipt(tmp_path, reference)


def test_failed_transport_and_truncated_body_remain_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failed = capture(tmp_path, monkeypatch, data=b"source error", status=404)
    assert Path(failed["capture_path"]).read_bytes() == b"source error"
    assert vintage.audit_records(tmp_path, [failed])["covered_currencies"] == []
    monkeypatch.setattr(vintage, "MAX_BODY", 20)
    truncated = capture(tmp_path, monkeypatch, data=b"x" * 25)
    assert truncated["body_complete"] is False
    assert truncated["bytes"] == 20

    def timeout(*_args: Any, **_kwargs: Any) -> Any:
        raise requests.Timeout("test-only sensitive endpoint details")

    monkeypatch.setattr(requests, "get", timeout)
    record = vintage.capture_snapshot(tmp_path, SPEC, refresh=True)
    assert record["transport_error"] == "Timeout"
    assert "sensitive" not in json.dumps(record)


@pytest.mark.parametrize(
    "spec",
    [
        {**SPEC, "series": "GBP_FAKE"},
        {**SPEC, "vintage": "20230214"},
        {**SPEC, "vintage": "2099-01-01"},
        {**SPEC, "end": "2024-01-01"},
        {**SPEC, "start": "1900-01-01"},
        {**SPEC, "units": "pc1"},
    ],
)
def test_invalid_identity_fails_before_network(spec: dict[str, str], tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        vintage.capture_cohort(tmp_path, [spec])


def test_request_batch_bounds_and_preservation_across_cohorts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    capture(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        vintage.capture_cohort(tmp_path, [])
    with pytest.raises(ValueError):
        vintage.capture_cohort(tmp_path, [SPEC] * 2)
    with pytest.raises(ValueError):
        vintage.capture_cohort(tmp_path, [SPEC] * 13)
    first = vintage.capture_cohort(tmp_path, [SPEC])
    next_spec = {**SPEC, "vintage": "2024-02-13"}
    capture(tmp_path, monkeypatch, next_spec)
    second = vintage.capture_cohort(tmp_path, [next_spec])
    assert len(second["captures"]) == 2
    assert first["captures"][0] in second["captures"]
    assert len(list((tmp_path / "cohorts").glob("*.json"))) == 2
