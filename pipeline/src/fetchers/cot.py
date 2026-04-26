# ruff: noqa: E302
"""CFTC COT weekly positioning (financial futures)."""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections import defaultdict
from datetime import date
from typing import Any

import requests

from src.types import PAIRS, CotRow

logger = logging.getLogger(__name__)
_K_MKT = "market and exchange names"
_K_DATE = "as of date in form yymmdd"
_K_LO = "noncommercial positions-long (all)"
_K_SH = "noncommercial positions-short (all)"
_K_OIa = "open interest (all)"
_K_OIb = "open interest all"
_KL_NEW = ("asset mgr positions long all", "lev money positions long all", "other rept positions long all")  # noqa: E501
_KS_NEW = ("asset mgr positions short all", "lev money positions short all", "other rept positions short all")  # noqa: E501

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
    return "EURUSD" if "EURO FX" in u else "USDJPY" if "JAPANESE YEN" in u else "USDINR" if "INDIAN RUPEE" in u else None  # noqa: E501

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

def fetch_cot(year: int | None = None) -> list[CotRow]:
    y = year if year is not None else date.today().year
    sources = [
        ("zip", f"https://www.cftc.gov/files/dea/history/fut_fin_txt_{y}.zip"),
        ("zip", "https://www.cftc.gov/files/dea/history/fut_fin_txt_2025.zip"),
        ("txt", "https://www.cftc.gov/dea/newcot/FinFutWk.txt"),
    ]
    raw_rows: list[dict[str, Any]] = []
    last_err = ""
    for kind, url in sources:
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            parsed = _rows_from_download(r.content, from_zip=(kind == "zip"))
            if parsed:
                raw_rows = parsed
                break
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            logger.debug("COT source failed %s: %s", url, exc)
    if not raw_rows:
        logger.warning("COT download/parse failed (all sources): %s", last_err or "no rows")
        return []
    by_pair: dict[str, list[CotRow]] = defaultdict(list)
    for row in raw_rows:
        try:
            nr = _norm_row(row)
            mkt = nr.get(_K_MKT, "")
            if not mkt:
                continue
            pair = _pair_from_market(mkt)
            if pair is None or pair not in PAIRS:
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
            by_pair[pair].append(
                CotRow(date=d, pair=pair, net_long=long_v - short_v, open_interest=oi_v))
        except Exception as exc:  # noqa: BLE001
            logger.debug("skip COT row: %s", exc)
    merged: list[CotRow] = []
    for pair in PAIRS:
        rows = sorted(by_pair.get(pair, []), key=lambda x: x.date)
        merged.extend(rows[-52:])
    merged.sort(key=lambda r: (r.date, r.pair))
    return merged
