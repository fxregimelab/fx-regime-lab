# ruff: noqa: E302
"""CFTC COT weekly positioning (financial futures)."""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import random
import time
import zipfile
from collections import defaultdict
from collections.abc import MutableMapping
from datetime import date
from typing import Any

import aiohttp
import requests

from src.fetchers.async_engine import AsyncFetcher
from src.signals.cot import COT_PERCENTILE_WINDOW_REPORTS
from src.types import CotRow, pairs_from_universe

logger = logging.getLogger(__name__)
_COT_LOOKBACK_WEEKS = COT_PERCENTILE_WINDOW_REPORTS
# Allow up to two absent weekly reports in the selected window. Longer
# interruptions need dated source evidence and an explicit policy exception.
_COT_MAX_REPORT_GAP_DAYS = 21
# A 156-report window normally spans 155 weeks. Allow 13 additional weeks
# for isolated omissions or shifted dates, but reject persistently sparse data.
_COT_MAX_WINDOW_SPAN_DAYS = 168 * 7
_K_MKT = "market and exchange names"
_K_DATE = "as of date in form yymmdd"
_K_LO = "noncommercial positions-long (all)"
_K_SH = "noncommercial positions-short (all)"
_K_OIa = "open interest (all)"
_K_OIb = "open interest all"
_KL_NEW = ("asset mgr positions long all", "lev money positions long all", "other rept positions long all")  # noqa: E501
_KS_NEW = ("asset mgr positions short all", "lev money positions short all", "other rept positions short all")  # noqa: E501
_K_AM_LONG = "asset mgr positions long all"
_K_AM_SHORT = "asset mgr positions short all"
_K_LM_LONG = "lev money positions long all"
_K_LM_SHORT = "lev money positions short all"
_USER_AGENTS = (
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
    ),
)

def _norm_header(h: str) -> str:
    s = str(h).strip().replace("_", " ")
    return " ".join(s.lower().split())

def _norm_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        _norm_header(str(k)): ("" if v is None else str(v).strip())
        for k, v in row.items()
        if k is not None
    }

def _parse_yymmdd(s: str) -> date | None:
    s = str(s).strip()
    if len(s) != 6 or not s.isdigit():
        return None
    yy = int(s[:2])
    year = 2000 + yy if yy <= 79 else 1900 + yy
    try:
        return date(year, int(s[2:4]), int(s[4:6]))
    except ValueError:
        return None

def _pair_from_market(name: str) -> str | None:
    u = name.upper()
    if "EURO FX" in u or ("EURO" in u and "FX" in u):
        return "EURUSD"
    if "JAPANESE YEN" in u:
        return "USDJPY"
    if "INDIAN RUPEE" in u:
        return "USDINR"
    return None

def _parse_int(nr: dict[str, str], key: str) -> int | None:
    s = nr.get(key, "")
    if not s:
        return None
    try:
        return int(float(s.replace(",", "")))
    except ValueError:
        return None


def _spec_ls(nr: dict[str, str]) -> tuple[int, int] | None:
    lo, sh = nr.get(_K_LO), nr.get(_K_SH)
    if lo and sh:
        return int(float(lo.replace(",", ""))), int(float(sh.replace(",", "")))
    if not all(nr.get(k) for k in _KL_NEW) or not all(nr.get(k) for k in _KS_NEW):
        return None
    return (
        sum(int(float(nr[k].replace(",", ""))) for k in _KL_NEW),
        sum(int(float(nr[k].replace(",", ""))) for k in _KS_NEW),
    )


def _breakdown_ls(nr: dict[str, str]) -> tuple[int | None, int | None]:
    """Return (asset_mgr_net, lev_money_net) from normalized row."""
    am_long = _parse_int(nr, _K_AM_LONG)
    am_short = _parse_int(nr, _K_AM_SHORT)
    lm_long = _parse_int(nr, _K_LM_LONG)
    lm_short = _parse_int(nr, _K_LM_SHORT)
    am_net = (am_long - am_short) if am_long is not None and am_short is not None else None
    lm_net = (lm_long - lm_short) if lm_long is not None and lm_short is not None else None
    return am_net, lm_net

def _rows_from_download(content: bytes, *, from_zip: bool) -> list[dict[str, Any]]:
    if from_zip:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            txts = [n for n in zf.namelist() if n.lower().endswith(".txt") and not n.endswith("/")]
            if not txts:
                raise ValueError("zip: no .txt")
            raw_bytes = zf.read(txts[0])
    else:
        raw_bytes = content
    text = ""
    for enc in ("utf-8", "latin-1"):
        try:
            text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = raw_bytes.decode("latin-1", errors="replace")
    rows: list[dict[str, Any]] = []
    if not text.strip():
        return rows
    sample = text[:4096]
    first_line = sample.splitlines()[0] if sample else ""
    if "|" in first_line:
        reader = csv.DictReader(io.StringIO(text), delimiter="|")
    else:
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows.extend(dict(r) for r in reader)
    return rows


