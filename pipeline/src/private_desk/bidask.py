"""Bounded, original FXCM archive evidence; no executable-fill qualification."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests

from src.private_desk.report import PAIRS, atomic_json

HEADER = (
    "DateTime",
    "BidOpen",
    "BidHigh",
    "BidLow",
    "BidClose",
    "AskOpen",
    "AskHigh",
    "AskLow",
    "AskClose",
)
MAX_COMPRESSED = 2_000_000
MAX_EXPANDED = 8_000_000
LIMITS = [
    "Indicative FXCM Active Trader quotes; not the owner's broker fills.",
    "UTC is documented; candle start/end role and boundary tick allocation are unknown.",
    "Side OHLC differences are descriptive, not synchronized tick spreads or realised costs.",
    "Missing minutes use an unverified New York market-clock proxy; no holiday inference.",
    "Historical publication/receipt, corrections, slippage and financing remain unverified.",
    "This cohort does not change backtests, candidate eligibility or current probabilities.",
]


def week_identity(value: str) -> tuple[int, int, datetime, datetime]:
    """Require a canonical ISO week, including valid year-boundary week numbers."""
    match = re.fullmatch(r"(\d{4})-W(\d{2})", value)
    if not match:
        raise ValueError("Use YYYY-Www")
    year, week = map(int, match.groups())
    monday = datetime.fromisocalendar(year, week, 1).replace(tzinfo=UTC)
    start = monday - timedelta(days=1)
    return year, week, start, start + timedelta(days=7)


def source_url(pair: str, week: str) -> str:
    if pair not in PAIRS:
        raise ValueError("Unknown private pair")
    year, number, _, _ = week_identity(week)
    return f"https://candledata.fxcorporate.com/m1/{pair}/{year}/{number}.csv.gz"


def receipt_clock(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() != timedelta(0):
        raise ValueError("Receipt must be UTC")
    return stamp


def parse_archive(body: bytes, week: str, received_at: str) -> list[tuple[Any, ...]]:
    """Reject the entire archive on any invalid observation; never repair a row."""
    if len(body) > MAX_COMPRESSED:
        raise ValueError("Compressed archive exceeds bound")
    with gzip.GzipFile(fileobj=io.BytesIO(body)) as archive:
        expanded = archive.read(MAX_EXPANDED + 1)
    if len(expanded) > MAX_EXPANDED:
        raise ValueError("Expanded archive exceeds bound")
    reader = csv.reader(io.StringIO(expanded.decode("utf-8-sig")))
    if tuple(next(reader, [])) != HEADER:
        raise ValueError("Unexpected archive header")
    _, _, start, end = week_identity(week)
    received = receipt_clock(received_at)
    result: list[tuple[Any, ...]] = []
    previous: datetime | None = None
    for row in reader:
        if len(row) != len(HEADER):
            raise ValueError("Invalid column count")
        if not re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}\.\d{3}", row[0]):
            raise ValueError("Invalid source datetime format")
        try:
            stamp = datetime.strptime(row[0], "%m/%d/%Y %H:%M:%S.%f").replace(tzinfo=UTC)
            prices = tuple(float(value) for value in row[1:])
        except ValueError:
            raise ValueError("Invalid source datetime/price") from None
        if stamp.second or stamp.microsecond or not start <= stamp < end or stamp > received:
            raise ValueError("Observation outside requested minute/receipt boundary")
        if previous is not None and stamp <= previous:
            raise ValueError("Non-increasing or duplicate archive timestamp")
        if not all(math.isfinite(price) and price > 0 for price in prices):
            raise ValueError("Non-finite or non-positive quote")
        for offset in (0, 4):
            opening, high, low, close = prices[offset : offset + 4]
            if not low <= min(opening, close) <= max(opening, close) <= high:
                raise ValueError("Invalid side OHLC")
        if any(prices[i + 4] < prices[i] for i in range(4)):
            raise ValueError("Crossed side bounds")
        result.append((stamp, *prices))
        previous = stamp
    if not result:
        raise ValueError("Empty archive")
    return result


def bounded_path(root: Path, value: str) -> Path:
    path = Path(value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Capture outside evidence directory")
    return path


def read_receipt(root: Path, reference: dict[str, Any]) -> dict[str, Any]:
    path = bounded_path(root, reference["capture_path"])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("Receipt hash mismatch")
    record: dict[str, Any] = json.loads(raw)
    if record["url"] != source_url(record["pair"], record["week"]):
        raise ValueError("Receipt request identity mismatch")
    receipt_clock(record["received_at"])
    body = bounded_path(root, record["capture_path"]).read_bytes()
    if hashlib.sha256(body).hexdigest() != record["sha256"] or len(body) != record["bytes"]:
        raise ValueError("Body hash/length mismatch")
    return {**record, "receipt_file": reference}


def capture_week(pair: str, week: str, root: Path, *, refresh: bool = False) -> dict[str, Any]:
    """Capture only this named week, preserving failed responses and old receipts."""
    url = source_url(pair, week)
    root.mkdir(parents=True, exist_ok=True)
    index = root / f"{pair}-{week}.json"
    if index.exists() and not refresh:
        record = read_receipt(root, json.loads(index.read_text(encoding="utf-8")))
        if (record["pair"], record["week"]) != (pair, week):
            raise ValueError("Cache request mismatch")
        return record
    body = bytearray()
    status: int | None = None
    complete = True
    error: str | None = None
    try:
        with requests.get(url, stream=True, allow_redirects=False, timeout=(10, 30)) as response:
            status = response.status_code
            for chunk in response.iter_content(64_000):
                remaining = MAX_COMPRESSED - len(body)
                body.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    complete = False
                    error = "Compressed response exceeds bound"
                    break
    except requests.RequestException as exc:
        complete = False
        error = type(exc).__name__
    received_at = datetime.now(UTC).isoformat()
    identity = uuid4().hex
    raw_path = root / f"{identity}.bin"
    with raw_path.open("xb") as handle:
        handle.write(body)
    record = {
        "pair": pair,
        "week": week,
        "url": url,
        "http_status": status,
        "received_at": received_at,
        "capture_path": str(raw_path.resolve()),
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
        "body_complete": complete,
        "transport_error": error,
    }
    receipt_path = root / f"{identity}.receipt.json"
    with receipt_path.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, allow_nan=False)
    reference = {
        "capture_path": str(receipt_path.resolve()),
        "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    }
    atomic_json(index, reference)
    return {**record, "receipt_file": reference}


def expected_minutes(week: str) -> set[datetime]:
    _, _, sunday, _ = week_identity(week)
    local = sunday.date()
    zone = ZoneInfo("America/New_York")
    start = datetime(local.year, local.month, local.day, 17, tzinfo=zone).astimezone(UTC)
    friday = local + timedelta(days=5)
    end = datetime(friday.year, friday.month, friday.day, 17, tzinfo=zone).astimezone(UTC)
    return {start + timedelta(minutes=i) for i in range(int((end - start).total_seconds() / 60))}


def gap_ranges(missing: set[datetime]) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    for stamp in sorted(missing):
        if ranges and stamp == datetime.fromisoformat(ranges[-1]["last"]) + timedelta(minutes=1):
            ranges[-1]["last"] = stamp.isoformat()
            ranges[-1]["minutes"] += 1
        else:
            ranges.append({"first": stamp.isoformat(), "last": stamp.isoformat(), "minutes": 1})
    return ranges


def audit_pair(pair: str, records: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    """Re-read every pinned body and union exact quotes, without filling gaps."""
    quotes: dict[datetime, tuple[Any, ...]] = {}
    expected: set[datetime] = set()
    verified: list[dict[str, Any]] = []
    duplicates = 0
    failures: list[str] = []
    for saved in records:
        record = read_receipt(root, saved["receipt_file"])
        if record["pair"] != pair or record != saved:
            raise ValueError("Saved receipt identity mismatch")
        verified.append(record)
        expected.update(expected_minutes(record["week"]))
        if record["http_status"] != 200 or not record["body_complete"]:
            failures.append(record["week"] + ": response unavailable/incomplete")
            continue
        try:
            rows = parse_archive(
                Path(record["capture_path"]).read_bytes(), record["week"], record["received_at"]
            )
        except (ValueError, OSError, UnicodeError, EOFError, csv.Error) as exc:
            reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            failures.append(record["week"] + ": rejected archive (" + reason + ")")
            continue
        for row in rows:
            if row[0] in quotes:
                if quotes[row[0]] != row:
                    failures.append("Conflicting same-minute quote")
                duplicates += 1
            else:
                quotes[row[0]] = row
    result: dict[str, Any] = {
        "pair": pair,
        "status": "UNAVAILABLE",
        "execution_qualification": "UNQUALIFIED",
        "timestamp_role": "UNKNOWN",
        "source": "FXCM public m1 indicative archives",
        "requested_weeks": sorted({record["week"] for record in verified}),
        "archives": verified,
        "limitations": LIMITS,
        "failures": failures,
    }
    if not verified or failures:
        return result
    missing = expected - quotes.keys()
    stamps = sorted(quotes)
    differences = [
        round((row[offset + 4] - row[offset]) * 10_000, 8)
        for row in quotes.values()
        for offset in (1, 4)
    ]
    result.update(
        {
            "status": "INDICATIVE_SOURCE_AUDIT",
            "observed_minutes": len(quotes),
            "equal_duplicates": duplicates,
            "first": stamps[0].isoformat(),
            "last": stamps[-1].isoformat(),
            "proxy_expected_minutes": len(expected),
            "proxy_observed_minutes": len(expected & quotes.keys()),
            "proxy_missing_minutes": len(missing),
            "outside_proxy_minutes": len(quotes.keys() - expected),
            "missing_ranges": gap_ranges(missing),
            "side_open_close_difference_pips": {
                "minimum": min(differences),
                "mean": sum(differences) / len(differences),
                "maximum": max(differences),
                "count": len(differences),
            },
        }
    )
    return result


def capture_cohort(
    root: Path, weeks: list[str], pairs: list[str], *, refresh: bool = False
) -> dict[str, Any]:
    if not weeks or len(weeks) > 12 or len(set(weeks)) != len(weeks):
        raise ValueError("Name one to twelve distinct ISO weeks")
    if not pairs or len(set(pairs)) != len(pairs) or not set(pairs) <= set(PAIRS):
        raise ValueError("Unknown/duplicate private pair")
    for week in weeks:
        week_identity(week)
    result = {
        "schema_version": "private-bidask-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "pair_audits": [
            audit_pair(
                pair, [capture_week(pair, week, root, refresh=refresh) for week in weeks], root
            )
            for pair in pairs
        ],
    }
    atomic_json(root / "cohorts" / f"{uuid4().hex}.json", result)
    atomic_json(root / "evidence.json", result)
    return result


def load_evidence(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "evidence.json"
    if not path.exists():
        return {}
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved["schema_version"] != "private-bidask-v1":
        raise ValueError("Unknown evidence schema")
    result: dict[str, dict[str, Any]] = {}
    for item in saved["pair_audits"]:
        pair = item["pair"]
        if pair not in PAIRS or pair in result:
            raise ValueError("Unknown/duplicate evidence pair")
        recomputed = audit_pair(pair, item["archives"], root)
        if recomputed != item:
            raise ValueError("Saved audit does not reproduce")
        result[pair] = recomputed
    return result
