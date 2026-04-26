"""Macro release calendar from FRED release dates with static fallback."""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any, cast

import requests

from src.types import PAIRS

logger = logging.getLogger(__name__)

_HIGH_MAP: dict[str, tuple[list[str], str, str]] = {
    "Unemployment Rate": (list(PAIRS), "HIGH", "US"),
    "Federal Funds Rate": (list(PAIRS), "HIGH", "US"),
    "Consumer Price Index": (list(PAIRS), "HIGH", "US"),
    "Gross Domestic Product": (["EURUSD", "USDJPY"], "HIGH", "US"),
    "Producer Price Index": (["EURUSD", "USDJPY"], "MEDIUM", "US"),
    "Industrial Production": (["EURUSD"], "MEDIUM", "US"),
}


def _next_weekday_on_or_after(d0: date, weekday: int) -> date:
    """date.weekday(): Mon=0 .. Sun=6."""
    delta = (weekday - d0.weekday()) % 7
    return d0 + timedelta(days=delta)


def _first_weekday_of_month(year: int, month: int, weekday: int) -> date:
    first = date(year, month, 1)
    return _next_weekday_on_or_after(first, weekday)


def _add_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _fallback_events(start: date, forward_days: int) -> list[dict[str, object]]:
    end = start + timedelta(days=forward_days)
    out: list[dict[str, object]] = []

    d = _next_weekday_on_or_after(start, 4)  # Friday
    while d <= end:
        out.append(
            {
                "date": d.isoformat(),
                "event": "NFP",
                "impact": "HIGH",
                "pairs": list(PAIRS),
                "category": "US",
                "ai_brief": None,
            }
        )
        d += timedelta(weeks=4)

    cur = date(start.year, start.month, 1)
    while cur <= end:
        try:
            fomc = _first_weekday_of_month(cur.year, cur.month, 2)  # Wednesday
        except ValueError:
            cur = _add_month(cur)
            continue
        if start <= fomc <= end:
            out.append(
                {
                    "date": fomc.isoformat(),
                    "event": "FOMC Rate Decision",
                    "impact": "HIGH",
                    "pairs": list(PAIRS),
                    "category": "US",
                    "ai_brief": None,
                }
            )
        cur = _add_month(cur)

    for label, offset, pairs, impact in (
        ("CPI", 10, list(PAIRS), "HIGH"),
        ("GDP Advance", 14, ["EURUSD", "USDJPY"], "HIGH"),
        ("PCE Deflator", 21, list(PAIRS), "HIGH"),
    ):
        evd = start + timedelta(days=offset)
        if start <= evd <= end:
            out.append(
                {
                    "date": evd.isoformat(),
                    "event": label,
                    "impact": impact,
                    "pairs": pairs,
                    "category": "US",
                    "ai_brief": None,
                }
            )

    out.extend(_cb_meetings(start, forward_days))
    dedup: dict[tuple[str, str], dict[str, object]] = {}
    for ev in out:
        dedup[(str(ev["date"]), str(ev["event"]))] = ev
    return sorted(dedup.values(), key=lambda e: str(e["date"]))


def _cb_meetings(start: date, forward_days: int) -> list[dict[str, object]]:
    """Static central bank meeting dates seeded for next 90 days."""
    # Floor horizon so bi-monthly RBI (first Friday) is not always dropped vs. a 30d macro window.
    end = start + timedelta(days=max(forward_days, 45))
    events: list[dict[str, object]] = []

    # Include May: common meeting month; without it, late-April 30d windows miss ECB entirely.
    ecb_months = [1, 3, 4, 5, 6, 7, 9, 10, 12]
    for year in (start.year, start.year + 1):
        for month in ecb_months:
            try:
                d0 = _first_weekday_of_month(year, month, 3)  # Thursday=3
                d = d0 + timedelta(weeks=1)  # second Thursday
                if start <= d <= end:
                    events.append(
                        {
                            "date": d.isoformat(),
                            "event": "ECB Rate Decision",
                            "impact": "HIGH",
                            "pairs": ["EURUSD"],
                            "category": "EU",
                            "ai_brief": None,
                        }
                    )
            except ValueError:
                pass

    boj_months = [1, 3, 4, 5, 6, 7, 9, 10, 12]
    for year in (start.year, start.year + 1):
        for month in boj_months:
            try:
                d = _first_weekday_of_month(year, month, 4)  # Friday=4
                if start <= d <= end:
                    events.append(
                        {
                            "date": d.isoformat(),
                            "event": "BoJ Rate Decision",
                            "impact": "HIGH",
                            "pairs": ["USDJPY"],
                            "category": "JP",
                            "ai_brief": None,
                        }
                    )
            except ValueError:
                pass

    rbi_months = [2, 4, 6, 8, 10, 12]
    for year in (start.year, start.year + 1):
        for month in rbi_months:
            try:
                d = _first_weekday_of_month(year, month, 4)  # Friday=4
                if start <= d <= end:
                    events.append(
                        {
                            "date": d.isoformat(),
                            "event": "RBI MPC Decision",
                            "impact": "HIGH",
                            "pairs": ["USDINR"],
                            "category": "IN",
                            "ai_brief": None,
                        }
                    )
            except ValueError:
                pass

    return events


def _fred_fetch(start: date, forward_days: int) -> list[dict[str, object]]:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        return []
    end = start + timedelta(days=forward_days)
    url = "https://api.stlouisfed.org/fred/releases/dates"
    params: dict[str, str] = {
        "api_key": key,
        "realtime_start": start.isoformat(),
        "realtime_end": end.isoformat(),
        "file_type": "json",
        "limit": "1000",
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("FRED releases/dates failed: %s", exc)
        return []

    rows = data.get("release_dates") or data.get("releases") or []
    if not isinstance(rows, list):
        return []

    out: list[dict[str, object]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        name = str(item.get("release_name") or item.get("name") or "")
        dt_raw = item.get("date") or item.get("release_date")
        if not dt_raw:
            continue
        dt_s = str(dt_raw)[:10]
        matched: tuple[list[str], str, str] | None = None
        for key_name, meta in _HIGH_MAP.items():
            if key_name.lower() in name.lower() or name.lower() in key_name.lower():
                matched = meta
                break
        if matched is None:
            continue
        pairs, impact, cat = matched
        out.append(
            {
                "date": dt_s,
                "event": name.strip() or "Economic release",
                "impact": impact,
                "pairs": pairs,
                "category": cat,
                "ai_brief": None,
            }
        )
    return out


def fetch_macro_events(forward_days: int = 30) -> list[dict[str, Any]]:
    """Macro events for seeding `macro_events`; FRED-first with programmatic fallback."""
    today = date.today()
    fred = _fred_fetch(today, forward_days)
    if len(fred) >= 2:
        out: list[dict[str, object]] = list(fred)
    else:
        out = _fallback_events(today, forward_days)
        logger.info("Using static macro calendar fallback (%s events)", len(out))

    out.extend(_cb_meetings(today, forward_days))
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, object]] = []
    for e in out:
        k = (str(e["date"]), str(e["event"]))
        if k not in seen:
            seen.add(k)
            deduped.append(e)
    return cast(list[dict[str, Any]], sorted(deduped, key=lambda ev: str(ev["date"])))
