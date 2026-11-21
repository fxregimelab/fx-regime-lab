"""Adverse chronology, value-identity and original-capture controls; no live network."""

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import requests

from src.private_desk import releases as m

RECEIPT = "2026-10-01T12:00:00+00:00"
FEB = {"source": "FOMC", "date": "2023-02-01"}
CPI = {"source": "CPI", "date": "2023-02-14"}


def statement(
    *, day: str = "February 01, 2023", zone: str = "EST", lower: str = "4-1/2", upper: str = "4-3/4"
) -> bytes:
    # Synthetic minimal source schema, not an actual archived capture.
    return (
        '<div id="article"><p class="article__time">' + day + "</p>"
        '<h3 class="title">Federal Reserve issues FOMC statement</h3>'
        '<p class="releaseTime">For release at 2:00 p.m. ' + zone + "</p>"
        "<p>The Committee decided to raise the target range for the federal funds rate to "
        + lower
        + " to "
        + upper
        + " percent.</p></div>"
    ).encode()


def cpi(
    *,
    weekday: str = "Tuesday",
    day: str = "February 14, 2023",
    month: str = "January",
    year: str = "2023",
    verb: str = "increased",
) -> bytes:
    return (
        "<pre>Transmission of material in this release is embargoed until "
        "8:30 a.m. (ET) " + weekday + ", " + day + " USDL-23-0277 "
        "CONSUMER PRICE INDEX - " + month.upper() + " " + year + " "
        "The Consumer Price Index for All Urban Consumers (CPI-U) "
        + verb
        + " 0.5 percent in "
        + month
        + " on a seasonally adjusted basis. "
        "Over the last 12 months, the all items index increased 6.4 percent "
        "before seasonal adjustment. The next release is scheduled for March 14, 2023, "
        "at 8:30 a.m. (ET).</pre>"
    ).encode()


