"""Original ALFRED calendar-date snapshots, without intraday/model qualification."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import requests

from src.private_desk.bidask import bounded_path, receipt_clock
from src.private_desk.report import atomic_json

SERIES = {
    "CPIAUCSL": {"currency": "USD", "label": "US consumer price index, original exported level"},
    "DGS2": {"currency": "USD", "label": "US two-year Treasury constant-maturity yield"},
}
MAX_BODY = 2_000_000
LIMITS = [
    "Selected ALFRED snapshots are calendar-date audit evidence, not exact release timestamps.",
    "Graph CSV is a witnessed first-party UI route, not a documented API guarantee.",
    "Historical units/frequency/seasonal metadata and contemporaneous receipt are unqualified.",
    "Source, provider or first-FRED release dates can be reconstructed or backfilled later.",
    "Typical one-business-day ingestion is not a guaranteed availability bound.",
    "Actual values alone do not establish consensus expectations or an economic surprise.",
    "No historical macro feature, current probability or trade qualification is added here.",
]


def canonical_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Require YYYY-MM-DD")
    return parsed


def request_url(spec: dict[str, str]) -> str:
    if set(spec) != {"series", "vintage", "start", "end"} or spec["series"] not in SERIES:
        raise ValueError("Unknown snapshot request")
    vintage, start, end = (canonical_date(spec[key]) for key in ("vintage", "start", "end"))
    if vintage > datetime.now(UTC).date():
        raise ValueError("Future vintage request")
    if not start <= end <= vintage or (end - start).days > 31 * 366:
        raise ValueError("Invalid/beyond-bound observation window")
    return "https://alfred.stlouisfed.org/graph/alfredgraph.csv?" + urlencode(
        {
            "id": spec["series"],
            "vintage_date": spec["vintage"],
            "cosd": spec["start"],
            "coed": spec["end"],
            "transformation": "lin",
        }
    )


def parse_snapshot(body: bytes, spec: dict[str, str], received_at: str) -> list[dict[str, Any]]:
    request_url(spec)
    if len(body) > MAX_BODY:
        raise ValueError("Snapshot body exceeds bound")
    receipt = receipt_clock(received_at).date()
    vintage = canonical_date(spec["vintage"])
    if vintage > receipt:
        raise ValueError("Vintage is after receipt")
    reader = csv.reader(io.StringIO(body.decode("utf-8-sig")))
    expected = ["observation_date", spec["series"] + "_" + spec["vintage"].replace("-", "")]
    if next(reader, []) != expected:
        raise ValueError("Wrong series/vintage/header")
    rows: list[dict[str, Any]] = []
    previous: date | None = None
    start, end = canonical_date(spec["start"]), canonical_date(spec["end"])
    for row in reader:
        if len(row) != 2:
            raise ValueError("Invalid snapshot columns")
        stamp = canonical_date(row[0])
        if not start <= stamp <= end or stamp > vintage or stamp > receipt:
            raise ValueError("Observation outside request/vintage/receipt boundary")
        if previous is not None and stamp <= previous:
            raise ValueError("Duplicate/non-increasing observation")
        try:
            value = None if row[1] in ("", ".") else float(row[1])
        except ValueError:
            raise ValueError("Invalid snapshot value") from None
        if value is not None and (
            not math.isfinite(value) or (spec["series"] == "CPIAUCSL" and value <= 0)
        ):
            raise ValueError("Invalid non-finite/index value")
        rows.append({"observation_date": stamp.isoformat(), "value": value})
        previous = stamp
    if not rows or not any(row["value"] is not None for row in rows):
        raise ValueError("No numeric snapshot observations")
    return rows


def read_receipt(root: Path, reference: dict[str, Any]) -> dict[str, Any]:
    raw = bounded_path(root, reference["capture_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("Snapshot receipt hash mismatch")
    record: dict[str, Any] = json.loads(raw)
    if record["url"] != request_url(record["request"]):
        raise ValueError("Snapshot request identity mismatch")
    receipt_clock(record["received_at"])
    body = bounded_path(root, record["capture_path"]).read_bytes()
    if len(body) != record["bytes"] or hashlib.sha256(body).hexdigest() != record["sha256"]:
        raise ValueError("Snapshot body hash/length mismatch")
    return {**record, "receipt_file": reference}


def capture_snapshot(root: Path, spec: dict[str, str], *, refresh: bool = False) -> dict[str, Any]:
    url = request_url(spec)
    if canonical_date(spec["vintage"]) > datetime.now(UTC).date():
        raise ValueError("Future vintage request")
    root.mkdir(parents=True, exist_ok=True)
    identity = "-".join(spec[key] for key in ("series", "vintage", "start", "end"))
    index = root / (identity + ".json")
    if index.exists() and not refresh:
        record = read_receipt(root, json.loads(index.read_text(encoding="utf-8")))
        if record["request"] != spec:
            raise ValueError("Snapshot cache request mismatch")
        return record
    body = bytearray()
    status: int | None = None
    complete = True
    error: str | None = None
    try:
        with requests.get(url, stream=True, allow_redirects=False, timeout=(10, 30)) as response:
            status = response.status_code
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
        "http_status": status,
        "received_at": datetime.now(UTC).isoformat(),
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
    """Recompute all audits from original bodies, preserving failed snapshots."""
    grouped: dict[str, dict[str, Any]] = {}
    panels: dict[str, dict[str, dict[str, Any]]] = {}
    receipts: list[dict[str, Any]] = []
    for saved in records:
        record = read_receipt(root, saved["receipt_file"])
        if record != saved:
            raise ValueError("Saved snapshot receipt mismatch")
        receipts.append(record)
        spec = record["request"]
        series, vintage = spec["series"], spec["vintage"]
        item = grouped.setdefault(
            series,
            {
                "series": series,
                **SERIES[series],
                "status": "CALENDAR_DATE_VINTAGE_AUDIT",
                "snapshot_summaries": [],
                "failures": [],
                "revisions": [],
            },
        )
        if record["http_status"] != 200 or not record["body_complete"]:
            item["failures"].append(vintage + ": HTTP/transport unavailable")
            continue
        try:
            rows = parse_snapshot(
                Path(record["capture_path"]).read_bytes(), spec, record["received_at"]
            )
        except (ValueError, OSError, UnicodeError, csv.Error):
            item["failures"].append(vintage + ": snapshot rejected")
            continue
        panel = panels.setdefault(series, {}).setdefault(vintage, {})
        equal = 0
        for row in rows:
            stamp = row["observation_date"]
            if stamp in panel:
                if panel[stamp] != row:
                    item["failures"].append(vintage + ": conflicting same-vintage observation")
                else:
                    equal += 1
            else:
                panel[stamp] = row
        item["snapshot_summaries"].append(
            {
                "vintage_date": vintage,
                "requested_start": spec["start"],
                "requested_end": spec["end"],
                "rows": len(rows),
                "numeric_rows": sum(row["value"] is not None for row in rows),
                "missing_rows": sum(row["value"] is None for row in rows),
                "equal_duplicates": equal,
                "first": rows[0]["observation_date"],
                "last": rows[-1]["observation_date"],
                "last_numeric": next(row for row in reversed(rows) if row["value"] is not None),
            }
        )
    for series, item in grouped.items():
        if item["failures"]:
            item["status"] = "UNAVAILABLE"
            item["snapshot_summaries"] = []
            continue
        previous: dict[str, Any] | None = None
        previous_date: str | None = None
        for vintage, panel in sorted(panels.get(series, {}).items()):
            if previous is not None:
                changes = [
                    {
                        "observation_date": stamp,
                        "earlier": previous[stamp]["value"],
                        "later": panel[stamp]["value"],
                    }
                    for stamp in sorted(panel.keys() & previous.keys())
                    if panel[stamp] != previous[stamp]
                ]
                item["revisions"].append(
                    {
                        "earlier_vintage": previous_date,
                        "later_vintage": vintage,
                        "changed_count": len(changes),
                        "changes": changes,
                    }
                )
            previous, previous_date = panel, vintage
    covered = sorted(
        {item["currency"] for item in grouped.values() if item["status"] != "UNAVAILABLE"}
    )
    status = (
        "UNAVAILABLE"
        if not covered
        else "PARTIAL_CALENDAR_DATE_SOURCE_AUDIT"
        if any(item["failures"] for item in grouped.values())
        else "CALENDAR_DATE_SOURCE_AUDIT"
    )
    return {
        "schema_version": "private-vintage-v1",
        "status": status,
        "release_timing": "UNKNOWN",
        "historical_model_qualification": "UNQUALIFIED",
        "metadata_qualification": "UNQUALIFIED",
        "covered_currencies": covered,
        "series_audits": list(grouped.values()),
        "captures": receipts,
        "limitations": LIMITS,
    }


def as_of_calendar_audit(
    root: Path, records: list[dict[str, Any]], series: str, as_of_date: str
) -> dict[str, Any]:
    """Inspect calendar knowledge only; this does not establish decision-hour availability."""
    cutoff = canonical_date(as_of_date)
    if series not in SERIES:
        raise ValueError("Unknown calendar-audit series")
    audit = audit_records(root, records)
    item: dict[str, Any] = next(
        (row for row in audit["series_audits"] if row["series"] == series), {}
    )
    eligible = [
        row
        for row in item.get("snapshot_summaries", [])
        if canonical_date(row["vintage_date"]) <= cutoff
    ]
    newest = max((row["vintage_date"] for row in eligible), default=None)
    rows = [row["last_numeric"] for row in eligible if row["vintage_date"] == newest]
    return {
        "series": series,
        "as_of_date": as_of_date,
        "vintage_date": newest,
        "latest_observation": max(rows, key=lambda row: row["observation_date"]) if rows else None,
        "release_timing": "UNKNOWN",
        "decision_qualification": "UNQUALIFIED",
    }


def load_evidence(root: Path) -> dict[str, Any] | None:
    path = root / "evidence.json"
    if not path.exists():
        return None
    saved: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    recomputed = audit_records(root, saved["captures"])
    if recomputed != saved:
        raise ValueError("Saved vintage audit does not reproduce")
    return recomputed


def capture_cohort(
    root: Path, specs: list[dict[str, str]], *, refresh: bool = False
) -> dict[str, Any]:
    if not 1 <= len(specs) <= 12:
        raise ValueError("Name one to twelve snapshot requests")
    urls = [request_url(spec) for spec in specs]
    if len(set(urls)) != len(urls):
        raise ValueError("Duplicate snapshot requests")
    existing = load_evidence(root)
    records = {item["url"]: item for item in existing["captures"]} if existing else {}
    for spec in specs:
        record = capture_snapshot(root, spec, refresh=refresh)
        records[record["url"]] = record
    result = audit_records(root, list(records.values()))
    atomic_json(root / "cohorts" / (uuid4().hex + ".json"), result)
    atomic_json(root / "evidence.json", result)
    return result
