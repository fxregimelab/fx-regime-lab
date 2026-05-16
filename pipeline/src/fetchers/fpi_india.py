"""SEBI FPI daily flow scraper for USD/INR signal augmentation.

Fetches net Foreign Portfolio Investor (FPI) equity and debt flows
from the SEBI daily bulletin. Published after market close (~6 PM IST).
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEBI_FPI_URL = (
    "https://www.sebi.gov.in/sebiweb/home/HomeAction.do"
    "?doListing=yes&smsId=2283&smsTitle=FPI"
)

# Historical archive URL pattern (for backfill)
SEBI_ARCHIVE_URL = (
    "https://www.sebi.gov.in/sebiweb/home/HomeAction.do"
    "?doListing=yes&smsId=2283"
)


def _parse_inr_crores(text: str) -> float | None:
    """Parse strings like '1,234.56' or '-1,234.56 Cr' to float."""
    cleaned = text.replace(",", "").replace("Cr", "").strip()
    # Handle parentheses for negative numbers: (1,234.56)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_sebi_date(text: str) -> date | None:
    """Parse SEBI date formats like '15-May-2026'."""
    try:
        return date.fromisoformat(text)  # fallback for ISO
    except ValueError:
        pass
    # Try DD-Mon-YYYY
    match = re.match(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", text.strip())
    if match:
        day, mon, year = match.groups()
        months = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        }
        if mon in months:
            return date(int(year), months[mon], int(day))
    return None


def fetch_fpi_flows(target_date: date | None = None) -> dict[str, Any] | None:
    """Fetch SEBI FPI net flows for target_date (defaults to today).

    Returns dict with keys:
        - date: ISO date string
        - fpi_equity_net_cr: float | None
        - fpi_debt_net_cr: float | None
        - fpi_total_net_cr: float | None
        - source: "SEBI_FPI_BULLETIN"
    """
    if target_date is None:
        target_date = date.today()

    try:
        resp = requests.get(
            SEBI_FPI_URL,
            headers={"User-Agent": "FX-Regime-Lab/1.0"},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("SEBI FPI request failed: %s", exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # SEBI uses various table structures over time.
    # Strategy: find all tables, iterate rows, match date.
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue

            # First cell is usually the date
            date_text = cells[0].get_text(strip=True)
            parsed_date = _parse_sebi_date(date_text)
            if parsed_date != target_date:
                continue

            # Extract flow values from subsequent cells
            # Typical layout: Date | Equity | Debt | Total
            equity = _parse_inr_crores(cells[1].get_text()) if len(cells) > 1 else None
            debt = _parse_inr_crores(cells[2].get_text()) if len(cells) > 2 else None
            total = _parse_inr_crores(cells[3].get_text()) if len(cells) > 3 else None

            # If total is missing but equity/debt present, compute it
            if total is None and equity is not None and debt is not None:
                total = equity + debt

            result: dict[str, Any] = {
                "date": target_date.isoformat(),
                "fpi_equity_net_cr": equity,
                "fpi_debt_net_cr": debt,
                "fpi_total_net_cr": total,
                "source": "SEBI_FPI_BULLETIN",
            }
            logger.info(
                "FPI flows for %s: equity=%s debt=%s total=%s",
                target_date,
                equity,
                debt,
                total,
            )
            return result

    logger.warning("No FPI data found for %s on SEBI bulletin", target_date)
    return None


def fetch_fpi_history(start_date: date, end_date: date) -> list[dict[str, Any]]:
    """Backfill FPI flows for a date range by iterating daily.

    NOTE: SEBI bulletins only show recent data (typically last 30 days).
    For historical backfill, RBI Bulletin or commercial data is required.
    """
    results: list[dict[str, Any]] = []
    current = start_date
    while current <= end_date:
        row = fetch_fpi_flows(current)
        if row:
            results.append(row)
        current = date.fromordinal(current.toordinal() + 1)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Smoke test: fetch today's data
    today = date.today()
    data = fetch_fpi_flows(today)
    if data:
        print(data)
    else:
        print(f"No FPI data available for {today}")
