#!/usr/bin/env python3
"""
FedWatch / implied policy path spike — NOT wired into run.py.

Goal: probe whether CME FedWatch HTML or an API surface is stable enough for a
future `fedwatch_pipeline.py` without adding a new dependency yet.

Run from repo root:
    python scripts/dev/fedwatch_spike.py

Next steps before any pipeline integration:
- Legal / ToS check on automated access to cmegroup.com
- Pick a stable data source (official API vs licensed vendor vs manual)
- Get explicit approval for new pip deps and a canonical run.py step slot
"""
from __future__ import annotations

import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    os.chdir(ROOT)
    url = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"
    print(f"[fedwatch_spike] GET {url}")
    try:
        r = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "FXRegimeLab-FedwatchSpike/1.0 (+research)"},
        )
    except requests.RequestException as e:
        print(f"  network error: {e}")
        return 1
    print(f"  status={r.status_code} bytes={len(r.content or b'')}")
    text = (r.text or "")[:200000]
    markers = ("FedWatch", "target rate", "probability", "FOMC")
    found = [m for m in markers if m.lower() in text.lower()]
    print(f"  naive markers found: {found or 'none'}")
    if r.status_code != 200:
        print(
            "  note: non-200 (e.g. 403) is common for scripted GETs — plan on a licensed API "
            "or manual data path before any production module."
        )
        return 0
    print("  spike OK — inspect HTML structure manually before any scraper.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
