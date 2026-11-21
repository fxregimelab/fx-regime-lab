"""Original BIS policy histories and retrospective, definition-aware pair features."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests

from src.private_desk.bidask import bounded_path, receipt_clock
from src.private_desk.report import PAIRS, atomic_json

AREAS = {
    "USD": "US", "EUR": "XM", "GBP": "GB", "AUD": "AU",
    "NZD": "NZ", "CAD": "CA", "CHF": "CH", "JPY": "JP",
}
LEGACY_CURRENCIES = tuple(currency for currency in AREAS if currency != "JPY")
HEADER = (
    "FREQ",
    "REF_AREA",
    "UNIT_MEASURE",
    "UNIT_MULT",
    "TIME_FORMAT",
    "COMPILATION",
    "DECIMALS",
    "SOURCE_REF",
    "SUPP_INFO_BREAKS",
    "TITLE",
    "TIME_PERIOD",
    "OBS_VALUE",
    "OBS_STATUS",
    "OBS_CONF",
    "OBS_PRE_BREAK",
)
MAX_BODY = 8 * 1024 * 1024
BODY_LIMITS = {currency: MAX_BODY for currency in AREAS}
BODY_LIMITS["JPY"] = 16 * 1024 * 1024
LEGACY_METHOD_VERSION = "private-policy-history-v1"
METHOD_VERSION = "private-policy-history-v2"
DOCUMENTATION = "https://www.bis.org/statistics/cbpol/cbpol_doc.pdf"
LIMITS = [
    "Current BIS snapshot of historical policy markers; verified historical vintages are absent.",
    "Observation/effective dates do not establish announcement or historical provider arrival.",
    "Weekly publication practice does not supply an observation-specific availability clock.",
    "Different central banks and historical segments use different policy instruments.",
    "Pair difference is percentage points of policy markers, not a 2Y spread, carry or surprise.",
    "Retrospective features cannot qualify historical forecasts, probabilities or current trades.",
]

# Dates and instruments are reviewed against the original BIS documentation.
SEGMENTS: dict[str, tuple[tuple[str, str | None], ...]] = {
    "USD": (("1985-12-19", "FED_TARGET_MIDPOINT"),),
    "EUR": (
        ("1999-01-05", "ECB_MRO_FIXED"),
        ("2000-06-28", "ECB_MRO_MINIMUM_BID"),
        ("2008-10-15", "ECB_MRO_FIXED"),
        ("2024-09-18", "ECB_DEPOSIT_FACILITY"),
    ),
    "GBP": (("1997-05-06", "BOE_REPO"), ("2006-08-03", "BOE_BANK_RATE")),
    "AUD": (("1990-08-02", "RBA_CASH_TARGET"),),
    # Registry begins within the requested euro-era scope, not at the series' inception.
    "NZD": (("1999-01-01", "NZ_OVERNIGHT_CASH"), ("1999-03-17", "RBNZ_OFFICIAL_CASH")),
    "CAD": (("1994-06-01", "BOC_OVERNIGHT_TARGET"),),
    "CHF": (
        ("1946-01-01", "SNB_DISCOUNT"),
        ("2000-01-01", "SNB_TARGET_MIDPOINT"),
        ("2019-06-13", "SNB_POLICY_RATE"),
    ),
    "JPY": (
        ("1998-09-09", "BOJ_OVERNIGHT_CALL_TARGET"),
        ("1999-02-12", None),
        ("2000-08-11", "BOJ_OVERNIGHT_CALL_TARGET"),
        ("2001-03-19", None),
        ("2006-03-09", "BOJ_OVERNIGHT_CALL_EFFECTIVELY_ZERO"),
        ("2006-07-14", "BOJ_OVERNIGHT_CALL_TARGET"),
        ("2010-10-05", "BOJ_OVERNIGHT_CALL_TARGET_MIDPOINT"),
        ("2013-04-04", None),
        ("2016-09-21", "BOJ_SHORT_TERM_POLICY_RATE_YCC"),
        ("2024-03-21", "BOJ_OVERNIGHT_CALL_TARGET_MIDPOINT"),
        ("2024-08-01", "BOJ_OVERNIGHT_CALL_TARGET"),
    ),
}

# Pinned, independently reviewed source definitions. Changed definitions need a new review.
COMPILATION = {
    "USD": (
        "From 19 Dec 1985 onwards: mid-point of the Federal Reserve target rate; from 1 Jul "
        "1954 to 18 Dec 1985: US Fed Funds effective rate."
    ),
    "EUR": (
        "From 18 Sep 2024 onwards: official central bank steering rate is the deposit "
        "facility rate, fixed rate; from 15 Oct 2008 to 17 Sep 2024: official central bank "
        "liquidity providing, main refinancing operations, fixed rate; from 28 Jun 2000 to "
        "14 Oct 2008: official central bank liquidity providing, main refinancing "
        "operations, minimum bid rate; from 5 Jan 1999 to 27 Jun 2000: official central "
        "bank liquidity providing, main refinancing operations, fixed rate."
    ),
    "GBP": (
        "From 3 Aug 2006 onwards: official bank rate; from 6 May 1997 to 2 Aug 2006: repo "
        "rate; from 20 Aug 1981 to 5 May 1997: minimum Bank of England Band 1 dealing rate; "
        "from 16 Oct 1972 to 19 Aug 1981: minimum lending rate; from 1 Jan 1946 to 15 Oct "
        "1972: bank rate."
    ),
    "AUD": (
        "From 2 Aug 1990 onwards: cash rate target; from 23 Jan 1990 to 1 Aug 1990: middle "
        "of the cash rate target range; from 7 Apr 1976 to 22 Jan 1990: interbank overnight "
        "cash rate."
    ),
    "NZD": (
        "From 17 Mar 1999 onwards: Official market intervention representative rate, "
        "official cash rate; from Jan 1985 to 16 Mar 1999: overnight cash rate."
    ),
    "CAD": (
        "From 1 Jun 1994 onwards: Central Bank target, overnight rate; from 27 Jul 1960 to "
        "31 May 1994: official bank rate."
    ),
    "CHF": (
        "From 13 June 2019 onwards SNB Policy rate; From 1 Jan 2000 to 12 June 2019 "
        "mid-point of the SNB target range; from 1 Jan 1946 to 31 Dec 1999: discount rate."
    ),
    "JPY": (
        "From 24 Sep 2026: the BOJ encourages the uncollateralized overnight call rate to "
        "remain at around 1.25 percent; From 17 Jun 2026 to 23 Sep 2026: the BOJ encourages "
        "the uncollateralized overnight call rate to remain at around 1.00 percent; From "
        "22 Dec 2025 to 16 Jun 2026: the BOJ encourages the uncollateralized overnight call "
        "rate to remain at around 0.75 percent; From 27 Jan 2025 to 21 Dec 2025: the BOJ "
        "encourages the uncollateralized overnight call rate to remain at around 0.50 "
        "percent; From 1 Aug 2024 to 26 Jan 2025: the BOJ encouraged the UOCR to remain "
        "at around 0.25% ; From 21 Mar 2024 to 31 July: the BOJ encouraged the UOCR to "
        "remain at around 0 to 0.1 %; from 21 Sep 2016 to 20 Mar 2024: the BOJ set the "
        "guideline for market operations which specifies a short-term policy interest "
        "rate at minus 0.1% and a target level of 10-year JGB yields at around 0%. "
        "Short-term policy interest rate; from 4 Apr 2013 to 20 Sep 2016: no policy rate; "
        "from 5 Oct 2010 to 3 Apr 2013: the BOJ encouraged the UOCR to remain at around "
        "0 to 0.1%; from 19 Dec 2008 to 4 Oct 2010: the BOJ encouraged the UOCR to remain "
        "at around 0. %; from 31 Oct 2008 to 18 Dec 2008: the BOJ encouraged the UOCR to "
        "remain at around 0.3%; before 30 Oct 2008, refer to https://data.bis.org/topics/CBPOL"
    ),
}
SOURCES = dict(
    zip(
        AREAS,
        (
            "US Federal Reserve System",
            "European Central Bank",
            "Bank of England",
            "Reserve Bank of Australia",
            "Reserve Bank of New Zealand",
            "Bank of Canada",
            "Swiss National Bank",
            "Bank of Japan",
        ),
        strict=True,
    )
)


def canonical_date(value: str) -> date:
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError("Expected YYYY-MM-DD")
    return result


def policy_request_url(spec: dict[str, str]) -> str:
    if set(spec) != {"currency", "start", "end"} or spec["currency"] not in AREAS:
        raise ValueError("Unknown policy currency/request")
    start, end = canonical_date(spec["start"]), canonical_date(spec["end"])
    try:
        limit = start.replace(year=start.year + 31)
    except ValueError:
        limit = start.replace(year=start.year + 31, day=28)
    if start < date(1999, 1, 5) or end < start or end > limit:
        raise ValueError("Policy window must begin in the euro era and span at most 31 years")
    if end > datetime.now(UTC).date():
        raise ValueError("Future policy window")
    return (
        "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D."
        + AREAS[spec["currency"]]
        + "?format=csv&startPeriod="
        + spec["start"]
        + "&endPeriod="
        + spec["end"]
    )


def instrument_at(currency: str, day: str) -> str | None:
    canonical_date(day)
    if currency not in AREAS:
        raise ValueError("Unknown currency")
    eligible = [name for start, name in SEGMENTS[currency] if start <= day]
    return eligible[-1] if eligible else None


def _rate(value: str) -> float | None:
    if value == "":
        return None
    result = float(value)
    if not math.isfinite(result) or not -10 <= result <= 100:
        raise ValueError("Invalid policy marker")
    return result


def parse_policy_history(body: bytes, spec: dict[str, str], received_at: str) -> dict[str, Any]:
    policy_request_url(spec)
    if len(body) > BODY_LIMITS[spec["currency"]]:
        raise ValueError("Policy response exceeds bound")
    received_clock = receipt_clock(received_at)
    if received_clock > datetime.now(UTC):
        raise ValueError("Future policy receipt")
    received = received_clock.date()
    if canonical_date(spec["end"]) > received:
        raise ValueError("Future policy window")
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    if tuple(reader.fieldnames or ()) != HEADER:
        raise ValueError("Unexpected policy CSV header")
    metadata: dict[str, str] | None = None
    seen: dict[str, dict[str, Any]] = {}
    previous = ""
    duplicates = 0
    for raw in reader:
        if None in raw or any(value is None for value in raw.values()):
            raise ValueError("Malformed policy row")
        if (raw["FREQ"], raw["REF_AREA"], raw["UNIT_MEASURE"], raw["UNIT_MULT"]) != (
            "D",
            AREAS[spec["currency"]],
            "368",
            "0",
        ):
            raise ValueError("Policy dimension/unit mismatch")
        if raw["TIME_FORMAT"] != "" or raw["OBS_CONF"] != "F":
            raise ValueError("Unexpected policy format/confidentiality")
        day = raw["TIME_PERIOD"]
        canonical_date(day)
        if not spec["start"] <= day <= spec["end"] or canonical_date(day) > received:
            raise ValueError("Policy observation outside window/receipt")
        if day < previous:
            raise ValueError("Unordered policy observations")
        token = raw["OBS_VALUE"]
        value = None if raw["OBS_STATUS"] == "M" and token in ("NaN", "") else _rate(token)
        pre_break = _rate(raw["OBS_PRE_BREAK"])
        if raw["OBS_STATUS"] not in (("A",) if value is not None else ("A", "M")):
            raise ValueError("Unsupported policy observation status")
        current_meta = {
            key: raw[key].strip()
            for key in ("COMPILATION", "DECIMALS", "SOURCE_REF", "SUPP_INFO_BREAKS", "TITLE")
        }
        if (
            not current_meta["SOURCE_REF"]
            or not current_meta["COMPILATION"]
            or not current_meta["TITLE"]
        ):
            raise ValueError("Missing policy instrument/source metadata")
        if current_meta["DECIMALS"] not in ("0", "1", "2", "3", "4", "5", "6"):
            raise ValueError("Unexpected decimals metadata")
        if spec["currency"] == "JPY" and (
            current_meta["DECIMALS"] != "4"
            or current_meta["TITLE"] != "Central bank policy rates - Japan - Daily - End of period"
        ):
            raise ValueError("Unreviewed Japan title/precision metadata")
        if (
            current_meta["COMPILATION"] != COMPILATION[spec["currency"]]
            or current_meta["SOURCE_REF"] != SOURCES[spec["currency"]]
        ):
            raise ValueError("Unreviewed policy definition/source metadata")
        if metadata is not None and metadata != current_meta:
            raise ValueError("Inconsistent series metadata")
        metadata = current_meta
        row = {
            "observation_date": day,
            "value": value,
            "status": raw["OBS_STATUS"],
            "pre_break_value": pre_break,
            "instrument": instrument_at(spec["currency"], day),
        }
        if day in seen:
            if seen[day] != row:
                raise ValueError("Conflicting policy observation")
            duplicates += 1
        else:
            seen[day] = row
        previous = day
    if not seen:
        raise ValueError("Empty policy observations")
    return {
        "currency": spec["currency"],
        "area": AREAS[spec["currency"]],
        "metadata": metadata,
        "rows": list(seen.values()),
        "equal_duplicates": duplicates,
    }


def read_receipt(root: Path, reference: dict[str, Any]) -> dict[str, Any]:
    raw = bounded_path(root, reference["capture_path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("Policy receipt hash mismatch")
    record: dict[str, Any] = json.loads(raw)
    if record["url"] != policy_request_url(record["request"]):
        raise ValueError("Policy receipt request mismatch")
    if receipt_clock(record["received_at"]) > datetime.now(UTC):
        raise ValueError("Future policy receipt")
    body = bounded_path(root, record["capture_path"]).read_bytes()
    if (
        len(body) != record["bytes"]
        or len(body) > BODY_LIMITS[record["request"]["currency"]]
        or hashlib.sha256(body).hexdigest() != record["sha256"]
    ):
        raise ValueError("Policy body hash/length mismatch")
    return {**record, "receipt_file": reference}


def capture_policy_history(
    root: Path, spec: dict[str, str], *, refresh: bool = False
) -> dict[str, Any]:
    url = policy_request_url(spec)
    if canonical_date(spec["end"]) > datetime.now(UTC).date():
        raise ValueError("Future policy window")
    root.mkdir(parents=True, exist_ok=True)
    pointer = root / ("-".join(spec[key] for key in ("currency", "start", "end")) + ".json")
    if pointer.exists() and not refresh:
        record = read_receipt(root, json.loads(pointer.read_text(encoding="utf-8")))
        if record["request"] != spec:
            raise ValueError("Policy cache request mismatch")
        return record
    body = bytearray()
    status: int | None = None
    media, error = "", None
    complete = True
    try:
        with requests.get(
            url,
            headers={"Accept": "text/csv"},
            stream=True,
            allow_redirects=False,
            timeout=(10, 30),
        ) as response:
            status = response.status_code
            media = response.headers.get("Content-Type", "")
            for chunk in response.iter_content(64_000):
                remaining = BODY_LIMITS[spec["currency"]] - len(body)
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
        "content_type": media,
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
    atomic_json(pointer, reference)
    return {**record, "receipt_file": reference}


def audit_records(
    root: Path, records: list[dict[str, Any]], *, method_version: str = METHOD_VERSION
) -> dict[str, Any]:
    if method_version not in (METHOD_VERSION, LEGACY_METHOD_VERSION):
        raise ValueError("Unknown policy-history method")
    currencies = LEGACY_CURRENCIES if method_version == LEGACY_METHOD_VERSION else tuple(AREAS)
    parsed: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    receipts = []
    for saved in records:
        record = read_receipt(root, saved["receipt_file"])
        if record != saved:
            raise ValueError("Saved policy receipt mismatch")
        receipts.append(record)
        currency = record["request"]["currency"]
        if currency not in currencies:
            raise ValueError("Policy currency outside the declared method")
        reason = None
        if record["http_status"] != 200 or not record["body_complete"]:
            reason = "HTTP/transport unavailable"
        elif record["content_type"].split(";")[0].strip().lower() != "text/csv":
            reason = "Unexpected policy media type"
        else:
            try:
                panel = parse_policy_history(
                    Path(record["capture_path"]).read_bytes(),
                    record["request"],
                    record["received_at"],
                )
                if currency in parsed:
                    raise ValueError("Multiple policy snapshots for one currency")
                numeric = [row for row in panel["rows"] if row["value"] is not None]
                parsed[currency] = {
                    **panel,
                    "status": "RETROSPECTIVE_ONLY",
                    "numeric_count": len(numeric),
                    "missing_value_count": len(panel["rows"]) - len(numeric),
                    "first_numeric": numeric[0] if numeric else None,
                    "last_numeric": numeric[-1] if numeric else None,
                    "instrument_segments": [
                        {"start": start, "instrument": name} for start, name in SEGMENTS[currency]
                    ],
                    "sha256": record["sha256"],
                    "source_url": record["url"],
                    "receipt_at": record["received_at"],
                }
            except (ValueError, OSError, UnicodeError, csv.Error):
                reason = "Policy snapshot rejected"
        if reason:
            parsed.pop(currency, None)
            failures.append(
                {"currency": currency, "http_status": record["http_status"], "reason": reason}
            )
    # Any failed or conflicting capture for a currency prevents accepting another copy.
    for failure in failures:
        parsed.pop(failure["currency"], None)
    return {
        "method_version": method_version,
        "status": "PARTIAL_RETROSPECTIVE_HISTORY"
        if failures or set(parsed) != set(currencies)
        else "RETROSPECTIVE_POLICY_HISTORY",
        "covered_currencies": [currency for currency in currencies if currency in parsed],
        "series_audits": [parsed[currency] for currency in currencies if currency in parsed],
        "captures": receipts,
        "failures": failures,
        "historical_availability": "UNKNOWN",
        "historical_vintage": "UNKNOWN",
        "forecast_qualification": "UNQUALIFIED",
        "documentation_url": DOCUMENTATION,
        "limitations": LIMITS,
    }


def _weekday_window(day: str) -> list[str]:
    cursor = canonical_date(day)
    dates = [cursor.isoformat()]
    for _ in range(5):
        cursor -= timedelta(days=1)
        while cursor.weekday() >= 5:
            cursor -= timedelta(days=1)
        dates.append(cursor.isoformat())
    return list(reversed(dates))


def pair_policy_features(evidence: dict[str, Any], pair: str) -> dict[str, Any]:
    if pair not in PAIRS:
        raise ValueError("Unknown private pair")
    series = {item["currency"]: item for item in evidence["series_audits"]}
    base, quote = pair[:3], pair[3:]
    result: dict[str, Any] = {
        "pair": pair,
        "status": "RETROSPECTIVE_ONLY",
        "historical_availability": "UNKNOWN",
        "forecast_qualification": "UNQUALIFIED",
        "source_hashes": {
            currency: series[currency]["sha256"] for currency in (base, quote) if currency in series
        },
        "missing_currencies": [currency for currency in (base, quote) if currency not in series],
        "rows": [],
        "limitations": LIMITS,
    }
    if result["missing_currencies"]:
        result["status"] = "UNAVAILABLE"
        return result
    base_rows = {row["observation_date"]: row for row in series[base]["rows"]}
    quote_rows = {row["observation_date"]: row for row in series[quote]["rows"]}
    rows = []
    for day in sorted(base_rows.keys() | quote_rows.keys()):
        if canonical_date(day).weekday() >= 5:
            continue
        left, right = base_rows.get(day), quote_rows.get(day)
        level = (
            left["value"] - right["value"]
            if left
            and right
            and left["value"] is not None
            and right["value"] is not None
            and left["instrument"]
            and right["instrument"]
            else None
        )
        window = _weekday_window(day)
        values = []
        reason = None
        for stamp in window:
            a, b = base_rows.get(stamp), quote_rows.get(stamp)
            if not a or not b or a["value"] is None or b["value"] is None:
                reason = "MISSING_WEEKDAY_OR_VALUE"
                break
            if not a["instrument"] or not b["instrument"]:
                reason = "UNKNOWN_INSTRUMENT"
                break
            values.append((a, b))
        if reason is None:
            if len({(a["instrument"], b["instrument"]) for a, b in values}) > 1 or any(
                a["pre_break_value"] is not None or b["pre_break_value"] is not None
                for a, b in values[1:]
            ):
                reason = "INSTRUMENT_DEFINITION_BREAK"
        change = (
            (values[-1][0]["value"] - values[-1][1]["value"])
            - (values[0][0]["value"] - values[0][1]["value"])
            if reason is None
            else None
        )
        rows.append(
            {
                "observation_date": day,
                "base_value": left["value"] if left else None,
                "quote_value": right["value"] if right else None,
                "base_instrument": left["instrument"] if left else None,
                "quote_instrument": right["instrument"] if right else None,
                "policy_marker_difference_pp": level,
                "difference_change_5_weekdays_pp": change,
                "change_unavailable_reason": reason,
                "window_start": window[0],
                "status": "RETROSPECTIVE_ONLY",
                "provider_available_at": None,
                "historical_vintage": None,
            }
        )
    result["rows"] = rows
    result["matched_numeric_count"] = sum(
        row["policy_marker_difference_pp"] is not None for row in rows
    )
    result["change_numeric_count"] = sum(
        row["difference_change_5_weekdays_pp"] is not None for row in rows
    )
    result["first_numeric_date"] = next(
        (row["observation_date"] for row in rows if row["policy_marker_difference_pp"] is not None),
        None,
    )
    result["last_numeric"] = next(
        (row for row in reversed(rows) if row["policy_marker_difference_pp"] is not None), None
    )
    return result


def load_evidence(root: Path) -> dict[str, Any] | None:
    path = root / "evidence.json"
    if not path.exists():
        return None
    saved = json.loads(path.read_text(encoding="utf-8"))
    recomputed = audit_records(root, saved["captures"], method_version=saved["method_version"])
    if recomputed != saved:
        raise ValueError("Saved policy history does not reproduce")
    return recomputed


def capture_cohort(
    root: Path, specs: list[dict[str, str]], *, refresh: bool = False
) -> dict[str, Any]:
    if not 1 <= len(specs) <= 8:
        raise ValueError("Name one to eight currencies")
    urls = [policy_request_url(spec) for spec in specs]
    if len({spec["currency"] for spec in specs}) != len(specs):
        raise ValueError("Duplicate policy currency request")
    existing = load_evidence(root)
    records = (
        {item["request"]["currency"]: item for item in existing["captures"]} if existing else {}
    )
    for spec, _url in zip(specs, urls, strict=True):
        record = capture_policy_history(root, spec, refresh=refresh)
        records[spec["currency"]] = record
    result = audit_records(root, list(records.values()))
    atomic_json(root / "cohorts" / (uuid4().hex + ".json"), result)
    atomic_json(root / "evidence.json", result)
    return result
