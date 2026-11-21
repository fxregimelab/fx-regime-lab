"""Original official statement inventory; announcement levels are not surprises."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import UTC, date, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from uuid import uuid4

import requests
from bs4 import BeautifulSoup

from src.private_desk.bidask import bounded_path, receipt_clock
from src.private_desk.releases import capture_release, english_date, read_receipt, release_clock
from src.private_desk.report import atomic_json

METHOD = "private-fomc-history-v1"
HOST = "https://www.federalreserve.gov"
INDEX_URLS = tuple(
    f"{HOST}/monetarypolicy/fomchistorical{year}.htm" for year in range(2014, 2021)
) + (HOST + "/monetarypolicy/fomccalendars.htm",)
EXPECTED = {
    2015: "01-28 03-18 04-29 06-17 07-29 09-17 10-28 12-16",
    2016: "01-27 03-16 04-27 06-15 07-27 09-21 11-02 12-14",
    2017: "02-01 03-15 05-03 06-14 07-26 09-20 11-01 12-13",
    2018: "01-31 03-21 05-02 06-13 08-01 09-26 11-08 12-19",
    2019: "01-30 03-20 05-01 06-19 07-31 09-18 10-11 10-30 12-11",
    2020: "01-29 03-03 03-15 03-23 04-29 06-10 07-29 09-16 11-05 12-16",
    2021: "01-27 03-17 04-28 06-16 07-28 09-22 11-03 12-15",
    2022: "01-26 03-16 05-04 06-15 07-27 09-21 11-02 12-14",
    2023: "02-01 03-22 05-03 06-14 07-26 09-20 11-01 12-13",
    2024: "01-31 03-20 05-01 06-12 07-31 09-18 11-07 12-18",
}
EXPECTED_DATES = {f"{year}-{day}" for year, days in EXPECTED.items() for day in days.split()}
SEED = "2014-12-17"
LIMITS = [
    "Current official archive bytes; original-release vintage and historical receipt unknown.",
    "Announcement target range is not an effective rate, yield, carry or policy surprise.",
    "2015 exact clocks are unavailable; no inferred 2 p.m. timestamp.",
    "Other policy actions, implementation notes and expectations are outside this inventory.",
    "Private development evidence; current probabilities and trade qualification unchanged.",
]


def _digest(raw: bytes | bytearray) -> str:
    return hashlib.sha256(raw).hexdigest()


def discover_index(body: bytes, url: str) -> dict[str, Any]:
    if url not in INDEX_URLS or len(body) > 2_000_000:
        raise ValueError("Unexpected or oversized official index")
    soup = BeautifulSoup(body, "html.parser")
    annual = re.search(r"fomchistorical(\d{4})\.htm$", url)
    links: list[dict[str, str]] = []
    exceptions = []
    if annual:
        year = int(annual[1])
        headings = soup.find_all("h5")
        for anchor in soup.find_all("a"):
            if anchor.get_text(" ", strip=True) != "Statement":
                continue
            heading = anchor.find_previous("h5")
            if heading is None or str(year) not in heading.get_text(" ", strip=True):
                raise ValueError("Statement has no year-bound meeting heading")
            links.append(
                _link(str(anchor.get("href", "")), year, heading.get_text(" ", strip=True))
            )
        names = {item["meeting_heading"] for item in links}
        exceptions = [
            h.get_text(" ", strip=True)
            for h in headings
            if str(year) in h.get_text(" ", strip=True) and h.get_text(" ", strip=True) not in names
        ]
    else:
        for panel in soup.select("div.panel"):
            header = panel.select_one(".panel-heading h4")
            match = (
                re.fullmatch(r"(202[1-4]) FOMC Meetings", header.get_text(" ", strip=True))
                if header
                else None
            )
            if not match:
                continue
            year = int(match[1])
            for meeting in panel.select(".fomc-meeting"):
                month = meeting.select_one(".fomc-meeting__month")
                dates = meeting.select_one(".fomc-meeting__date")
                if month is None or dates is None:
                    raise ValueError("Missing meeting identity")
                label = (
                    f"{month.get_text(' ', strip=True)} {dates.get_text(' ', strip=True)} - {year}"
                )
                found = []
                for anchor in meeting.find_all("a"):
                    if (
                        anchor.get_text(" ", strip=True) == "HTML"
                        and anchor.parent
                        and anchor.parent.get_text(" ", strip=True).startswith("Statement:")
                    ):
                        found.append(_link(str(anchor.get("href", "")), year, label))
                if len(found) > 1:
                    raise ValueError("Ambiguous statement link")
                links.extend(found)
                if not found:
                    exceptions.append(label)
    if len({item["url"] for item in links}) != len(links):
        raise ValueError("Duplicate official statement identity")
    update = soup.find(string=re.compile(r"Last Update:"))
    return {
        "url": url,
        "links": links,
        "headings_without_statement": exceptions,
        "index_last_update": update.strip() if update else None,
    }


def _link(href: str, year: int, heading: str) -> dict[str, str]:
    url = urljoin(HOST, href)
    match = re.fullmatch(re.escape(HOST) + r"/newsevents/pressreleases/monetary(\d{8})a\.htm", url)
    if not match:
        raise ValueError("Statement link must be an exact official archive URL")
    day = datetime.strptime(match[1], "%Y%m%d").date()
    if day.year != year:
        raise ValueError("Statement link date is outside meeting year")
    return {"url": url, "release_date": day.isoformat(), "meeting_heading": heading}


def _bound(token: str) -> float:
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return float(token)
    match = re.fullmatch(r"(?:(\d+)-)?(\d+)/(\d+)", token)
    if not match or not 0 < int(match[2]) < int(match[3]):
        raise ValueError("Only proper published fractions are supported")
    return float(int(match[1] or 0) + Fraction(int(match[2]), int(match[3])))


def parse_statement(body: bytes, day: str, received_at: str) -> dict[str, Any]:
    requested = date.fromisoformat(day)
    soup = BeautifulSoup(body, "html.parser")
    articles = soup.select("#article")
    if len(articles) != 1:
        raise ValueError("Missing/ambiguous statement article")
    article = articles[0]
    titles, dates, clocks = (
        article.select("h3"),
        article.select(".article__time"),
        article.select(".releaseTime"),
    )
    if (
        len(titles) != 1
        or len(dates) != 1
        or len(clocks) != 1
        or english_date(dates[0].get_text(" ", strip=True)) != requested
    ):
        raise ValueError("Ambiguous statement title/date/clock")
    title = titles[0].get_text(" ", strip=True)
    kind = "TARGET_DECISION"
    if day == "2019-10-11" and title == "Statement Regarding Monetary Policy Implementation":
        kind = "IMPLEMENTATION_ONLY_NO_STANCE_CHANGE"
        if "do not represent a change in the stance of monetary policy" not in article.get_text(
            " ", strip=True
        ):
            raise ValueError("Implementation-only classification unsupported")
    elif title != "Federal Reserve issues FOMC statement":
        raise ValueError("Unexpected statement title")
    elif day == "2020-03-23":
        kind = "OTHER_POLICY_STATEMENT"
        if "directs the Desk" not in article.get_text(" ", strip=True):
            raise ValueError("Restatement classification unsupported")
    clock = clocks[0].get_text(" ", strip=True)
    matches = re.findall(r"For release at (\d{1,2}):(\d{2}) (a\.m\.|p\.m\.) (EST|EDT)", clock)
    release_at = None
    if len(matches) == 1:
        hour, minute, meridiem, zone = matches[0]
        release_at = (
            release_clock(requested, int(hour), int(minute), meridiem, zone)
            .astimezone(UTC)
            .isoformat()
        )
        if receipt_clock(release_at) > receipt_clock(received_at):
            raise ValueError("Release is after original capture")
    elif not matches and clock.startswith("For immediate release"):
        pass
    else:
        raise ValueError("Missing/ambiguous source clock")
    receipt_clock(received_at)
    original = None
    lower = upper = None
    if kind == "TARGET_DECISION":
        paragraphs = [p.get_text(" ", strip=True) for p in article.find_all("p")]
        decisions = []
        for paragraph in paragraphs:
            normalized = (
                paragraph.replace("\xa0", " ").replace("\u2011", "-").replace("\u2013", "-")
            )
            normalized = re.sub(r"\s+", " ", normalized)
            # An explicit Committee decision, never a dissenting preference or Desk quote.
            if not re.search(
                r"the (?:Committee|Federal Open Market Committee) "
                r"(?:decided (?:today )?to|today reaffirmed)",
                normalized,
                re.IGNORECASE,
            ) or re.search(r"Voting (?:for|against)|directs the Desk", normalized):
                continue
            forward = re.findall(
                r"target range for the federal funds rate "
                r"(?:by [\d./-]+ percentage point,? )?(?:to|at) "
                r"([\d./-]+) to ([\d./-]+) percent",
                normalized,
            )
            reverse = re.findall(
                r"current ([\d./-]+) to ([\d./-]+) percent target range "
                r"for the federal funds rate remains appropriate",
                normalized,
            )
            for lo, hi in forward + reverse:
                decisions.append((_bound(lo), _bound(hi), paragraph))
        if len(decisions) != 1:
            raise ValueError("Missing/ambiguous Committee target decision")
        lower, upper, original = decisions[0]
        if not 0 <= lower <= upper <= 30 or upper - lower > 1:
            raise ValueError("Invalid announced target bounds")
    update = soup.find(string=re.compile(r"Last Update:"))
    return {
        "release_date": day,
        "title": title,
        "document_class": kind,
        "source_release_line": clock,
        "source_stated_release_at": release_at,
        "timing_status": "SOURCE_STATED_RELEASE_CLOCK" if release_at else "DATE_ONLY",
        "target_lower_percent": lower,
        "target_upper_percent": upper,
        "target_midpoint_percent": (lower + upper) / 2
        if lower is not None and upper is not None
        else None,
        "original_decision_paragraph": original,
        "page_last_update": update.strip() if update else None,
        "historical_receipt_at": None,
        "actual_transmission_at": None,
        "effective_policy_date": None,
        "archival_revision_status": "UNKNOWN",
        "consensus": None,
        "surprise": None,
        "forecast_qualification": "UNQUALIFIED",
    }


def _read_index(root: Path, reference: dict[str, str]) -> dict[str, Any]:
    raw = bounded_path(root, reference["capture_path"]).read_bytes()
    if _digest(raw) != reference["sha256"]:
        raise ValueError("Index receipt changed")
    record: dict[str, Any] = json.loads(raw)
    if record["url"] not in INDEX_URLS:
        raise ValueError("Unexpected index identity")
    receipt_clock(record["received_at"])
    body = bounded_path(root, record["capture_path"]).read_bytes()
    if len(body) != record["bytes"] or _digest(body) != record["sha256"]:
        raise ValueError("Index body changed")
    return {**record, "receipt_file": reference}


def capture_index(root: Path, url: str) -> dict[str, Any]:
    if url not in INDEX_URLS:
        raise ValueError("Only named official meeting indexes are allowed")
    root.mkdir(parents=True, exist_ok=True)
    index = root / (_digest(url.encode()) + ".json")
    if index.exists():
        result = _read_index(root, json.loads(index.read_bytes()))
        if result["url"] != url:
            raise ValueError("Cached index request changed")
        return result
    body = bytearray()
    status, content_type, error = None, "", None
    complete = True
    try:
        with requests.get(url, stream=True, allow_redirects=False, timeout=(10, 30)) as response:
            status, content_type = response.status_code, response.headers.get("content-type", "")
            for chunk in response.iter_content(64_000):
                remaining = 2_000_000 - len(body)
                body.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    complete, error = False, "BODY_BOUND_EXCEEDED"
                    break
    except requests.RequestException as exc:
        complete, error = False, type(exc).__name__
    token = uuid4().hex
    path = root / (token + ".bin")
    with path.open("xb") as stream:
        stream.write(body)
    record = {
        "url": url,
        "received_at": datetime.now(UTC).isoformat(),
        "http_status": status,
        "content_type": content_type,
        "body_complete": complete,
        "transport_error": error,
        "capture_path": str(path.resolve()),
        "bytes": len(body),
        "sha256": _digest(body),
    }
    receipt = root / (token + ".receipt.json")
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
    reference = {"capture_path": str(receipt.resolve()), "sha256": _digest(receipt.read_bytes())}
    atomic_json(index, reference)
    return {**record, "receipt_file": reference}


def audit_history(
    root: Path, indexes: list[dict[str, Any]], captures: list[dict[str, Any]]
) -> dict[str, Any]:
    discovery, failures = [], []
    links: dict[str, dict[str, str]] = {}
    if len(indexes) != 8 or {r["url"] for r in indexes} != set(INDEX_URLS):
        raise ValueError("Exactly eight official index identities are required")
    for saved in indexes:
        record = _read_index(root / "indexes", saved["receipt_file"])
        if record != saved:
            raise ValueError("Index manifest changed")
        if (
            record["http_status"] != 200
            or not record["body_complete"]
            or not record["content_type"].lower().startswith("text/html")
        ):
            raise ValueError("Official discovery source unavailable")
        item = discover_index(Path(record["capture_path"]).read_bytes(), record["url"])
        discovery.append(item)
        for link in item["links"]:
            if "2015-01-01" <= link["release_date"] <= "2024-12-31" or link["release_date"] == SEED:
                if link["release_date"] in links:
                    raise ValueError("Duplicate cross-index statement")
                links[link["release_date"]] = {**link, "index_url": record["url"]}
    if set(links) != EXPECTED_DATES | {SEED}:
        raise ValueError("Official inventory differs from independently reviewed dates")
    by_date: dict[str, dict[str, Any]] = {}
    for saved in captures:
        record = read_receipt(root / "releases", saved["receipt_file"])
        if record != saved or record["request"]["source"] != "FOMC":
            raise ValueError("Statement receipt identity changed")
        day = record["request"]["date"]
        if day not in links or day in by_date or record["url"] != links[day]["url"]:
            raise ValueError("Unknown/duplicate statement capture")
        by_date[day] = record
    events, previous = [], None
    for day in sorted(links):
        statement_record = by_date.get(day)
        try:
            if (
                statement_record is None
                or statement_record["http_status"] != 200
                or not statement_record["body_complete"]
                or not statement_record["content_type"].lower().startswith("text/html")
            ):
                raise ValueError("Original statement unavailable")
            event = parse_statement(
                Path(statement_record["capture_path"]).read_bytes(),
                day,
                statement_record["received_at"],
            )
        except (ValueError, UnicodeError, ZeroDivisionError) as exc:
            failures.append(
                {
                    "release_date": day,
                    "reason": str(exc),
                    "http_status": statement_record.get("http_status")
                    if statement_record
                    else None,
                }
            )
            if day not in ("2019-10-11", "2020-03-23"):
                previous = None
            continue
        event.update(links[day])
        event["body_sha256"] = statement_record["sha256"]
        event["capture_received_at"] = statement_record["received_at"]
        event["predecessor_release_date"] = None
        event["change_from_prior_statement_pp"] = None
        if event["document_class"] == "TARGET_DECISION":
            if previous is not None:
                event["predecessor_release_date"] = previous["release_date"]
                event["change_from_prior_statement_pp"] = (
                    event["target_midpoint_percent"] - previous["target_midpoint_percent"]
                )
            previous = event
        if day != SEED:
            events.append(event)
    return {
        "method_version": METHOD,
        "status": "PARTIAL" if failures else "SOURCE_RECONSTRUCTION",
        "inventory_statement_count": len(EXPECTED_DATES),
        "captured_statement_count": len(captures),
        "events": events,
        "failures": failures,
        "indexes": indexes,
        "captures": captures,
        "discovery": discovery,
        "yearly_inventory_counts": dict(Counter(day[:4] for day in EXPECTED_DATES)),
        "target_change_count": sum(
            e["change_from_prior_statement_pp"] not in (None, 0) for e in events
        ),
        "exact_clock_count": sum(e["source_stated_release_at"] is not None for e in events),
        "historical_availability": "UNKNOWN",
        "forecast_qualification": "UNQUALIFIED",
        "limitations": LIMITS,
    }


def capture_history(root: Path) -> dict[str, Any]:
    indexes = [capture_index(root / "indexes", url) for url in INDEX_URLS]
    # Validate original discovery before permitting statement requests.
    inventory = audit_history(root, indexes, [])
    dates = sorted(
        {
            link["release_date"]
            for item in inventory["discovery"]
            for link in item["links"]
            if link["release_date"] in EXPECTED_DATES | {SEED}
        }
    )
    if len(dates) > 100:
        raise ValueError("Statement request bound exceeded")
    captures = []
    for day in dates:
        captures.append(capture_release(root / "releases", {"source": "FOMC", "date": day}))
        print("FOMC_CAPTURE", len(captures), len(dates), day, flush=True)
    evidence = audit_history(root, indexes, captures)
    artifact = root / "cohorts" / (uuid4().hex + ".json")
    atomic_json(artifact, evidence)
    atomic_json(root / "evidence.json", evidence)
    return evidence


def load_history(root: Path) -> dict[str, Any]:
    saved: dict[str, Any] = json.loads((root / "evidence.json").read_bytes())
    result = audit_history(root, saved["indexes"], saved["captures"])
    if result != saved:
        raise ValueError("Saved FOMC history does not replay")
    return result
