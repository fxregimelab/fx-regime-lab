# macro_pipeline.py
# Phase 10 Stage 2: Fetch economic calendar from ForexFactory XML feed
# Outputs data/macro_cal.json — a richer event list with impact levels and pair tags
#
# Source (primary):  https://nfs.faireconomy.media/ff_calendar_thisweek.xml
#                    https://nfs.faireconomy.media/ff_calendar_nextweek.xml
# Source (fallback): cb_events.json (manually curated CB meetings)
#
# Strategy:
#   1. If data/macro_cal.json exists and is <12h old, skip all network calls (avoids rate limits)
#   2. Fetch ForexFactory thisweek + nextweek XML; filter HIGH/MEDIUM for USD/EUR/JPY/INR
#   3. Always supplement with cb_events.json (CB meetings beyond FF 2-week window)
#   4. Write to data/macro_cal.json

import os
import json
import datetime
import xml.etree.ElementTree as ET

import requests
import pandas as pd
from config import TODAY

"""
Economic calendar Pipeline.

Execution context:
- Called by run.py as STEP 8 (macro)
- Depends on: morning_brief.py
- Outputs: data/macro_cal.json
- Next step: ai_brief.py
- Blocking: NO — pipeline continues if this step fails

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""

_FF_URLS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.xml",   # may 404 at week boundary
]

# ForexFactory currency codes → (display country, pair list)
_FF_CURRENCY_MAP = {
    "USD": ("US",  ["EURUSD", "USDJPY", "USDINR"]),
    "EUR": ("EUR", ["EURUSD"]),
    "JPY": ("JP",  ["USDJPY"]),
    "INR": ("IN",  ["USDINR"]),
}

_OUTPATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "macro_cal.json")
_CB_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cb_events.json")

# Cache freshness: skip network requests if file is younger than this
_CACHE_MAX_AGE_HOURS = 12


def _is_cache_fresh():
    if not os.path.exists(_OUTPATH):
        return False
    age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(_OUTPATH))
    return age.total_seconds() < _CACHE_MAX_AGE_HOURS * 3600


def _parse_ff_date(date_str):
    """Parse ForexFactory date string e.g. 'Mar 07 2026' → pd.Timestamp."""
    try:
        return pd.Timestamp(date_str.strip())
    except Exception:
        return None


def _fetch_ff_xml(url):
    """Fetch one ForexFactory XML URL; return list of raw dicts or [] on any failure."""
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 404:
            return []                        # nextweek URL may 404 at week boundary — normal
        r.raise_for_status()

        # Detect rate-limit HTML response (FF returns HTML page, not XML)
        content_type = r.headers.get("Content-Type", "")
        if "html" in content_type or r.text.strip().startswith("<!DOCTYPE"):
            print(f"    FF rate-limited for {url.split('/')[-1]} — will use cached/fallback data")
            return None                      # None = rate-limited (different from [] = fetched but empty)

        root = ET.fromstring(r.content)
        events = []
        for ev in root.findall("eventInfo"):
            events.append({
                "title":   (ev.findtext("title")   or "").strip(),
                "country": (ev.findtext("country") or "").strip().upper(),
                "date":    ev.findtext("date")   or "",
                "time":    (ev.findtext("time")    or "").strip(),
                "impact":  (ev.findtext("impact")  or "").strip(),
            })
        return events
    except ET.ParseError:
        print(f"    FF XML parse error for {url.split('/')[-1]}")
        return []
    except Exception as e:
        print(f"    FF fetch failed ({url.split('/')[-1]}): {e}")
        return []


def _load_cb_fallback(today, cutoff):
    """Load cb_events.json and return events in new schema format."""
    events = []
    try:
        cb = json.load(open(_CB_PATH, encoding="utf-8"))
        for date_str, name in cb.items():
            try:
                dt = pd.Timestamp(date_str)
            except Exception:
                continue
            if today <= dt <= cutoff:
                events.append({
                    "date":    date_str,
                    "time":    None,
                    "country": "CB",
                    "event":   name,
                    "impact":  "HIGH",
                    "pairs":   ["EURUSD", "USDJPY", "USDINR"],
                })
    except Exception as e:
        print(f"    cb_events.json load failed: {e}")
    return events


def fetch_macro_calendar():
    print("\n[macro] fetching economic calendar...")

    today  = pd.Timestamp(TODAY).normalize()
    cutoff = today + pd.Timedelta(days=45)

    # --- 1. Cache freshness check ---
    if _is_cache_fresh():
        try:
            cached = json.load(open(_OUTPATH, encoding="utf-8"))
            print(f"    cache fresh (<{_CACHE_MAX_AGE_HOURS}h) — using {len(cached)} cached events")
            return cached
        except Exception:
            pass

    # --- 2. Fetch ForexFactory XML feeds ---
    print(f"    fetching ForexFactory calendar (thisweek + nextweek)...")
    ff_events = []
    rate_limited = False
    seen = set()

    for url in _FF_URLS:
        raw_list = _fetch_ff_xml(url)
        if raw_list is None:
            rate_limited = True
            continue
        for ev in raw_list:
            currency = ev["country"]
            if currency not in _FF_CURRENCY_MAP:
                continue
            impact_raw = ev["impact"]
            if impact_raw not in ("High", "Medium"):
                continue

            dt = _parse_ff_date(ev["date"])
            if dt is None or dt < today or dt > cutoff:
                continue

            date_str = dt.strftime("%Y-%m-%d")
            # Normalize time: "1:30pm" → "13:30"
            time_str = None
            raw_time = ev.get("time", "")
            if raw_time and raw_time.lower() not in ("", "all day", "tentative"):
                try:
                    t = pd.Timestamp(f"2000-01-01 {raw_time}")
                    time_str = t.strftime("%H:%M")
                except Exception:
                    time_str = raw_time

            country_code, pairs = _FF_CURRENCY_MAP[currency]
            event_name = ev["title"]
            impact = "HIGH" if impact_raw == "High" else "MED"

            key = (date_str, event_name[:30])
            if key in seen:
                continue
            seen.add(key)

            ff_events.append({
                "date":    date_str,
                "time":    time_str,
                "country": country_code,
                "event":   event_name,
                "impact":  impact,
                "pairs":   pairs,
            })

    # --- 3. CB events as supplement (always add CB meetings beyond FF window) ---
    cb_events = _load_cb_fallback(today, cutoff)
    for cb_ev in cb_events:
        if not any(e["date"] == cb_ev["date"] for e in ff_events):
            ff_events.append(cb_ev)

    ff_events.sort(key=lambda x: (x["date"], x["country"]))

    # --- 4. Write output ---
    os.makedirs(os.path.dirname(_OUTPATH), exist_ok=True)
    with open(_OUTPATH, "w", encoding="utf-8") as f:
        json.dump(ff_events, f, indent=2)

    high_n = sum(1 for e in ff_events if e["impact"] == "HIGH")
    med_n  = sum(1 for e in ff_events if e["impact"] == "MED")
    status = "(rate-limited; CB only)" if rate_limited and not any(e["country"] != "CB" for e in ff_events) else ""
    print(f"    OK  {len(ff_events)} events ({high_n} HIGH, {med_n} MED) -> {_OUTPATH} {status}")
    return ff_events


if __name__ == "__main__":
    fetch_macro_calendar()