def saved(
    root: Path, body: bytes, spec: dict[str, str], *, status: int = 200, media: str = "text/html"
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    token = str(len(list(root.glob("*.bin"))))
    p = root / (token + ".bin")
    p.write_bytes(body)
    record = {
        "request": spec,
        "url": m.archive_url(spec),
        "received_at": RECEIPT,
        "http_status": status,
        "body_complete": True,
        "transport_error": None,
        "content_type": media,
        "capture_path": str(p.resolve()),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    receipt = root / (token + ".receipt.json")
    receipt.write_text(json.dumps(record), encoding="utf-8")
    return {
        **record,
        "receipt_file": {
            "capture_path": str(receipt.resolve()),
            "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        },
    }


@pytest.mark.parametrize(
    "spec",
    [
        {"source": "FOMC", "date": "20230201"},
        {"source": "FOMC", "date": "2023-02-30"},
        {"source": "FOMC", "date": "2999-01-01"},
        {"source": "FOMC", "date": "1990-01-01"},
        {"source": "CURRENT", "date": "2023-02-01"},
        {**FEB, "url": "https://example.com"},
    ],
)
def test_named_request_boundary(spec: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        m.archive_url(spec)


@pytest.mark.parametrize(
    ("token", "expected"), [("4-1/2", 4.5), ("4-3/4", 4.75), ("5", 5.0), ("5.25", 5.25), ("0", 0)]
)
def test_target_bounds_are_not_decimal_fraction_shortcuts(token: str, expected: float) -> None:
    assert m.rate_bound(token) == expected


@pytest.mark.parametrize("token", ["4-3/0", "4-5/4", "-1", "NaN", "inf", "1e2", "31", "4.3/4"])
def test_bad_target_bound_rejected(token: str) -> None:
    with pytest.raises(ValueError):
        m.rate_bound(token)


def test_fomc_clock_value_identity_and_unknown_arrival() -> None:
    event = m.parse_release(statement(), FEB, RECEIPT)
    assert event["source_stated_release_at"] == "2023-02-01T19:00:00+00:00"
    assert [row["value"] for row in event["measures"]] == [4.5, 4.75]
    assert event["source_clock"] == "2:00 p.m. EST"
    assert event["source_document_id"] == "monetary20230201a"
    assert event["decision_qualification"] == "UNQUALIFIED"
    for field in [
        "actual_transmission_at",
        "historical_receipt_at",
        "provider_available_at",
        "effective_policy_date",
        "consensus",
        "surprise",
    ]:
        assert event[field] is None


def test_daylight_saving_clock_does_not_shift_value() -> None:
    spec = {"source": "FOMC", "date": "2023-03-22"}
    event = m.parse_release(
        statement(day="March 22, 2023", zone="EDT", lower="4-3/4", upper="5"), spec, RECEIPT
    )
    assert event["source_stated_release_at"] == "2023-03-22T18:00:00+00:00"
    assert [row["value"] for row in event["measures"]] == [4.75, 5.0]
    with pytest.raises(ValueError, match="DST"):
        m.parse_release(statement(day="March 22, 2023", zone="EST"), spec, RECEIPT)


@pytest.mark.parametrize(
    "body",
    [
        statement().replace(b"FOMC statement", b"implementation note"),
        statement().replace(b"February 01", b"February 02"),
        statement().replace(b"2:00 p.m. EST", b"2:00 p.m."),
        statement().replace(b"2:00", b"13:00"),
        statement().replace(b"2:00", b"2:99"),
        statement(lower="5", upper="4"),
        statement(lower="5", upper="5"),
        statement() + statement(),
        statement().replace(
            b"</p></div>", b" target range for the federal funds rate at 5 to 6 percent.</p></div>"
        ),
        b"<html>Access Denied</html>",
    ],
)
def test_wrong_ambiguous_source_and_clock_rejected(body: bytes) -> None:
    with pytest.raises(ValueError):
        m.parse_release(body, FEB, RECEIPT)


@pytest.mark.parametrize(("day", "hour"), [(date(2023, 3, 12), 2), (date(2023, 11, 5), 1)])
def test_dst_gap_and_fold_fail_without_inventing_an_instant(day: date, hour: int) -> None:
    with pytest.raises(ValueError):
        m.release_clock(day, hour, 30, "a.m.", "ET")


def test_source_clock_after_receipt_is_not_released_evidence() -> None:
    with pytest.raises(ValueError, match="after receipt"):
        m.parse_release(statement(), FEB, "2023-02-01T18:59:59+00:00")


def test_cpi_period_adjustment_and_own_header_not_future_schedule() -> None:
    event = m.parse_release(cpi(), CPI, RECEIPT)
    assert event["source_stated_release_at"] == "2023-02-14T13:30:00+00:00"
    assert event["observation_period"] == "2023-01-01"
    assert event["source_document_id"] == "USDL-23-0277"
    assert [row["value"] for row in event["measures"]] == [0.5, 6.4]
    assert [row["adjustment"] for row in event["measures"]] == [
        "seasonally adjusted",
        "not seasonally adjusted",
    ]
    assert not any("index level" in row["name"] for row in event["measures"])
    assert m.parse_release(cpi(verb="fell"), CPI, RECEIPT)["measures"][0]["value"] == -0.5


def test_cpi_summer_et_is_resolved_by_release_date() -> None:
    event = m.parse_release(
        cpi(weekday="Wednesday", day="April 12, 2023", month="March"),
        {"source": "CPI", "date": "2023-04-12"},
        RECEIPT,
    )
    assert event["source_stated_release_at"] == "2023-04-12T12:30:00+00:00"


@pytest.mark.parametrize(
    "body",
    [
        cpi(weekday="Monday"),
        cpi(day="February 15, 2023"),
        cpi(month="February"),
        cpi(year="2024"),
        cpi().replace(b"USDL-23-0277", b"USDL-24-0277"),
        cpi().replace(b"USDL-23-0277", b""),
        cpi().replace(b"(CPI-U)", b"(CPI-W)"),
        cpi().replace(b"on a seasonally adjusted basis", b"prior to seasonal adjustment"),
        cpi().replace(b"before seasonal adjustment", b"after seasonal adjustment"),
        cpi() + cpi(),
        cpi().replace(b"0.5 percent", b"NaN percent"),
    ],
)
def test_cpi_wrong_month_measure_identity_and_revision_not_accepted(body: bytes) -> None:
    with pytest.raises(ValueError):
        m.parse_release(body, CPI, RECEIPT)


def test_calendar_date_and_exact_release_instant_do_not_enter_cutoff(tmp_path: Path) -> None:
    audit = m.audit_records(tmp_path, [saved(tmp_path, statement(), FEB)])
    with pytest.raises(ValueError, match="offset"):
        m.as_of_release_audit(audit, "2023-02-01")
    assert m.as_of_release_audit(audit, "2023-02-01T18:59:59Z") == []
    assert m.as_of_release_audit(audit, "2023-02-01T19:00:00Z") == []
    after = m.as_of_release_audit(audit, "2023-02-01T14:00:01-05:00")
    assert len(after) == 1
    assert after[0]["provider_available_at"] is None
    assert after[0]["decision_qualification"] == "UNQUALIFIED"


def test_equal_duplicate_counts_once_but_conflict_rejects_whole_source(tmp_path: Path) -> None:
    a, b = (saved(tmp_path, statement(), FEB) for _ in range(2))
    audit = m.audit_records(tmp_path, [a, b])
    assert len(audit["events"]) == 1 and audit["equal_duplicates"] == 1
    c = saved(tmp_path, statement(upper="5"), FEB)
    later = saved(
        tmp_path,
        statement(day="March 22, 2023", zone="EDT"),
        {"source": "FOMC", "date": "2023-03-22"},
    )
    audit = m.audit_records(tmp_path, [a, c, later])
    assert audit["events"] == [] and audit["conflicting_sources"] == ["FOMC"]
    assert audit["status"] == "UNAVAILABLE"


def test_blocked_and_wrong_media_bodies_remain_visible(tmp_path: Path) -> None:
    good = saved(tmp_path, statement(), FEB)
    blocked = saved(tmp_path, b"Access denied", CPI, status=403)
    media = saved(tmp_path, cpi(), CPI, media="application/json")
    audit = m.audit_records(tmp_path, [good, blocked, media])
    assert audit["status"] == "PARTIAL_SOURCE_CLOCK_AUDIT"
    assert len(audit["events"]) == 1 and len(audit["failures"]) == 2
    assert audit["failures"][0]["http_status"] == 403


@pytest.mark.parametrize("kind", ["body", "receipt", "path", "request", "statistics"])
def test_tampering_fails_closed(tmp_path: Path, kind: str) -> None:
    record = saved(tmp_path, statement(), FEB)
    audit = m.audit_records(tmp_path, [record])
    evidence = tmp_path / "evidence.json"
    if kind == "body":
        Path(record["capture_path"]).write_bytes(b"changed")
    elif kind == "receipt":
        Path(record["receipt_file"]["capture_path"]).write_text("{}", encoding="utf-8")
    elif kind in ("path", "request"):
        receipt = Path(record["receipt_file"]["capture_path"])
        raw = json.loads(receipt.read_text(encoding="utf-8"))
        if kind == "path":
            raw["capture_path"] = str((tmp_path / ".." / "outside").resolve())
        else:
            raw["url"] = "https://example.com"
        receipt.write_text(json.dumps(raw), encoding="utf-8")
        audit["captures"][0]["receipt_file"]["sha256"] = hashlib.sha256(
            receipt.read_bytes()
        ).hexdigest()
    else:
        audit["events"][0]["measures"][0]["value"] = 9
    evidence.write_text(json.dumps(audit), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_evidence(tmp_path)


class Response:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body = body
        self.status_code = status
        self.headers = {"content-type": "text/html; charset=UTF-8"}

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def iter_content(self, _size: int) -> list[bytes]:
        return [self.body]


def test_named_capture_cache_replay_and_prior_cohort_preservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def get(url: str, **kwargs: Any) -> Response:
        assert kwargs == {"stream": True, "allow_redirects": False, "timeout": (10, 30)}
        calls.append(url)
        return Response(statement()) if "federalreserve" in url else Response(b"Access denied", 403)

    monkeypatch.setattr(requests, "get", get)
    one = m.capture_cohort(tmp_path, [FEB])
    assert one["status"] == "SOURCE_CLOCK_AUDIT"
    two = m.capture_cohort(tmp_path, [CPI])
    assert len(two["captures"]) == 2 and two["status"] == "PARTIAL_SOURCE_CLOCK_AUDIT"
    assert m.load_evidence(tmp_path) == two
    m.capture_cohort(tmp_path, [FEB, CPI])
    assert len(calls) == 2
    assert len(list((tmp_path / "cohorts").glob("*.json"))) == 3
    Path(two["captures"][0]["capture_path"]).write_bytes(b"corruption")
    with pytest.raises(ValueError):
        m.capture_cohort(tmp_path, [FEB])
    assert len(calls) == 2


@pytest.mark.parametrize("kind", ["timeout", "oversize"])
def test_failed_original_transport_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    def get(_url: str, **_kwargs: Any) -> Response:
        if kind == "timeout":
            raise requests.Timeout("Test-only secret-bearing provider text")
        return Response(b"x" * 17)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(m, "MAX_BODY", 16)
    record = m.capture_release(tmp_path, FEB)
    assert record["body_complete"] is False
    assert record["bytes"] == (0 if kind == "timeout" else 16)
    assert "secret" not in json.dumps(record)
    assert m.audit_records(tmp_path, [record])["status"] == "UNAVAILABLE"


@pytest.mark.parametrize("specs", [[], [FEB] * 13, [FEB, FEB]])
def test_batch_bound_is_checked_before_any_fetch(
    tmp_path: Path, specs: list[dict[str, str]]
) -> None:
    with pytest.raises(ValueError):
        m.capture_cohort(tmp_path, specs)
