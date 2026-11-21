"""Witnessed private-desk sources, with immutable captures and honest coverage.

Yahoo bars are a current reconstruction, not a point-in-time price archive.
FRED policy observations describe current conditions only; they must never be
joined to historical strategy labels as if their original availability were known.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import os
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
import yfinance as yf
from bs4 import BeautifulSoup

from src.private_desk.universe import PAIRS as PAIRS

_DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[3] / ".private-fx" / "sources"
_FEEDS = (
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_monetary.xml"),
    ("European Central Bank", "https://www.ecb.europa.eu/rss/press.html"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Reserve Bank of Australia", "https://www.rba.gov.au/rss/rss-cb-media-releases.xml"),
    ("Swiss National Bank", "https://www.snb.ch/public/rss/en/mopo"),
    ("Bank of Canada", "https://www.bankofcanada.ca/content_type/press-releases/feed/"),
    ("Bank of England", "https://www.bankofengland.co.uk/rss/news"),
    ("Bank of Japan", "https://www.boj.or.jp/en/rss/whatsnew.xml"),
)
_SERIES = {
    "usd_target_lower": ("DFEDTARL", "USD", "Federal Reserve target range lower bound"),
    "usd_target_upper": ("DFEDTARU", "USD", "Federal Reserve target range upper bound"),
    "eur_deposit_rate": ("ECBDFR", "EUR", "ECB deposit facility rate"),
}
_EXTRA_POLICY = {
    "gbp_bank_rate": (
        "GBP",
        "Bank of England official Bank Rate",
        "Bank of England",
        "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp",
        "boe",
    ),
    "aud_cash_rate_target": (
        "AUD",
        "RBA cash rate target",
        "Reserve Bank of Australia",
        "https://www.rba.gov.au/statistics/tables/csv/f1-data.csv",
        "rba",
    ),
    "nzd_ocr": (
        "NZD",
        "RBNZ Official Cash Rate",
        "Reserve Bank of New Zealand",
        "https://www.rbnz.govt.nz/monetary-policy",
        "rbnz",
    ),
    "cad_overnight_target": (
        "CAD",
        "Bank of Canada target for the overnight rate",
        "Bank of Canada",
        "https://www.bankofcanada.ca/valet/observations/V39079/json?recent=10",
        "boc",
    ),
    "chf_policy_rate": (
        "CHF",
        "SNB policy rate",
        "Swiss National Bank",
        "https://www.snb.ch/en/the-snb/mandates-goals/statistics/statistics-pub/"
        "current_interest_exchange_rates",
        "snb",
    ),
    "jpy_call_rate_guideline": (
        "JPY",
        "BoJ uncollateralized overnight call-rate guideline (around)",
        "Bank of Japan",
        "https://www.boj.or.jp/en/index.htm",
        "boj",
    ),
}


def _now() -> datetime:
    return datetime.now(UTC)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _capture(directory: Path, payload: dict[str, Any]) -> tuple[str, Path]:
    """A hash names one complete capture. An existing capture is never overwritten."""
    serialized = _canonical(payload)
    digest = hashlib.sha256(serialized).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{digest}.json"
    try:
        with target.open("xb") as handle:
            handle.write(serialized)
    except FileExistsError:
        if target.read_bytes() != serialized:
            raise ValueError("capture hash mismatch") from None
    return digest, target


def _write_pointer(path: Path, pointer: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(_canonical(pointer))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _failure(
    metadata: dict[str, Any], category: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # Exception text may contain URLs, headers or credentials. Return fixed categories only.
    return [], {**metadata, "status": "UNAVAILABLE", "errors": [category], "bar_count": 0}


def _validate_bars(
    rows: list[dict[str, Any]], interval: str, now: datetime
) -> tuple[list[dict[str, Any]], int]:
    completed: list[dict[str, Any]] = []
    previous: datetime | None = None
    omitted = 0
    for row in rows:
        stamp = datetime.fromisoformat(str(row["time"]).replace("Z", "+00:00"))
        stamp = stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC)
        if previous is not None and stamp <= previous:
            raise ValueError("unordered or duplicated timestamps")
        previous = stamp
        if stamp > now:
            raise ValueError("future timestamp")
        values = {key: float(row[key]) for key in ("open", "high", "low", "close")}
        if not all(math.isfinite(value) and value > 0 for value in values.values()):
            raise ValueError("nonfinite or nonpositive OHLC")
        if not (
            values["low"] <= min(values["open"], values["close"])
            and values["high"] >= max(values["open"], values["close"])
        ):
            raise ValueError("invalid OHLC envelope")
        # Daily Yahoo labels do not establish the FX session's close time. Only
        # dates before today are accepted. Hourly bars get a two-minute close cushion.
        incomplete = (
            stamp.date() >= now.date()
            if interval == "1d"
            else stamp + timedelta(hours=1, minutes=2) > now
        )
        if incomplete:
            omitted += 1
            continue
        clean = {"time": row["time"], **values}
        if "gap_before" in row:
            if not isinstance(row["gap_before"], bool):
                raise ValueError("invalid gap marker")
            clean["gap_before"] = row["gap_before"]
        if "hour_count" in row:
            clean["hour_count"] = row["hour_count"]
        completed.append(clean)
    return completed, omitted


def _download(pair: str, interval: str, start: str, now: datetime) -> list[dict[str, Any]]:
    requested = datetime.fromisoformat(start).replace(tzinfo=UTC)
    if interval == "1h":
        # Yahoo restricts hourly retention. Actual returned coverage remains the authority.
        requested = max(requested, now - timedelta(days=729))
    frame = yf.Ticker("JPY=X" if pair == "USDJPY" else f"{pair}=X").history(
        start=requested.date().isoformat(),
        interval=interval,
        auto_adjust=False,
        actions=False,
        timeout=12,
        raise_errors=True,
    )
    rows: list[dict[str, Any]] = []
    for stamp, row in frame.iterrows():
        raw_stamp = stamp.to_pydatetime()
        moment = (
            raw_stamp.replace(tzinfo=UTC) if raw_stamp.tzinfo is None else raw_stamp.astimezone(UTC)
        )
        rows.append(
            {
                # Preserve the provider's daily calendar label: converting midnight
                # in a positive-offset timezone to UTC shifts it to the prior day.
                "time": raw_stamp.date().isoformat() if interval == "1d" else moment.isoformat(),
                "provider_time": raw_stamp.isoformat(),
                **{key: float(row[key.title()]) for key in ("open", "high", "low", "close")},
            }
        )
    return rows


def _aggregate_hourly(
    rows: list[dict[str, Any]], now: datetime
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Complete FX sessions end at 17:00 New York, respecting daylight saving time."""
    new_york = ZoneInfo("America/New_York")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        stamp = datetime.fromisoformat(str(row["time"]))
        if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
            raise ValueError("hourly aggregation requires UTC")
        if stamp.minute or stamp.second or stamp.microsecond:
            raise ValueError("hourly bars must start on an exact hour")
        local = stamp.astimezone(new_york)
        label = local.date() + (timedelta(days=1) if local.hour >= 17 else timedelta(0))
        session_end = datetime.combine(label, datetime.min.time(), new_york).replace(hour=17)
        if label.weekday() >= 5 or session_end.astimezone(UTC) > now:
            continue
        grouped.setdefault(label.isoformat(), []).append(row)
    complete: list[dict[str, Any]] = []
    incomplete: list[str] = []
    for date, day in sorted(grouped.items()):
        session_end = datetime.fromisoformat(date).replace(tzinfo=new_york, hour=17)
        session_start = (session_end - timedelta(days=1)).astimezone(UTC)
        expected = [session_start + timedelta(hours=index) for index in range(24)]
        actual = [datetime.fromisoformat(str(row["time"])) for row in day]
        if len(day) != 24 or actual != expected:
            incomplete.append(date)
            continue
        complete.append(
            {
                "time": date,
                "open": day[0]["open"],
                "high": max(row["high"] for row in day),
                "low": min(row["low"] for row in day),
                "close": day[-1]["close"],
                "hour_count": 24,
            }
        )
    missing: list[str] = []
    if complete:
        dates = {row["time"] for row in complete}
        cursor = datetime.fromisoformat(str(complete[0]["time"]))
        end = datetime.fromisoformat(str(complete[-1]["time"]))
        while cursor <= end:
            if cursor.weekday() < 5 and cursor.date().isoformat() not in dates:
                missing.append(cursor.date().isoformat())
            cursor += timedelta(days=1)
        previous: datetime | None = None
        for row in complete:
            stamp = datetime.fromisoformat(str(row["time"]))
            next_weekday = None if previous is None else previous + timedelta(days=1)
            while next_weekday is not None and next_weekday.weekday() >= 5:
                next_weekday += timedelta(days=1)
            row["gap_before"] = next_weekday is not None and stamp != next_weekday
            previous = stamp
    return complete, {
        "aggregation": "24 hourly candles per complete FX session ending 17:00 New York",
        "session_timezone": "America/New_York",
        "incomplete_days_omitted": incomplete,
        "missing_weekdays": missing,
        "gap_count": len(missing),
        "gap_policy": "Reject feature and holding windows crossing gap_before.",
    }


