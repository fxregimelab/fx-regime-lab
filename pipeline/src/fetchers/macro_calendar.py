"""Macro calendar: ForexFactory weekly XML (primary) with programmatic fallback.

FRED ``releases/dates`` is deprecated for this module — use the free NFS weekly feed.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from typing import Any, cast

import requests

from src.types import pairs_from_universe

logger = logging.getLogger(__name__)

FOREXFACTORY_WEEKLY_XML_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"


def _impact_meta() -> dict[str, tuple[list[str], str, str]]:
    """Canonical ``macro_events.event`` keys → (pairs, impact, category)."""

    fx = list(pairs_from_universe(asset_class="FX"))
    return {
        "US CPI YoY": (fx, "HIGH", "US"),
        "US Non-Farm Payrolls": (fx, "HIGH", "US"),
        "FOMC Rate Decision": (fx, "HIGH", "US"),
        "US GDP Advance": (fx, "HIGH", "US"),
        "US PCE Deflator": (fx, "HIGH", "US"),
        "US Unemployment Rate": (fx, "HIGH", "US"),
        "US PPI MoM": (fx, "MEDIUM", "US"),
        "US Industrial Production": (fx, "MEDIUM", "US"),
        "ECB Rate Decision": (["EURUSD", "EURINR"], "HIGH", "EU"),
        "BoJ Rate Decision": (["USDJPY"], "HIGH", "JP"),
        "RBI MPC Decision": (["USDINR"], "HIGH", "IN"),
        "BoE Rate Decision": (["GBPUSD", "GBPINR"], "HIGH", "UK"),
        "RBA Rate Decision": (["AUDUSD"], "HIGH", "AU"),
        "BoC Rate Decision": (["USDCAD"], "HIGH", "CA"),
        "SNB Rate Decision": (["USDCHF"], "HIGH", "CH"),
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
                "event": "US Non-Farm Payrolls",
                "impact": "HIGH",
                "pairs": list(pairs_from_universe(asset_class="FX")),
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
                    "pairs": list(pairs_from_universe(asset_class="FX")),
                    "category": "US",
                    "ai_brief": None,
                }
            )
        cur = _add_month(cur)

    for label, offset, pairs, impact in (
        ("US CPI YoY", 10, list(pairs_from_universe(asset_class="FX")), "HIGH"),
        ("US GDP Advance", 14, list(pairs_from_universe(asset_class="FX")), "HIGH"),
        ("US PCE Deflator", 21, list(pairs_from_universe(asset_class="FX")), "HIGH"),
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
    end = start + timedelta(days=max(forward_days, 45))
    events: list[dict[str, object]] = []

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
                            "pairs": ["EURUSD", "EURINR"],
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


def _elem_text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    if el.text is None:
        return ""
    return str(el.text).strip()


def _parse_ff_calendar_date(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%m-%d-%Y").date().isoformat()
    except ValueError:
        logger.warning("Unparseable ForexFactory date: %s", raw)
        return None


def _match_forexfactory_event(country: str, title: str) -> str | None:
    """Map FF ``country`` + ``title`` to a canonical impact-map key, or None."""
    c = country.strip().upper()
    t = title.strip().lower()

    if c == "USD":
        if "fomc" in t or ("federal funds" in t and "rate" in t):
            return "FOMC Rate Decision"
        if "non-farm" in t or "nonfarm" in t or "non farm" in t:
            return "US Non-Farm Payrolls"
        if "cpi" in t or "consumer price" in t:
            return "US CPI YoY"
        if "employment cost index" in t:
            return None
        if "gdp" in t or "gross domestic product" in t:
            return "US GDP Advance"
        if "pce" in t and "price" in t:
            return "US PCE Deflator"
        if "unemployment" in t and "rate" in t:
            return "US Unemployment Rate"
        if "producer price" in t or " ppi" in t or t.startswith("ppi"):
            return "US PPI MoM"
        if "industrial production" in t:
            return "US Industrial Production"
        return None

    if c == "EUR":
        if "ecb" in t:
            if any(k in t for k in ("rate", "interest", "deposit", "refinancing", "monetary")):
                return "ECB Rate Decision"
        return None

    if c in ("GBP", "UK"):
        if "boe" in t or "bank of england" in t:
            if any(k in t for k in ("rate", "interest", "bank", "monetary", "mpc")):
                return "BoE Rate Decision"
        return None

    if c == "AUD":
        if "rba" in t or "reserve bank of australia" in t:
            if any(k in t for k in ("rate", "interest", "cash rate", "monetary")):
                return "RBA Rate Decision"
        return None

    if c == "CAD":
        if "boc" in t or "bank of canada" in t:
            if any(k in t for k in ("rate", "interest", "overnight", "monetary")):
                return "BoC Rate Decision"
        return None

    if c == "CHF":
        if "snb" in t or "swiss national bank" in t:
            if any(k in t for k in ("rate", "interest", "monetary")):
                return "SNB Rate Decision"
        return None

    if c == "JPY":
        if "boj" in t or "bank of japan" in t:
            return "BoJ Rate Decision"
        return None

    if c == "INR" or c == "IN":
        if "rbi" in t:
            return "RBI MPC Decision"
        return None

    if "rbi" in t and "rate" in t:
        return "RBI MPC Decision"

    return None


def _fetch_forexfactory_weekly_xml() -> str | None:
    try:
        r = requests.get(FOREXFACTORY_WEEKLY_XML_URL, timeout=45)
        r.raise_for_status()
        return r.text
    except Exception as exc:  # noqa: BLE001
        logger.warning("ForexFactory weekly XML fetch failed: %s", exc)
        return None


def fetch_forexfactory_week_high_impact() -> list[dict[str, Any]]:
    """High-impact rows from the weekly XML feed with consensus/previous metadata.

    Unmapped FF titles are skipped (logged at DEBUG).
    """
    xml_text = _fetch_forexfactory_weekly_xml()
    if not xml_text:
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("ForexFactory weekly XML parse error: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    for ev in root.findall("./event"):
        title = _elem_text(ev.find("title"))
        country = _elem_text(ev.find("country"))
        impact_raw = _elem_text(ev.find("impact")).lower()
        if impact_raw != "high":
            continue

        date_iso = _parse_ff_calendar_date(_elem_text(ev.find("date")))
        if not date_iso:
            continue

        canonical = _match_forexfactory_event(country, title)
        if canonical is None:
            logger.debug("Skipping unmapped high-impact event: %s %s", country, title)
            continue

        meta = _impact_meta()[canonical]
        _, cal_impact, cat = meta
        time_s = _elem_text(ev.find("time")) or None
        forecast = _elem_text(ev.find("forecast")) or None
        previous = _elem_text(ev.find("previous")) or None

        out.append(
            {
                "event_name": canonical,
                "date": date_iso,
                "time": time_s,
                "forecast": forecast,
                "previous": previous,
                "impact": cal_impact,
                "category": cat,
                "pairs": list(meta[0]),
                "title_raw": title,
                "country": country,
            }
        )

    logger.info("ForexFactory weekly XML: %s mapped high-impact events", len(out))
    return out


def fetch_macro_events(forward_days: int = 30) -> list[dict[str, Any]]:
    """Macro events for seeding ``macro_events``: ForexFactory XML + static fallback.

    FRED release dates are no longer queried for this path.
    """
    logger.info(
        "macro calendar: using ForexFactory weekly XML (FRED release dates deprecated)"
    )
    today = date.today()
    end_horizon = today + timedelta(days=forward_days)

    xml_rows = fetch_forexfactory_week_high_impact()
    out: list[dict[str, object]] = []
    for row in xml_rows:
        d_iso = str(row["date"])
        event_d = date.fromisoformat(d_iso)
        if event_d > end_horizon or event_d < today:
            continue
        out.append(
            {
                "date": d_iso,
                "event": row["event_name"],
                "impact": row["impact"],
                "pairs": row["pairs"],
                "category": row["category"],
                "ai_brief": None,
            }
        )

    if len(xml_rows) < 1:
        logger.warning("ForexFactory XML yielded no mapped events; using static fallback")
        out = _fallback_events(today, forward_days)
    else:
        out.extend(_fallback_events(today, forward_days))

    out.extend(_cb_meetings(today, forward_days))
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, object]] = []
    for e in out:
        k = (str(e["date"]), str(e["event"]))
        if k not in seen:
            seen.add(k)
            deduped.append(e)
    return cast(list[dict[str, Any]], sorted(deduped, key=lambda ev: str(ev["date"])))
