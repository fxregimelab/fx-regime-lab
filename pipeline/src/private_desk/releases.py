"""First-party release statements, distinct from actual historical information arrival."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, date, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from src.private_desk.bidask import bounded_path, receipt_clock
from src.private_desk.report import atomic_json
from src.private_desk.vintage import canonical_date

MAX_BODY = 2_000_000
MONTHS = dict(
    zip(
        (
            "January February March April May June July August September October November December"
        ).split(),
        range(1, 13),
        strict=True,
    )
)
LIMITS = [
    "A source-stated release clock does not prove actual transmission or historical receipt.",
    "Current archive receipt is separate from provider availability at the historical decision.",
    "An announced federal-funds target range is not an effective rate or a two-year yield spread.",
    "Effective implementation dates require separate implementation evidence.",
    "CPI changes retain period and seasonal adjustment; no ALFRED index identity is assumed.",
    "Consensus expectations and economic surprises are unavailable.",
    "Selected USD releases do not establish other currency legs or complete historical coverage.",
    "No macro feature, current probability or strategy qualification is added by this audit.",
]


def archive_url(spec: dict[str, str]) -> str:
    if set(spec) != {"source", "date"} or spec["source"] not in ("FOMC", "CPI"):
        raise ValueError("Unknown release request")
    stamp = canonical_date(spec["date"])
    if stamp > datetime.now(UTC).date() or stamp.year < 1994:
        raise ValueError("Future or unsupported release date")
    if spec["source"] == "FOMC":
        return (
            "https://www.federalreserve.gov/newsevents/pressreleases/monetary"
            + stamp.strftime("%Y%m%d")
            + "a.htm"
        )
    return "https://www.bls.gov/news.release/archives/cpi_" + stamp.strftime("%m%d%Y") + ".htm"


def english_date(text: str) -> date:
    match = re.fullmatch(r"([A-Za-z]+) (\d{1,2}), (\d{4})", text)
    if not match or match[1] not in MONTHS:
        raise ValueError("Unrecognized release date")
    return date(int(match[3]), MONTHS[match[1]], int(match[2]))


def release_clock(day: date, hour: int, minute: int, meridiem: str, label: str) -> datetime:
    if not 1 <= hour <= 12 or not 0 <= minute < 60 or meridiem not in ("a.m.", "p.m."):
        raise ValueError("Invalid release clock")
    local = datetime(
        day.year,
        day.month,
        day.day,
        hour % 12 + (12 if meridiem == "p.m." else 0),
        minute,
        tzinfo=ZoneInfo("America/New_York"),
    )
    if local.utcoffset() != local.replace(fold=1).utcoffset():
        raise ValueError("Ambiguous/nonexistent local release clock")
    if local.astimezone(UTC).astimezone(local.tzinfo).replace(tzinfo=None) != local.replace(
        tzinfo=None
    ):
        raise ValueError("Nonexistent local release clock")
    if label not in ("ET", "EST", "EDT") or (label != "ET" and local.tzname() != label):
        raise ValueError("Clock label conflicts with date/DST")
    return local


def rate_bound(token: str) -> float:
    if re.fullmatch(r"\d+-\d+/\d+", token):
        whole, fraction = token.split("-", 1)
        numerator, denominator = fraction.split("/")
        if not 0 < int(numerator) < int(denominator):
            raise ValueError("Invalid mixed fraction")
        result = float(int(whole) + Fraction(int(numerator), int(denominator)))
    elif re.fullmatch(r"\d+(?:\.\d+)?", token):
        result = float(token)
    else:
        raise ValueError("Invalid target-bound format")
    if not math.isfinite(result) or not 0 <= result <= 30:
        raise ValueError("Target bound outside supported range")
    return result


def parse_release(body: bytes, spec: dict[str, str], received_at: str) -> dict[str, Any]:
    archive_url(spec)
    if not body or len(body) > MAX_BODY:
        raise ValueError("Invalid release body size")
    soup = BeautifulSoup(body.decode("utf-8-sig"), "html.parser")
    requested = canonical_date(spec["date"])
    if spec["source"] == "FOMC":
        articles = soup.select("#article")
        if len(articles) != 1:
            raise ValueError("Missing/ambiguous statement article")
        article = articles[0]
        titles, days, clocks = (
            article.select(sel) for sel in (".title", ".article__time", ".releaseTime")
        )
        if (
            len(titles) != 1
            or titles[0].get_text(" ", strip=True) != "Federal Reserve issues FOMC statement"
        ):
            raise ValueError("Not an FOMC statement")
        if len(days) != 1 or english_date(days[0].get_text(" ", strip=True)) != requested:
            raise ValueError("Statement date mismatch")
        if len(clocks) != 1:
            raise ValueError("Ambiguous statement clock")
        clock_matches = re.findall(
            r"For release at (\d{1,2}):(\d{2}) (a\.m\.|p\.m\.) (EST|EDT)\b",
            clocks[0].get_text(" ", strip=True),
        )
        text = " ".join(article.get_text(" ", strip=True).split())
        ranges = list(
            re.finditer(
                r"target range for the federal funds rate "
                r"(?:to|at) ([\d./-]+) to ([\d./-]+) percent\b",
                text,
            )
        )
        if len(ranges) != 1:
            raise ValueError("Missing/ambiguous target range")
        lower, upper = (rate_bound(value) for value in ranges[0].groups())
        if lower >= upper:
            raise ValueError("Unordered target range")
        measures = [
            {
                "name": "Announced federal-funds target lower bound",
                "value": lower,
                "unit": "percent",
            },
            {
                "name": "Announced federal-funds target upper bound",
                "value": upper,
                "unit": "percent",
            },
        ]
        observation_period = None
        original_measure = ranges[0][0]
        document_id = "monetary" + requested.strftime("%Y%m%d") + "a"
    else:
        blocks = soup.find_all("pre")
        if len(blocks) != 1:
            raise ValueError("Missing/ambiguous CPI archive")
        text = " ".join(blocks[0].get_text(" ", strip=True).split())
        header = re.findall(
            r"Transmission of material in this release is embargoed until "
            r"(\d{1,2}):(\d{2}) (a\.m\.|p\.m\.) \(ET\) "
            r"([A-Za-z]+), ([A-Za-z]+ \d{1,2}, \d{4})",
            text,
        )
        if len(header) != 1 or english_date(header[0][4]) != requested:
            raise ValueError("CPI release-header date mismatch")
        weekdays = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
        if header[0][3] != weekdays[requested.weekday()]:
            raise ValueError("CPI header weekday mismatch")
        release_ids = re.findall(r"\bUSDL-(\d{2})-(\d{4})\b", text)
        if len(release_ids) != 1 or int(release_ids[0][0]) != requested.year % 100:
            raise ValueError("CPI release ID missing/mismatched")
        document_id = "USDL-" + "-".join(release_ids[0])
        clock_matches = [(*header[0][:3], "ET")]
        periods = re.findall(r"CONSUMER PRICE INDEX[\s-]+([A-Z]+) (\d{4})\b", text)
        if len(periods) != 1 or periods[0][0].title() not in MONTHS:
            raise ValueError("Missing/ambiguous CPI observation month")
        month, year = periods[0][0].title(), int(periods[0][1])
        observation_period = date(year, MONTHS[month], 1).isoformat()
        if canonical_date(observation_period) >= requested.replace(day=1):
            raise ValueError("CPI observation must precede release month")
        change = re.findall(
            r"The Consumer Price Index for All Urban Consumers \(CPI-U\) "
            r"(increased|rose|decreased|fell) (\d+(?:\.\d+)?) percent in "
            + month
            + r" on a seasonally adjusted basis",
            text,
        )
        annual = re.findall(
            r"Over the last 12 months, the all items index "
            r"(increased|rose|decreased|fell) (\d+(?:\.\d+)?) percent before seasonal adjustment",
            text,
        )
        if len(change) != 1 or len(annual) != 1:
            raise ValueError("Missing/ambiguous headline CPI changes")
        values = [
            float(value) * (-1 if direction in ("decreased", "fell") else 1)
            for direction, value in (change[0], annual[0])
        ]
        if not all(math.isfinite(value) and abs(value) <= 100 for value in values):
            raise ValueError("Invalid CPI changes")
        measures = [
            {
                "name": "CPI-U all items month-on-month",
                "value": values[0],
                "unit": "percent",
                "adjustment": "seasonally adjusted",
                "period": "preceding month",
            },
            {
                "name": "CPI-U all items year-on-year",
                "value": values[1],
                "unit": "percent",
                "adjustment": "not seasonally adjusted",
                "period": "12 months ending observation month",
            },
        ]
        original_measure = "Headline CPI-U percentage changes for " + month + " " + str(year)
    if len(clock_matches) != 1:
        raise ValueError("Missing/ambiguous release clock")
    hour, minute, meridiem, label = clock_matches[0]
    local = release_clock(requested, int(hour), int(minute), meridiem, label)
    release_at = local.astimezone(UTC)
    if release_at > receipt_clock(received_at):
        raise ValueError("Source-stated release is after receipt")
    return {
        "source": spec["source"],
        "source_document_id": document_id,
        "currency": "USD",
        "release_date": spec["date"],
        "source_clock": f"{hour}:{minute} {meridiem} {label}",
        "source_timezone": "America/New_York",
        "source_stated_release_at": release_at.isoformat(),
        "observation_period": observation_period,
        "measures": measures,
        "original_measure": original_measure,
        "timing_status": "SOURCE_STATED_RELEASE_CLOCK",
        "actual_transmission_at": None,
        "historical_receipt_at": None,
        "provider_available_at": None,
        "archival_revision_status": "UNKNOWN",
        "effective_policy_date": None,
        "consensus": None,
        "surprise": None,
        "decision_qualification": "UNQUALIFIED",
    }


def read_receipt(root: Path, reference: dict[str, Any]) -> dict[str, Any]:
    raw = bounded_path(root, reference["capture_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("Release receipt hash mismatch")
    record: dict[str, Any] = json.loads(raw)
    if record["url"] != archive_url(record["request"]):
        raise ValueError("Release request identity mismatch")
    receipt_clock(record["received_at"])
    body = bounded_path(root, record["capture_path"]).read_bytes()
    if len(body) != record["bytes"] or hashlib.sha256(body).hexdigest() != record["sha256"]:
        raise ValueError("Release body hash/length mismatch")
    return {**record, "receipt_file": reference}


def capture_release(root: Path, spec: dict[str, str], *, refresh: bool = False) -> dict[str, Any]:
    url = archive_url(spec)
    root.mkdir(parents=True, exist_ok=True)
    index = root / (spec["source"] + "-" + spec["date"] + ".json")
    if index.exists() and not refresh:
        record = read_receipt(root, json.loads(index.read_text(encoding="utf-8")))
        if record["request"] != spec:
            raise ValueError("Release cache request mismatch")
        return record
    body = bytearray()
    status: int | None = None
    content_type = ""
    complete, error = True, None
    try:
        with requests.get(url, stream=True, allow_redirects=False, timeout=(10, 30)) as response:
            status = response.status_code
            content_type = response.headers.get("content-type", "")
            for chunk in response.iter_content(64_000):
                remaining = MAX_BODY - len(body)
                body.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    complete, error = False, "Response exceeds bound"
                    break
    except requests.RequestException as exc:
        complete, error = False, type(exc).__name__
    token = uuid4().hex
    path = root / (token + ".bin")
    with path.open("xb") as handle:
        handle.write(body)
    record = {
        "request": spec,
        "url": url,
        "received_at": datetime.now(UTC).isoformat(),
        "http_status": status,
        "content_type": content_type,
        "body_complete": complete,
        "transport_error": error,
        "capture_path": str(path.resolve()),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    receipt = root / (token + ".receipt.json")
    with receipt.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, allow_nan=False)
    reference = {
        "capture_path": str(receipt.resolve()),
        "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
    }
    atomic_json(index, reference)
    return {**record, "receipt_file": reference}


def audit_records(root: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    events: dict[tuple[str, str], dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    conflicts: set[str] = set()
    duplicates = 0
    for saved in records:
        record = read_receipt(root, saved["receipt_file"])
        if record != saved:
            raise ValueError("Saved release receipt mismatch")
        spec = record["request"]
        reason = None
        if record["http_status"] != 200 or not record["body_complete"]:
            reason = "HTTP/transport unavailable"
        elif record.get("content_type", "").split(";", 1)[0].strip().lower() != "text/html":
            reason = "Unexpected release media type"
        else:
            try:
                event = parse_release(
                    Path(record["capture_path"]).read_bytes(), spec, record["received_at"]
                )
            except (ValueError, OSError, UnicodeError, ZeroDivisionError):
                reason = "Release rejected"
            else:
                key = spec["source"], spec["date"]
                if key in events:
                    if events[key] != event:
                        conflicts.add(spec["source"])
                        reason = "Conflicting same-date release"
                    else:
                        duplicates += 1
                else:
                    events[key] = event
        if reason:
            failures.append(
                {
                    "source": spec["source"],
                    "release_date": spec["date"],
                    "reason": reason,
                    "http_status": record["http_status"],
                }
            )
    accepted = sorted(
        (event for event in events.values() if event["source"] not in conflicts),
        key=lambda event: (event["source_stated_release_at"], event["source"]),
    )
    return {
        "schema_version": "private-release-v1",
        "status": "PARTIAL_SOURCE_CLOCK_AUDIT"
        if accepted and failures
        else "SOURCE_CLOCK_AUDIT"
        if accepted
        else "UNAVAILABLE",
        "covered_currencies": ["USD"] if accepted else [],
        "events": accepted,
        "failures": failures,
        "conflicting_sources": sorted(conflicts),
        "equal_duplicates": duplicates,
        "historical_model_qualification": "UNQUALIFIED",
        "provider_availability": "UNKNOWN",
        "captures": records,
        "limitations": LIMITS,
    }


def as_of_release_audit(evidence: dict[str, Any], decision_at: str) -> list[dict[str, Any]]:
    cutoff = datetime.fromisoformat(decision_at)
    if cutoff.utcoffset() is None:
        raise ValueError("Decision timestamp requires an explicit offset")
    cutoff = cutoff.astimezone(UTC)
    return [
        event
        for event in evidence["events"]
        if receipt_clock(event["source_stated_release_at"]) < cutoff
    ]


def load_evidence(root: Path) -> dict[str, Any] | None:
    path = root / "evidence.json"
    if not path.exists():
        return None
    saved: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    recomputed = audit_records(root, saved["captures"])
    if recomputed != saved:
        raise ValueError("Saved release audit does not reproduce")
    return recomputed


def capture_cohort(
    root: Path, specs: list[dict[str, str]], *, refresh: bool = False
) -> dict[str, Any]:
    if not 1 <= len(specs) <= 12:
        raise ValueError("Name one to twelve release requests")
    urls = [archive_url(spec) for spec in specs]
    if len(set(urls)) != len(urls):
        raise ValueError("Duplicate release requests")
    existing = load_evidence(root)
    records = {item["url"]: item for item in existing["captures"]} if existing else {}
    for spec in specs:
        record = capture_release(root, spec, refresh=refresh)
        records[record["url"]] = record
    result = audit_records(root, list(records.values()))
    atomic_json(root / "cohorts" / (uuid4().hex + ".json"), result)
    atomic_json(root / "evidence.json", result)
    return result