def _reference_rows(payload: dict[str, Any], pair: str, end: str) -> list[dict[str, Any]]:
    if payload.get("base") != "EUR" or payload.get("amount") != 1:
        raise ValueError("unexpected reference base or amount")
    rows: list[dict[str, Any]] = []
    base, quote = pair[:3], pair[3:]
    previous: datetime | None = None
    for date, rates in sorted(payload["rates"].items()):
        stamp = datetime.fromisoformat(date)
        if stamp.date().isoformat() > end or stamp.weekday() >= 5:
            raise ValueError("future or weekend reference observation")
        if previous is not None and stamp <= previous:
            raise ValueError("duplicate reference timestamp")
        previous = stamp
        legs = {"EUR": 1.0, **rates}
        values = [float(legs[currency]) for currency in (base, quote)]
        if not all(math.isfinite(value) and value > 0 for value in values):
            raise ValueError("invalid reference currency leg")
        rows.append({"time": date, "close": values[1] / values[0]})
    if not rows:
        raise ValueError("empty reference observations")
    return rows


def load_reference_history(
    pair: str, *, cache_dir: Path, refresh: bool = False
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """ECB daily fixes via Frankfurter, for direction research only, with no OHLC."""
    now = _now()
    end = (now - timedelta(days=1)).date().isoformat()
    url = f"https://api.frankfurter.dev/v1/1999-01-04..{end}?base=EUR&symbols=USD,GBP,AUD,NZD,CAD,CHF,JPY"
    metadata: dict[str, Any] = {
        "pair": pair,
        "source": "ECB reference exchange rates via Frankfurter",
        "source_url": url,
        "official_source_url": "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/"
        "euro_reference_exchange_rates/html/index.en.html",
        "interval": "1d_reference_fix",
        "received_at": now.isoformat(),
        "retrieved_at": now.isoformat(),
        "published_at": None,
        "point_in_time": False,
        "research_status": "REFERENCE_DIRECTION_ONLY",
        "executable_ohlc": False,
        "derivation": "quote_currency_per_EUR / base_currency_per_EUR from the same daily fix",
        "warnings": [
            "Reference fixes are indicative; no intraday path or executable stop/target prices.",
            "Current archive reconstruction; original publication availability is unknown.",
        ],
        "errors": [],
        "from_cache": False,
    }
    if pair not in PAIRS:
        return _failure(metadata, "unsupported_pair")
    directory = cache_dir / "reference"
    pointer = directory / "latest.json"
    try:
        if pointer.exists() and not refresh:
            digest = json.loads(pointer.read_text("utf-8"))["sha256"]
            if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("invalid reference digest")
            path = directory / f"{digest}.json"
            serialized = path.read_bytes()
            if hashlib.sha256(serialized).hexdigest() != digest:
                raise ValueError("reference capture integrity failed")
            capture = json.loads(serialized)
            payload = capture["raw_json"]
            metadata.update(
                {
                    "from_cache": True,
                    "received_at": capture["received_at"],
                    "retrieved_at": capture["received_at"],
                    "source_url": capture["source_url"],
                }
            )
        else:
            raw = _get_text(url)
            payload = json.loads(raw)
            # Validate all private derivations before accepting the shared capture.
            for member in PAIRS:
                _reference_rows(payload, member, end)
            digest, path = _capture(
                directory,
                {
                    "schema_version": "private-reference-v1",
                    "source_url": url,
                    "received_at": now.isoformat(),
                    "raw_json": payload,
                },
            )
            _write_pointer(pointer, {"sha256": digest})
        rows = _reference_rows(payload, pair, end)
        metadata.update(
            {
                "status": "AVAILABLE",
                "first_bar": rows[0]["time"],
                "last_bar": rows[-1]["time"],
                "bar_count": len(rows),
                "sha256": digest,
                "capture_path": str(path),
                "stale": (now.date() - datetime.fromisoformat(rows[-1]["time"]).date()).days > 7,
                "coverage_years": round(
                    (
                        datetime.fromisoformat(rows[-1]["time"])
                        - datetime.fromisoformat(rows[0]["time"])
                    ).days
                    / 365.25,
                    2,
                ),
            }
        )
        return rows, metadata
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return _failure(metadata, "reference_source_or_integrity_unavailable")


def _safe_raw(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _safe_raw(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_raw(item) for item in value]
    return value


def _rejected_capture(
    rows: list[dict[str, Any]], metadata: dict[str, Any], directory: Path
) -> dict[str, Any]:
    digest, path = _capture(
        directory,
        {
            "schema_version": "private-rejected-source-v1",
            "validation_status": "REJECTED",
            "reason": "invalid_provider_bars",
            "raw_bars": _safe_raw(rows),
            "metadata": metadata,
        },
    )
    return {
        "rejected_capture_sha256": digest,
        "rejected_capture_path": str(path),
        "rejected_raw_first_bar": rows[0]["time"],
        "rejected_raw_last_bar": rows[-1]["time"],
        "rejected_raw_bar_count": len(rows),
    }


def _quarantine_daily(
    rows: list[dict[str, Any]], now: datetime
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Keep unchanged valid prices and mark gaps; broken date identity fails closed."""
    valid: list[dict[str, Any]] = []
    invalid_dates: list[str] = []
    previous: datetime | None = None
    incomplete = 0
    for row in rows:
        date = str(row["time"])
        stamp = datetime.fromisoformat(date).replace(tzinfo=UTC)
        if len(date) != 10 or stamp > now or (previous is not None and stamp <= previous):
            raise ValueError("unusable daily date identity")
        previous = stamp
        if stamp.date() >= now.date():
            incomplete += 1
            continue
        if stamp.weekday() >= 5:
            invalid_dates.append(date)
            continue
        try:
            completed, _ = _validate_bars([row], "1d", now)
        except (ValueError, KeyError, TypeError, OverflowError):
            invalid_dates.append(date)
            continue
        valid.extend(completed)
    if not valid:
        raise ValueError("no valid daily observations")
    missing: list[str] = []
    previous = None
    for row in valid:
        stamp = datetime.fromisoformat(str(row["time"]))
        expected: datetime | None = None if previous is None else previous + timedelta(days=1)
        gap = False
        while expected is not None and expected < stamp:
            if expected.weekday() < 5:
                missing.append(expected.date().isoformat())
                gap = True
            expected += timedelta(days=1)
        row["gap_before"] = gap
        previous = stamp
    return valid, {
        "research_status": "PROVISIONAL_QUARANTINED",
        "source_status": "PROVISIONAL_QUARANTINED",
        "invalid_row_count": len(invalid_dates),
        "invalid_dates": invalid_dates,
        "incomplete_bars_omitted": incomplete,
        "missing_weekdays": missing,
        "gap_count": len(missing),
        "gap_policy": "Reject every feature, label and holding window crossing gap_before.",
        "quarantine_policy": (
            "Original valid OHLC retained; invalid rows omitted; no repaired prices."
        ),
    }


def _stooq_bars(pair: str, start: str) -> tuple[list[dict[str, Any]], str]:
    # Euro-era observations only: no assumed pre-1999 synthetic euro prices.
    since = max(start, "1999-01-04") if "EUR" in pair else start
    url = f"https://stooq.com/q/d/l/?s={pair.lower()}&i=d&d1={since.replace('-', '')}"
    raw = _get_text(url)
    rows = [
        {
            "time": row["Date"],
            **{key: float(row[key.title()]) for key in ("open", "high", "low", "close")},
        }
        for row in csv.DictReader(io.StringIO(raw))
    ]
    if not rows:
        raise ValueError("Stooq unavailable")
    return rows, url


def _daily_fallback(
    pair: str,
    start: str,
    cache_dir: Path,
    refresh: bool,
    metadata: dict[str, Any],
    directory: Path,
    now: datetime,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    warnings = [
        *metadata["warnings"],
        "Primary daily history failed OHLC validation or availability.",
    ]
    try:
        rows, url = _stooq_bars(pair, start)
        bars, omitted = _validate_bars(rows, "1d", now)
        if not bars:
            raise ValueError("empty Stooq completed history")
        metadata.update(
            {
                "source": "Stooq daily prices",
                "source_url": url,
                "incomplete_bars_omitted": omitted,
                "warnings": [*warnings, "Stooq prices are provider quotes, not broker fills."],
            }
        )
        raw_capture = {"raw_bars": rows}
    except (ValueError, KeyError, TypeError, OverflowError, OSError):
        hourly, hourly_meta = load_history(
            pair, interval="1h", start=start, cache_dir=cache_dir, refresh=refresh
        )
        if not hourly or hourly_meta["status"] != "AVAILABLE":
            metadata["warnings"] = [*warnings, "Stooq and hourly fallback are unavailable."]
            return _failure(metadata, "all_ohlc_sources_unavailable")
        bars, aggregation = _aggregate_hourly(hourly, now)
        if not bars:
            metadata["warnings"] = [*warnings, "No complete New York FX session aggregates."]
            return _failure(metadata, "no_complete_daily_aggregates")
        metadata.update(
            {
                "source": "Yahoo hourly candles aggregated to complete New York FX sessions",
                "source_url": hourly_meta["source_url"],
                "hourly_capture_sha256": hourly_meta["sha256"],
                "hourly_capture_path": hourly_meta["capture_path"],
                **aggregation,
                "warnings": [
                    *warnings,
                    "Stooq daily endpoint unavailable.",
                    "Only complete FX sessions; gaps must be excluded from backtest windows.",
                    "Actual hourly retention limits this cohort to roughly two years.",
                ],
            }
        )
        raw_capture = {
            "hourly_capture_sha256": hourly_meta["sha256"],
            "hourly_capture_path": hourly_meta["capture_path"],
        }
    metadata.update(
        {
            "status": "AVAILABLE",
            "first_bar": bars[0]["time"],
            "last_bar": bars[-1]["time"],
            "bar_count": len(bars),
            "stale": (now.date() - datetime.fromisoformat(bars[-1]["time"]).date()).days > 4,
            "coverage_years": round(
                (
                    datetime.fromisoformat(bars[-1]["time"])
                    - datetime.fromisoformat(bars[0]["time"])
                ).days
                / 365.25,
                2,
            ),
        }
    )
    digest, path = _capture(
        directory,
        {
            "schema_version": "private-source-v1",
            "pair": pair,
            "interval": "1d",
            "requested_start": start,
            "bars": bars,
            "metadata": metadata,
            **raw_capture,
        },
    )
    _write_pointer(directory / "latest.json", {"sha256": digest})
    return bars, {**metadata, "sha256": digest, "capture_path": str(path), "cache_age_hours": 0}


def load_history(
    pair: str,
    *,
    interval: str = "1d",
    start: str = "1997-01-01",
    cache_dir: Path,
    refresh: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load an audited capture, or acquire real provider bars without inventing coverage."""
    now = _now()
    symbol = "JPY=X" if pair == "USDJPY" else f"{pair}=X"
    metadata: dict[str, Any] = {
        "pair": pair,
        "interval": interval,
        "requested_start": start,
        "source": "Yahoo Finance via yfinance",
        "source_url": f"https://finance.yahoo.com/quote/{symbol.replace('=', '%3D')}/history/",
        "provider_symbol": symbol,
        "received_at": now.isoformat(),
        "retrieved_at": now.isoformat(),
        "first_bar": None,
        "last_bar": None,
        "bar_count": 0,
        "research_status": "PROVISIONAL_RECONSTRUCTED",
        "point_in_time": False,
        "from_cache": False,
        "errors": [],
        "warnings": [
            "Current provider reconstruction; original publication times are unavailable."
        ],
    }
    if pair not in PAIRS or interval not in ("1d", "1h"):
        return _failure(metadata, "unsupported_pair_or_interval")
    try:
        requested = datetime.fromisoformat(start)
        if requested.date() >= now.date():
            return _failure(metadata, "invalid_start_date")
    except ValueError:
        return _failure(metadata, "invalid_start_date")
    directory = cache_dir / "history" / pair / interval
    pointer = directory / "latest.json"
    if pointer.exists() and not refresh:
        try:
            digest = json.loads(pointer.read_text("utf-8"))["sha256"]
            if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("invalid digest")
            path = directory / f"{digest}.json"
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("capture tampered")
            payload = json.loads(raw)
            if payload["pair"] != pair or payload["interval"] != interval:
                raise ValueError("capture identity mismatch")
            if payload["requested_start"] != start:
                # Different requested coverage warrants a new acquisition.
                return load_history(
                    pair, interval=interval, start=start, cache_dir=cache_dir, refresh=True
                )
            bars, _ = _validate_bars(payload["bars"], interval, now)
            received = datetime.fromisoformat(payload["metadata"]["received_at"])
            age = (now - received).total_seconds() / 3600
            if age < 0:
                raise ValueError("future capture")
            return bars, {
                **payload["metadata"],
                "from_cache": True,
                "sha256": digest,
                "capture_path": str(path),
                "cache_age_hours": round(age, 2),
                "stale": bool(payload["metadata"].get("stale"))
                or age > (36 if interval == "1d" else 2),
            }
        except (OSError, ValueError, KeyError, TypeError):
            return _failure(metadata, "cache_integrity_failure")
    rows: list[dict[str, Any]] | None = None
    for _attempt in range(2):
        try:
            rows = _download(pair, interval, start, now)
            break
        except Exception:
            # yfinance has provider-specific exceptions beyond requests' hierarchy.
            continue
    if rows is None or not rows:
        if interval == "1d":
            try:
                return _daily_fallback(pair, start, cache_dir, refresh, metadata, directory, now)
            except (ValueError, OSError):
                return _failure(metadata, "daily_fallback_unavailable")
        return _failure(metadata, "provider_history_unavailable")
    try:
        if interval == "1d":
            bars, quality = _quarantine_daily(rows, now)
            metadata.update(quality)
            omitted = quality["incomplete_bars_omitted"]
            if quality["invalid_row_count"]:
                metadata.update(_rejected_capture(rows, metadata, directory))
                metadata["warnings"].append(
                    "Malformed daily OHLC rows quarantined; windows crossing gaps must be excluded."
                )
        else:
            bars, omitted = _validate_bars(rows, interval, now)
        if not bars:
            return _failure(metadata, "no_completed_bars")
        metadata.update(
            {
                "status": "AVAILABLE",
                "first_bar": bars[0]["time"],
                "last_bar": bars[-1]["time"],
                "bar_count": len(bars),
                "incomplete_bars_omitted": omitted,
                "stale": (now.date() - datetime.fromisoformat(str(bars[-1]["time"])).date()).days
                > 4,
                "coverage_years": round(
                    (
                        datetime.fromisoformat(str(bars[-1]["time"]))
                        - datetime.fromisoformat(str(bars[0]["time"]))
                    ).total_seconds()
                    / (86400 * 365.25),
                    2,
                ),
            }
        )
        payload = {
            "schema_version": "private-source-v1",
            "pair": pair,
            "interval": interval,
            "requested_start": start,
            "raw_bars": _safe_raw(rows),
            "bars": bars,
            "metadata": metadata,
        }
        digest, path = _capture(directory, payload)
        _write_pointer(pointer, {"sha256": digest})
        return bars, {**metadata, "sha256": digest, "capture_path": str(path), "cache_age_hours": 0}
    except (ValueError, KeyError, TypeError, OverflowError):
        try:
            metadata.update(_rejected_capture(rows, metadata, directory))
            if interval == "1d":
                return _daily_fallback(pair, start, cache_dir, refresh, metadata, directory, now)
        except (ValueError, OSError):
            return _failure(metadata, "daily_fallback_or_storage_failure")
        return _failure(metadata, "invalid_provider_bars")
    except OSError:
        return _failure(metadata, "capture_storage_failure")


def _get_text(url: str) -> str:
    # RBA's public data endpoints accept requests' standard client identifier,
    # but reject this application's custom identifier in the witnessed probe.
    host = urlparse(url).hostname or ""
    agent = (
        requests.utils.default_user_agent()
        if host == "www.rba.gov.au"
        else "FXResearchLab-PrivateResearch/1.0"
    )
    for attempt in range(2):
        try:
            response = requests.get(
                url,
                timeout=(5, 12),
                headers={
                    "User-Agent": agent,
                },
            )
            response.raise_for_status()
            if len(response.content) > 2_000_000:
                raise ValueError("source exceeds capture limit")
            # Fed RSS is UTF-8 with a BOM but omits its HTTP charset; requests
            # otherwise assumes Latin-1 and corrupts the XML before parsing it.
            return response.content.decode("utf-8-sig")
        except requests.RequestException:
            if attempt == 1:
                raise ValueError("source request unavailable") from None
    raise ValueError("source unavailable")


def _published(value: str) -> str | None:
    try:
        stamp = parsedate_to_datetime(value)
    except (ValueError, TypeError):
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if stamp.tzinfo is None:
        return None  # A timezone must be witnessed, never guessed.
    return stamp.astimezone(UTC).isoformat()


def _parse_boj_feed(text: str, received: datetime) -> list[dict[str, Any]]:
    """Retain original BOJ links; HTTPS display transport does not fetch an article."""
    from src.private_desk.boj_current import FEED_URL

    if (
        len(text.encode("utf-8")) > 256 * 1024
        or re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I)
    ):
        raise ValueError("BOJ feed size or entity declaration rejected")
    root = ET.fromstring(text)
    channel = root.find("channel")
    if root.tag != "rss" or root.attrib.get("version") != "2.0" or channel is None:
        raise ValueError("Unsupported BOJ RSS structure")
    links = channel.findall("{http://www.w3.org/2005/Atom}link")
    if len(links) != 1 or links[0].get("rel") != "self":
        raise ValueError("Missing BOJ feed identity")
    identity = urlparse(links[0].get("href", ""))
    if (
        identity.scheme not in ("http", "https") or identity.netloc != "www.boj.or.jp"
        or identity.path != urlparse(FEED_URL).path
    ):
        raise ValueError("BOJ feed identity mismatch")
    entries = channel.findall("item")
    if len(entries) > 100:
        raise ValueError("BOJ feed item bound exceeded")
    seen: dict[str, tuple[str, str]] = {}
    items: list[dict[str, Any]] = []
    for entry in entries:
        values = {child.tag: child.text or "" for child in entry}
        title = " ".join(html.unescape(re.sub(r"<[^>]*>", "", values.get("title", ""))).split())
        original = values.get("link", "").strip()
        link = urlparse(original)
        date = values.get("pubDate", "").strip()
        if (
            not title or len(title) > 500 or link.scheme not in ("http", "https")
            or link.netloc != "www.boj.or.jp" or not link.path.startswith("/en/")
            or values.get("guid", "").strip() != original
            or not re.search(r"[+-]\d{4}$", date)
        ):
            continue
        published = _published(date)
        if published is None or datetime.fromisoformat(published) > received:
            continue
        canonical = link._replace(scheme="https").geturl()
        if canonical in seen:
            if seen[canonical] != (title, published):
                raise ValueError("Conflicting BOJ headline duplicates")
            continue
        seen[canonical] = (title, published)
        items.append({
            "title": title, "url": canonical, "original_url": original,
            "source": "Bank of Japan", "published_at": published,
            "retrieved_at": received.isoformat(), "content_scope": "attributed_headline_only",
            "link_transport": "HTTPS_SAME_HOST_LINK; ARTICLE_NOT_FETCHED",
            "source_publication_clock": date,
            "coverage_scope": "GENERAL_WHATS_NEW; POLICY_DECISION_COMPLETENESS_UNKNOWN",
        })
    return items


def _parse_feed(text: str, source: str, received: datetime) -> list[dict[str, Any]]:
    if source == "Bank of Japan":
        return _parse_boj_feed(text, received)
    root = ET.fromstring(text)
    entries = [entry for entry in root.iter() if entry.tag.split("}")[-1] in ("item", "entry")]
    items: list[dict[str, Any]] = []
    for entry in entries[:20]:
        values = {child.tag.split("}")[-1]: child.text or "" for child in entry}
        title = " ".join(html.unescape(re.sub(r"<[^>]*>", "", values.get("title", ""))).split())
        url = values.get("link", "")
        if not url:
            link = entry.find("{http://www.w3.org/2005/Atom}link")
            url = "" if link is None else link.attrib.get("href", "")
        parsed_url = urlparse(url)
        allowed = (
            "federalreserve.gov",
            "ecb.europa.eu",
            "bbc.co.uk",
            "bbc.com",
            "bankofengland.co.uk",
            "rba.gov.au",
            "rbnz.govt.nz",
            "bankofcanada.ca",
            "snb.ch",
        )
        host = parsed_url.hostname or ""
        if parsed_url.scheme not in ("https", "http") or not any(
            host == domain or host.endswith(f".{domain}") for domain in allowed
        ):
            continue
        published = _published(
            values.get("pubDate")
            or values.get("published")
            or values.get("date")
            or values.get("updated")
            or ""
        )
        if not title or published is None or datetime.fromisoformat(published) > received:
            continue
        items.append(
            {
                "title": title[:500],
                "url": url,
                "source": source,
                "published_at": published,
                "retrieved_at": received.isoformat(),
                "content_scope": "attributed_headline_only",
            }
        )
    return items


def fetch_news() -> list[dict[str, Any]]:
    """Return dated publisher headlines; unavailable feeds add no invented entries."""
    collected: dict[str, dict[str, Any]] = {}
    for source, url in _FEEDS:
        try:
            transport: dict[str, Any] = {}
            if source == "Bank of Japan":
                from src.private_desk.boj_current import capture_source

                raw, transport = capture_source(
                    _DEFAULT_CACHE_DIR / "news" / "boj", url, clock=_now
                )
                received = datetime.fromisoformat(transport["received_at"])
            else:
                raw = _get_text(url)
                received = _now()
            records = _parse_feed(raw, source, received)
            digest, path = _capture(
                _DEFAULT_CACHE_DIR / "news",
                {
                    "source": source,
                    "source_url": url,
                    "received_at": received.isoformat(),
                    "raw_feed": raw,
                    "records": records,
                    "point_in_time": False,
                    "research_status": "CURRENT_DESCRIPTIVE_ONLY",
                    **transport,
                },
            )
            for item in records:
                collected[item["url"]] = {
                    **item,
                    "source_url": url,
                    "sha256": digest,
                    "capture_path": str(path),
                    **transport,
                }
        except (ValueError, UnicodeError, ET.ParseError, OSError):
            continue
    return sorted(collected.values(), key=lambda item: str(item["published_at"]), reverse=True)


def _latest_policy(csv_text: str, series: str, now: datetime) -> tuple[str, float]:
    rows = csv.DictReader(io.StringIO(csv_text))
    observations: list[tuple[str, float]] = []
    for row in rows:
        date = row.get("observation_date") or row.get("DATE") or ""
        value = row.get(series, "")
        try:
            stamp = datetime.fromisoformat(date)
            number = float(value)
        except (ValueError, TypeError):
            continue
        if stamp.date() > now.date() or not math.isfinite(number):
            continue
        observations.append((date, number))
    if not observations:
        raise ValueError("no witnessed policy values")
    return max(observations, key=lambda observation: observation[0])


def _plain_text(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    for element in soup(("script", "style")):
        element.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def _finite_policy(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite policy rate")
    return number


def _rba_policy(raw: str, now: datetime) -> dict[str, Any]:
    rows = list(csv.reader(io.StringIO(raw)))
    titles = next(row for row in rows if row and row[0] == "Title")
    # Explicit target column, never the independently supplied interbank cash rate.
    column = titles.index("Cash Rate Target")
    observations = []
    for row in rows:
        try:
            date = datetime.strptime(row[0], "%d-%b-%Y").date()
            value = _finite_policy(row[column])
        except (ValueError, IndexError):
            continue
        if date <= now.date():
            observations.append((date.isoformat(), value))
    if not observations:
        raise ValueError("no RBA target observations")
    observed_date, value = max(observations)
    return {
        "value": value,
        "observation_date": observed_date,
        "date_role": "daily_policy_target_observation",
    }


def _boc_policy(raw: str, now: datetime) -> dict[str, Any]:
    payload = json.loads(raw)
    label = payload["seriesDetail"]["V39079"]["label"].lower()
    if "target for the overnight rate" not in label:
        raise ValueError("unverified Bank of Canada policy target")
    observations = []
    for row in payload["observations"]:
        date = datetime.fromisoformat(row["d"]).date()
        value = _finite_policy(row["V39079"]["v"])
        if date <= now.date():
            observations.append((date.isoformat(), value))
    if not observations:
        raise ValueError("no Bank of Canada target observations")
    observed_date, value = max(observations)
    return {
        "value": value,
        "observation_date": observed_date,
        "date_role": "daily_policy_target_observation",
        "series_id": "V39079",
    }


def _boe_policy(raw: str, now: datetime) -> dict[str, Any]:
    text = _plain_text(raw)
    current = re.search(r"Current official Bank Rate\s+([-+]?\d+(?:\.\d+)?)\s*%", text)
    changed = re.search(r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{2})\s*\|?\s*([-+]?\d+(?:\.\d+)?)", text)
    if current is None or changed is None:
        raise ValueError("missing official current Bank Rate or change date")
    value = _finite_policy(current.group(1))
    effective = datetime.strptime(changed.group(1), "%d %b %y").date()
    if effective > now.date() or value != _finite_policy(changed.group(2)):
        raise ValueError("conflicting Bank Rate assertion and change table")
    return {
        "value": value,
        "observation_date": now.date().isoformat(),
        "effective_from": effective.isoformat(),
        "date_role": "current_page_observed_on",
    }


def _rbnz_policy(raw: str, now: datetime) -> dict[str, Any]:
    text = _plain_text(raw)
    current = re.search(
        r"Official Cash Rate\s+([-+]?\d+(?:\.\d+)?)\s*%\s+Updated:\s*"
        r"([^,]+),\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
        text,
    )
    if current is None:
        raise ValueError("missing RBNZ Official Cash Rate card")
    updated = datetime.strptime(current.group(3), "%d %b %Y").date()
    if updated > now.date():
        raise ValueError("future RBNZ policy update")
    result: dict[str, Any] = {
        "value": _finite_policy(current.group(1)),
        "observation_date": now.date().isoformat(),
        "policy_updated_date": updated.isoformat(),
        "date_role": "current_page_observed_on",
        "reported_update_local_time": current.group(2),
        "publication_timing": "UNKNOWN: update clock lacks an explicit timezone",
    }
    next_update = re.search(
        r"Next update:\s*[^,]+,\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
        text[current.end() : current.end() + 180],
    )
    if next_update is not None:
        next_date = datetime.strptime(next_update.group(1), "%d %b %Y").date()
        result["next_policy_update_date"] = next_date.isoformat()
        if next_date <= now.date():
            result["status"] = "STALE"
    return result


def _snb_policy(raw: str, now: datetime) -> dict[str, Any]:
    text = _plain_text(raw)
    current = re.search(
        r"SNB policy rate\s+([-+]?\d+(?:\.\d+)?)\s*%\s+valid from\s*"
        r"(\d{2}\.\d{2}\.\d{4})",
        text,
    )
    if current is None:
        raise ValueError("missing SNB policy rate assertion")
    effective = datetime.strptime(current.group(2), "%d.%m.%Y").date()
    if effective > now.date():
        raise ValueError("future SNB policy effective date")
    return {
        "value": _finite_policy(current.group(1)),
        "observation_date": now.date().isoformat(),
        "effective_from": effective.isoformat(),
        "date_role": "current_page_observed_on",
    }


def _boj_policy(raw: str, now: datetime) -> dict[str, Any]:
    soup = BeautifulSoup(raw, "html.parser")
    for node in soup(("script", "style")):
        node.decompose()
    headings = [
        node for node in soup.find_all(["h2", "h3", "h4"])
        if node.get_text(strip=True) == "Guideline"
    ]
    if len(headings) != 1:
        raise ValueError("Missing or duplicate BOJ guideline heading")
    heading = headings[0]
    section = heading.find_parent("section", class_="policy")
    if section is None:
        raise ValueError("Missing BOJ guideline section")
    anchors = section.find_all("a")
    assertions = [
        node for node in soup.find_all("a")
        if " ".join(node.get_text(" ", strip=True).split()).startswith(
            "The Bank will encourage the uncollateralized overnight call rate"
        )
    ]
    if len(anchors) != 1 or len(assertions) != 1 or assertions[0] is not anchors[0]:
        raise ValueError("Missing or duplicate BOJ guideline assertion")
    anchor = anchors[0]
    href_value = anchor.get("href", "")
    if not isinstance(href_value, str):
        raise ValueError("Invalid BOJ guideline link")
    link = urlparse(href_value)
    if link.scheme or link.netloc:
        if link.scheme != "https" or link.netloc != "www.boj.or.jp":
            raise ValueError("Invalid BOJ guideline source link")
    if not re.fullmatch(r"/en/mopo/mpmdeci/state_\d{4}/index\.htm", link.path):
        raise ValueError("Unsupported BOJ guideline source path")
    text = " ".join(anchor.get_text(" ", strip=True).split())
    match = re.fullmatch(
        r"The Bank will encourage the uncollateralized overnight call rate to remain at around "
        r"([-+]?\d+(?:\.\d+)?) percent\.", text,
    )
    if match is None:
        raise ValueError("Unsupported BOJ point guideline")
    return {
        "value": _finite_policy(match.group(1)), "observation_date": now.date().isoformat(),
        "date_role": "current_page_observed_on", "current_page_observed_at": now.isoformat(),
        "policy_instrument": "BOJ_OVERNIGHT_CALL_RATE_GUIDELINE",
        "policy_target_qualifier": "around", "effective_from": None,
        "decision_date": None, "guideline_assertion": text,
        "source_warning": (
            "Current homepage guideline; decision/effective/publication clocks are not inferred."
        ),
    }


def _extra_policy_sources(cache_dir: Path, now: datetime) -> dict[str, Any]:
    parsers = {
        "rba": _rba_policy,
        "boc": _boc_policy,
        "boe": _boe_policy,
        "rbnz": _rbnz_policy,
        "snb": _snb_policy,
        "boj": _boj_policy,
    }
    result: dict[str, Any] = {}
    for key, (currency, label, source, url, parser) in _EXTRA_POLICY.items():
        indicator: dict[str, Any] = {
            "currency": currency,
            "label": label,
            "source": source,
            "source_url": url,
            "download_url": url,
            "retrieved_at": now.isoformat(),
            "published_at": None,
            "publication_timing": "UNKNOWN: no witnessed announcement timestamp",
            "point_in_time": False,
            "unit": "percent",
            "transport": "DIRECT_OFFICIAL_SOURCE",
        }
        try:
            try:
                if parser == "boj":
                    from src.private_desk.boj_current import capture_source

                    raw, transport = capture_source(
                        cache_dir / "fundamentals" / "boj", url, clock=_now
                    )
                    indicator.update(transport)
                    indicator["retrieved_at"] = transport["received_at"]
                else:
                    raw = _get_text(url)
            except ValueError:
                if parser not in ("boe", "rbnz"):
                    raise
                reader = f"https://r.jina.ai/{url}"
                raw = _get_text(reader)
                if f"URL Source: {url}" not in raw:
                    raise ValueError("reader source identity mismatch")
                indicator.update(
                    {
                        "download_url": reader,
                        "transport": "PUBLIC_READER_OF_OFFICIAL_PAGE",
                        "source_warning": "Direct source unavailable; public reader used.",
                    }
                )
            observed = datetime.fromisoformat(indicator["retrieved_at"])
            parsed = parsers[parser](raw, observed)
            indicator.update(parsed)
            age = (now.date() - datetime.fromisoformat(parsed["observation_date"]).date()).days
            indicator.update(
                {
                    "observation_age_days": age,
                    "status": parsed.get("status", "AVAILABLE" if age <= 10 else "STALE"),
                }
            )
            digest, path = _capture(
                cache_dir / "fundamentals",
                {"raw_source": raw, "indicator": indicator, "received_at": now.isoformat()},
            )
            indicator.update({"sha256": digest, "capture_path": str(path)})
        except (ValueError, UnicodeError, KeyError, TypeError, IndexError, StopIteration, OSError):
            indicator.update(
                {
                    "value": None,
                    "observation_date": None,
                    "status": "UNAVAILABLE",
                    "error": "official_policy_source_or_parser_unavailable",
                }
            )
        result[key] = indicator
    return result


def fetch_fundamentals(cache_dir: Path) -> dict[str, Any]:
    """Witnessed current policy targets for all currencies; other macro gaps stay explicit."""
    now = _now()
    indicators: dict[str, Any] = {}
    for key, (series, currency, label) in _SERIES.items():
        since = (now - timedelta(days=90)).date().isoformat()
        url = f"https://fred.stlouisfed.org/graph/?g=1&id={series}&cosd={since}"
        csv_url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={since}"
        indicator: dict[str, Any] = {
            "label": label,
            "currency": currency,
            "series_id": series,
            "source": "Federal Reserve via FRED" if currency == "USD" else "ECB via FRED",
            "source_url": f"https://fred.stlouisfed.org/series/{series}",
            "download_url": csv_url,
            "chart_url": url,
            "retrieved_at": now.isoformat(),
            "published_at": None,
            "publication_timing": "UNKNOWN: CSV observation date is not publication time",
            "point_in_time": False,
            "unit": "percent",
        }
        try:
            raw = _get_text(csv_url)
            date, value = _latest_policy(raw, series, now)
            age = (now.date() - datetime.fromisoformat(date).date()).days
            indicator.update(
                {
                    "value": value,
                    "observation_date": date,
                    "status": "AVAILABLE" if age <= 10 else "STALE",
                    "observation_age_days": age,
                }
            )
            digest, path = _capture(
                cache_dir / "fundamentals",
                {
                    "raw_csv": raw,
                    "indicator": indicator,
                    "received_at": now.isoformat(),
                },
            )
            indicator.update({"sha256": digest, "capture_path": str(path)})
        except (ValueError, OSError):
            indicator.update(
                {
                    "value": None,
                    "observation_date": None,
                    "status": "UNAVAILABLE",
                    "error": "policy_source_unavailable",
                }
            )
        indicators[key] = indicator
    indicators.update(_extra_policy_sources(cache_dir, now))
    required = {
        "USD": ("usd_target_lower", "usd_target_upper"),
        "EUR": ("eur_deposit_rate",),
        **{values[0]: (key,) for key, values in _EXTRA_POLICY.items()},
    }
    missing = [
        currency
        for currency, keys in required.items()
        if not keys or any(indicators[key]["status"] != "AVAILABLE" for key in keys)
    ]
    warnings = [
        "These current-vintage values are excluded from historical backtests.",
        "Growth, inflation surprises, positioning and dated event calendar are unavailable.",
        "RBNZ RSS is not configured; other news feeds depend on provider access.",
        "BoJ general headlines are incomplete policy coverage; "
        "an absent item does not mean unchanged policy.",
    ]
    if missing:
        warnings.append(
            "Some policy legs are unavailable or stale; full pair comparisons are incomplete."
        )
    if any(
        item.get("transport") == "PUBLIC_READER_OF_OFFICIAL_PAGE" for item in indicators.values()
    ):
        warnings.append(
            "Official page transport through a public reader is recorded in source metadata."
        )
    return {
        "as_of": now.isoformat(),
        "status": "PARTIAL",
        "research_status": "CURRENT_DESCRIPTIVE_ONLY",
        "indicators": indicators,
        "policy_status": "COMPLETE" if not missing else "PARTIAL",
        "missing_currencies": missing,
        "warnings": warnings,
    }
