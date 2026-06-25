"""CFTC COT bulk historical fetcher (1995–2026).

Downloads annual zip files from CFTC, parses pipe-delimited CSVs,
and upserts into ``historical_cot``.
"""

from __future__ import annotations

import csv
import io
import logging
import random
import ssl
import time
import zipfile
from collections.abc import MutableMapping
from dataclasses import dataclass
from datetime import date
from typing import Any

import pg8000.native
import requests

logger = logging.getLogger(__name__)

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

_K_MKT = "market and exchange names"
_K_DATE = "as of date in form yymmdd"

# Old format (pre-2017)
_K_LO = "noncommercial positions-long (all)"
_K_SH = "noncommercial positions-short (all)"
_K_OIa = "open interest (all)"
_K_OIb = "open interest all"

# New format (post-2017)
_K_ASSET_MGR_LONG = "asset mgr positions long all"
_K_ASSET_MGR_SHORT = "asset mgr positions short all"
_K_LEV_MONEY_LONG = "lev money positions long all"
_K_LEV_MONEY_SHORT = "lev money positions short all"
_K_OTHER_REPT_LONG = "other rept positions long all"
_K_OTHER_REPT_SHORT = "other rept positions short all"

_TARGET_PAIRS = {"EURUSD", "USDJPY", "USDINR"}


@dataclass
class CotHistoricalRow:
    date: date
    pair: str
    net_long: int
    lev_money_net: int | None
    asset_mgr_net: int | None
    open_interest: int


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


def _to_int(s: str) -> int | None:
    if not s:
        return None
    try:
        return int(float(s.replace(",", "")))
    except ValueError:
        return None


def _extract_row(nr: dict[str, str]) -> CotHistoricalRow | None:
    mkt = nr.get(_K_MKT, "")
    if not mkt:
        return None
    pair = _pair_from_market(mkt)
    if pair is None or pair not in _TARGET_PAIRS:
        return None
    d = _parse_yymmdd(nr.get(_K_DATE, ""))
    if d is None:
        return None

    oi_s = nr.get(_K_OIa, "") or nr.get(_K_OIb, "")
    oi_v = _to_int(oi_s) or 0

    # Try old format first
    lo_old = _to_int(nr.get(_K_LO, ""))
    sh_old = _to_int(nr.get(_K_SH, ""))
    if lo_old is not None and sh_old is not None:
        return CotHistoricalRow(
            date=d,
            pair=pair,
            net_long=lo_old - sh_old,
            lev_money_net=None,
            asset_mgr_net=None,
            open_interest=oi_v,
        )

    # New format
    am_lo = _to_int(nr.get(_K_ASSET_MGR_LONG, ""))
    am_sh = _to_int(nr.get(_K_ASSET_MGR_SHORT, ""))
    lm_lo = _to_int(nr.get(_K_LEV_MONEY_LONG, ""))
    lm_sh = _to_int(nr.get(_K_LEV_MONEY_SHORT, ""))
    or_lo = _to_int(nr.get(_K_OTHER_REPT_LONG, ""))
    or_sh = _to_int(nr.get(_K_OTHER_REPT_SHORT, ""))

    if am_lo is None or am_sh is None or lm_lo is None or lm_sh is None:
        return None

    total_long = am_lo + lm_lo + (or_lo or 0)
    total_short = am_sh + lm_sh + (or_sh or 0)

    return CotHistoricalRow(
        date=d,
        pair=pair,
        net_long=total_long - total_short,
        lev_money_net=lm_lo - lm_sh,
        asset_mgr_net=am_lo - am_sh,
        open_interest=oi_v,
    )


