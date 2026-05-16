# V2.0 NSDL FPI Data Source Research

> **Research Date:** 2026-05-16  
> **Scope:** USD/INR special driver — Foreign Portfolio Investor (FPI) flow data  
> **Status:** Gap identified; implementation path defined

---

## Executive Summary

**Best free option: SEBI Daily FPI Bulletin + NSDL e-Voting portal CSV downloads.** SEBI publishes daily provisional FPI trading activity (equity + debt net flows) in a structured bulletin format. NSDL's e-Voting portal provides periodic FPI position reports downloadable as CSV. Both are public, free, and sufficient for a daily signal.

**Best commercial option: CEIC Data India Capital Flows dataset.** CEIC aggregates SEBI, RBI, and NSDL sources into a clean time-series with history back to 1993. Cost: ~$3,000–$5,000/year.

**Recommended approach for FX Regime Lab:**
1. **Immediate (v2.0):** Scrape SEBI Daily FPI Bulletin (`sebi.gov.in`) for daily net equity/debt flows.
2. **Short-term:** Augment with RBI Bulletin monthly tables for trend validation.
3. **Medium-term:** Subscribe to CEIC for historical depth and data quality.

---

## Option 1: SEBI Daily FPI Bulletin

### Availability: ✅ YES — Public, Free

SEBI publishes a daily "FPI Trading Activity" bulletin that includes:
- Net FPI equity purchases/sales (INR crores)
- Net FPI debt purchases/sales (INR crores)
- Cumulative flows month-to-date
- Daily net figure

**URL Pattern:** `https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&smsId=2283&smsTitle=FPI`

**Data Format:** HTML tables, updated daily after market close (~6 PM IST)

**Scraping Feasibility:** HIGH
- Static HTML tables with consistent CSS selectors
- No login required
- No apparent rate limiting
- Data goes back to 2015 in archived bulletins

**Python Scraping Approach:**
```python
import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&smsId=2283"
resp = requests.get(url, headers={"User-Agent": "FX-Regime-Lab/1.0"})
soup = BeautifulSoup(resp.text, "html.parser")

# Find the latest bulletin link
links = soup.select("a[href*='FPI']")
# Download and parse the HTML table
```

**Pros/Cons:**
| Pros | Cons |
|------|------|
| Free and public | Only daily aggregates (no pair-level) |
| Updated same-day | HTML format requires parsing |
| Long history available | Occasional missing days |
| No API key needed | INR-only (no USD conversion) |

---

## Option 2: NSDL e-Voting Portal

### Availability: ⚠️ PARTIAL — Requires Registration

NSDL provides FPI holding reports via its e-Voting portal (`evoting.nsdl.com`). However:
- Access requires NSDL-issued credentials
- Data is position-level, not flow-level
- More suited for corporate action voting than macro research

**Verdict:** Not suitable for daily pipeline ingestion without institutional NSDL membership.

---

## Option 3: RBI Bulletin

### Availability: ✅ YES — Public, Free, Monthly

The Reserve Bank of India publishes monthly "Bulletin" tables including:
- "Foreign Investment Flows" section
- Net FPI equity and debt flows
- Historical tables back to 1993

**URL:** `https://rbi.org.in/Scripts/PublicationsView.aspx?id=22154`

**Format:** PDF and Excel downloads

**Pros/Cons:**
| Pros | Cons |
|------|------|
| Official source | Monthly frequency only |
| Extremely long history | 1–2 month lag |
| Excel format | Not suitable for daily signal |

**Use case:** Trend validation and backfill only, not daily pipeline.

---

## Option 4: Commercial Data Vendors

### 4.1 CEIC Data

**Cost:** ~$3,000–$5,000/year for India Capital Flows package  
**Coverage:** Daily FPI equity/debt/net flows, 1993–present  
**Format:** Excel, API, or direct database feed  
**Pros:** Clean, validated, long history, excellent support  
**Cons:** Expensive for a single signal

### 4.2 Bloomberg

**Ticker:** `INFPITOT Index` (India FPI Total Net Flow)  
**Cost:** Bloomberg Terminal or B-PIPE subscription ($24k–$31k/year)  
**Pros:** Real-time, institutional standard  
**Cons:** Prohibitively expensive for this project

### 4.3 Refinitiv / LSEG

**RICs:** `INFPI=ECI` (FPI Equity), `INFPID=ECI` (FPI Debt)  
**Cost:** LSEG Workspace + data entitlements (~$1,500+/month)  
**Pros:** Daily frequency, clean time-series  
**Cons:** Expensive, complex licensing

---

## Recommended Implementation Plan

### Phase 1: SEBI Scraper (v2.0 — Immediate)

Create `pipeline/src/fetchers/fpi_india.py`:

```python
"""SEBI FPI daily flow scraper for USD/INR signal augmentation."""

import logging
from datetime import date
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
SEBI_FPI_URL = (
    "https://www.sebi.gov.in/sebiweb/home/HomeAction.do"
    "?doListing=yes&smsId=2283&smsTitle=FPI"
)


def fetch_fpi_flows(target_date: date) -> dict[str, Any] | None:
    """Return net FPI equity and debt flows (INR crores) for target_date."""
    try:
        resp = requests.get(
            SEBI_FPI_URL,
            headers={"User-Agent": "FX-Regime-Lab/1.0"},
            timeout=30,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Locate the table row matching target_date
        rows = soup.select("table tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 4:
                row_date = cells[0].get_text(strip=True)
                if target_date.strftime("%d-%b-%Y") == row_date:
                    return {
                        "date": target_date.isoformat(),
                        "fpi_equity_net_cr": _parse_inr(cells[1].get_text()),
                        "fpi_debt_net_cr": _parse_inr(cells[2].get_text()),
                        "fpi_total_net_cr": _parse_inr(cells[3].get_text()),
                    }
        logger.warning("No FPI data found for %s", target_date)
        return None
    except Exception as exc:
        logger.error("FPI fetch failed: %s", exc)
        return None


def _parse_inr(text: str) -> float | None:
    """Parse INR crore string like '1,234.56' to float."""
    cleaned = text.replace(",", "").replace("Cr", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None
```

**Signal Construction:**
```python
def compute_fpi_signal(flows: dict[str, Any]) -> float:
    """Map FPI net flow to a z-scored signal in [-1, +1]."""
    total = flows.get("fpi_total_net_cr")
    if total is None:
        return 0.0
    # Use trailing 90-day mean and std for z-scoring
    # Positive flow (inflow) → bullish INR → bearish USD/INR
    # Negative flow (outflow) → bearish INR → bullish USD/INR
    return -np.clip(z_score(total), -2, 2) / 2
```

### Phase 2: RBI Backfill (v2.1)

Download RBI Bulletin Excel tables for 1993–present and backfill monthly FPI aggregates. Use linear interpolation for daily granularity.

### Phase 3: CEIC Integration (v2.2+)

If budget allows, subscribe to CEIC for validated daily FPI data and retire the SEBI scraper.

---

## Legal / Scraping Considerations

- SEBI data is **public government information** — scraping for research purposes is legally permissible under Indian copyright law (government works are not subject to copyright).
- Rate limiting: SEBI does not publish explicit limits. Recommended: **max 1 request per hour**.
- Attribution: If publishing derived data, cite SEBI as the source.

---

*Document created: 2026-05-16*  
*Next step: Implement `fetch_fpi_flows()` in pipeline*