def _download_cot_bytes(url: str) -> bytes:
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        headers: MutableMapping[str, str | bytes] = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.cftc.gov/",
            "Connection": "keep-alive",
            "DNT": "1",
        }
        try:
            with requests.Session() as session:
                response = session.get(url, headers=headers, timeout=60)
                response.raise_for_status()
                return response.content
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < 3:
                time.sleep(1.2 * attempt)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"Unable to download COT payload: {url}")

def fetch_cot(year: int | None = None) -> list[CotRow]:
    y = year if year is not None else date.today().year
    # A January report needs almost three complete prior calendar years to fill
    # the signal's 156-report window. The weekly file may overlap the archive.
    sources = [
        ("zip", f"https://www.cftc.gov/files/dea/history/fut_fin_txt_{source_year}.zip")
        for source_year in range(y - 3, y + 1)
    ]
    sources.append(("txt", "https://www.cftc.gov/dea/newcot/FinFutWk.txt"))
    raw_rows: list[dict[str, Any]] = []
    failed_sources: list[str] = []
    for kind, url in sources:
        try:
            payload = _download_cot_bytes(url)
            parsed = _rows_from_download(payload, from_zip=(kind == "zip"))
            if parsed:
                raw_rows.extend(parsed)
            else:
                failed_sources.append(f"{url}: empty")
        except Exception as exc:  # noqa: BLE001
            failed_sources.append(f"{url}: {exc}")
            logger.debug("COT source failed %s: %s", url, exc)
    if not raw_rows:
        logger.warning("COT download/parse failed (all sources): %s", "; ".join(failed_sources))
        return []
    if failed_sources:
        logger.warning("COT partial source coverage: %s", "; ".join(failed_sources))
    fx_pairs = pairs_from_universe(asset_class="FX")
    fx_set = frozenset(fx_pairs)
    by_pair: dict[str, dict[date, CotRow]] = defaultdict(dict)
    conflicting_pairs: set[str] = set()
    for row in raw_rows:
        try:
            nr = _norm_row(row)
            mkt = nr.get(_K_MKT, "")
            if not mkt:
                continue
            pair = _pair_from_market(mkt)
            if pair is None or pair not in fx_set:
                continue
            d = _parse_yymmdd(nr.get(_K_DATE, ""))
            if d is None:
                continue
            ls = _spec_ls(nr)
            if ls is None:
                continue
            long_v, short_v = ls
            oi_s = nr.get(_K_OIa, "") or nr.get(_K_OIb, "")
            oi_v = int(float(oi_s.replace(",", ""))) if oi_s else 0
            am_net, lm_net = _breakdown_ls(nr)
            cot_row = CotRow(
                date=d,
                pair=pair,
                net_long=long_v - short_v,
                open_interest=oi_v,
                asset_mgr_net=am_net,
                lev_money_net=lm_net,
            )
            previous = by_pair[pair].get(d)
            if previous is not None and previous != cot_row:
                conflicting_pairs.add(pair)
                logger.warning("COT conflicting duplicate for %s on %s", pair, d)
            else:
                by_pair[pair][d] = cot_row
        except Exception as exc:  # noqa: BLE001
            logger.debug("skip COT row: %s", exc)
    merged: list[CotRow] = []
    for pair in fx_pairs:
        if pair in conflicting_pairs:
            logger.warning("COT %s rejected due to conflicting duplicate reports", pair)
            continue
        rows = [by_pair[pair][d] for d in sorted(by_pair[pair])]
        if len(rows) < COT_PERCENTILE_WINDOW_REPORTS:
            logger.warning(
                "COT %s insufficient distinct reports: %d/%d",
                pair, len(rows), COT_PERCENTILE_WINDOW_REPORTS,
            )
            continue
        window = rows[-_COT_LOOKBACK_WEEKS:]
        broken_gap = next(
            (
                (left.date, right.date, (right.date - left.date).days)
                for left, right in zip(window, window[1:])
                if (right.date - left.date).days > _COT_MAX_REPORT_GAP_DAYS
            ),
            None,
        )
        if broken_gap is not None:
            logger.warning(
                "COT %s rejected report-date gap %s to %s (%d days; max %d)",
                pair, *broken_gap, _COT_MAX_REPORT_GAP_DAYS,
            )
            continue
        span_days = (window[-1].date - window[0].date).days
        if span_days > _COT_MAX_WINDOW_SPAN_DAYS:
            logger.warning(
                "COT %s rejected report-date span %d days (max %d)",
                pair, span_days, _COT_MAX_WINDOW_SPAN_DAYS,
            )
            continue
        merged.extend(window)
    merged.sort(key=lambda r: (r.date, r.pair))
    return merged


async def fetch_cot_async(
    universe: dict[str, Any],
    session: aiohttp.ClientSession,
    *,
    fetcher: AsyncFetcher | None = None,
) -> list[CotRow]:
    """COT via threaded ``fetch_cot`` (ZIP/CSV parse stays sync to avoid regressions)."""

    _ = universe, session
    gate = fetcher if fetcher is not None else AsyncFetcher()
    t0 = time.perf_counter()
    async with gate.semaphore:
        rows = await asyncio.to_thread(fetch_cot)
    logger.info("fetch_cot_async rows=%s in %.3fs", len(rows), time.perf_counter() - t0)
    return rows
