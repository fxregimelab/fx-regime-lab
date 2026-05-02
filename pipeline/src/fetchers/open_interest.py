"""OI signal derived from CFTC COT open_interest field.

Includes :func:`cme_http_get` for CME Group HTTP fetches (browser-like headers + 403 retry).
"""

from __future__ import annotations

import logging
import time

import requests

from src.types import CotRow

logger = logging.getLogger(__name__)

CME_BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.cmegroup.com/",
}


def cme_http_get(url: str, *, timeout: float = 60.0) -> requests.Response:
    """GET with institutional headers; on HTTP 403, wait 2s and retry once."""
    session = requests.Session()
    response: requests.Response | None = None
    for attempt in (1, 2):
        response = session.get(url, headers=CME_BROWSER_HEADERS, timeout=timeout)
        if response.status_code != 403:
            return response
        if attempt == 1:
            logger.warning("CME HTTP 403 for %s — retrying after 2s", url)
            time.sleep(2.0)
    assert response is not None
    return response


def compute_oi_from_cot(cot_rows: list[CotRow], pair: str) -> float | None:
    """
    Rank the most recent week's OI among the last 52 weeks for the pair.
    Returns a percentile (0–100) or None if fewer than 4 weeks of data.
    """
    rows = sorted(
        [r for r in cot_rows if r.pair == pair],
        key=lambda r: r.date,
    )
    if len(rows) < 4:
        logger.debug("Not enough COT rows for OI percentile on %s", pair)
        return None
    oi_series = [r.open_interest for r in rows if r.open_interest > 0]
    if not oi_series:
        return None
    latest = oi_series[-1]
    rank = sum(1 for v in oi_series if v <= latest)
    return round(rank / len(oi_series) * 100, 1)


def compute_oi_delta_from_cot(cot_rows: list[CotRow], pair: str) -> int | None:
    """Return latest week-over-week open-interest delta for a pair."""
    rows = sorted(
        [r for r in cot_rows if r.pair == pair and r.open_interest > 0],
        key=lambda r: r.date,
    )
    if len(rows) < 2:
        logger.debug("Not enough COT rows for OI delta on %s", pair)
        return None
    latest = rows[-1].open_interest
    previous = rows[-2].open_interest
    return int(latest - previous)