def _rows_from_zip(content: bytes) -> list[dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        txts = [n for n in zf.namelist() if n.lower().endswith(".txt") and not n.endswith("/")]
        if not txts:
            raise ValueError("zip: no .txt")
        raw_bytes = zf.read(txts[0])

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


def _download_cot_zip(year: int) -> bytes | None:
    url = f"https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip"
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
                if response.status_code == 404:
                    logger.info("COT zip 404 for year %d: %s", year, url)
                    return None
                response.raise_for_status()
                return response.content
        except Exception as exc:  # noqa: BLE001
            if attempt < 3:
                logger.warning("COT download retry %d/%d for %d: %s", attempt, 3, year, exc)
                time.sleep(1.2 * attempt)
            else:
                logger.error("COT download failed for year %d: %s", year, exc)
    return None


def _pg_conn() -> Any:
    import os
    ctx = ssl._create_unverified_context()
    host = os.environ.get("SUPABASE_DB_HOST", "db.weaaacohvzzgkgxzpaee.supabase.co")
    password = os.environ.get("SUPABASE_DB_PASSWORD")
    if not password:
        raise RuntimeError("SUPABASE_DB_PASSWORD must be set in the environment.")
    return pg8000.native.Connection(
        host=host,
        database="postgres",
        user="postgres",
        password=password,
        ssl_context=ctx,
    )


def _ensure_table() -> None:
    conn = _pg_conn()
    conn.run(
        """
        CREATE TABLE IF NOT EXISTS historical_cot (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            pair VARCHAR(10) NOT NULL,
            net_long BIGINT,
            lev_money_net BIGINT,
            asset_mgr_net BIGINT,
            open_interest BIGINT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(date, pair)
        )
        """
    )
    conn.close()


def _upsert_rows(rows: list[CotHistoricalRow], batch_size: int = 500) -> int:
    if not rows:
        return 0
    conn = _pg_conn()
    inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        placeholders: list[str] = []
        params: dict[str, Any] = {}
        for bidx, row in enumerate(batch):
            prefix = f"p{i}_{bidx}_"
            ph = f"(:{prefix}d, :{prefix}p, :{prefix}nl, :{prefix}lm, :{prefix}am, :{prefix}oi)"
            placeholders.append(ph)
            params[f"{prefix}d"] = row.date.isoformat()
            params[f"{prefix}p"] = row.pair
            params[f"{prefix}nl"] = row.net_long
            params[f"{prefix}lm"] = row.lev_money_net
            params[f"{prefix}am"] = row.asset_mgr_net
            params[f"{prefix}oi"] = row.open_interest

        sql = (
            "INSERT INTO historical_cot (date, pair, net_long, lev_money_net, "
            "asset_mgr_net, open_interest) VALUES "
            f"{', '.join(placeholders)}"
            " ON CONFLICT (date, pair) DO UPDATE SET"
            " net_long = EXCLUDED.net_long,"
            " lev_money_net = EXCLUDED.lev_money_net,"
            " asset_mgr_net = EXCLUDED.asset_mgr_net,"
            " open_interest = EXCLUDED.open_interest"
        )
        conn.run(sql, **params)
        inserted += len(batch)
    conn.close()
    return inserted


def fetch_and_store_all(
    *,
    start_year: int = 1995,
    end_year: int = 2026,
    delay_seconds: float = 1.0,
) -> tuple[int, list[int]]:
    """Download all COT annual zips and upsert into ``historical_cot``.

    Returns (total_rows_inserted, missing_years).
    """
    _ensure_table()
    missing_years: list[int] = []
    total_rows_inserted = 0

    for year in range(start_year, end_year + 1):
        logger.info("Fetching COT for year %d...", year)
        content = _download_cot_zip(year)
        if content is None:
            missing_years.append(year)
            continue
        try:
            raw_rows = _rows_from_zip(content)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to parse zip for year %d: %s", year, exc)
            missing_years.append(year)
            continue

        year_rows: list[CotHistoricalRow] = []
        for row in raw_rows:
            try:
                nr = _norm_row(row)
                parsed = _extract_row(nr)
                if parsed is not None:
                    year_rows.append(parsed)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skip row in %d: %s", year, exc)

        if year_rows:
            # Deduplicate by (date, pair) — some markets appear on multiple exchanges
            seen: set[tuple[date, str]] = set()
            deduped: list[CotHistoricalRow] = []
            for r in year_rows:
                key = (r.date, r.pair)
                if key not in seen:
                    seen.add(key)
                    deduped.append(r)
            inserted = _upsert_rows(deduped)
            total_rows_inserted += inserted
            logger.info(
                "Year %d: parsed %d rows, deduped to %d, upserted %d",
                year,
                len(year_rows),
                len(deduped),
                inserted,
            )
        else:
            logger.warning("Year %d: no rows parsed", year)

        if year < end_year:
            time.sleep(delay_seconds)

    return total_rows_inserted, missing_years


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    total, missing = fetch_and_store_all()
    logger.info("Done. Total rows upserted: %d", total)
    if missing:
        logger.info("Missing/failed years: %s", missing)


if __name__ == "__main__":
    main()
