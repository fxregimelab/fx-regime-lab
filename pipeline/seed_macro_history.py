#!/usr/bin/env python3
"""One-off seed for historical_macro_surprises using embedded mock CPI data.

Run from repo root:
  cd pipeline && python seed_macro_history.py

Replace MOCK_CSV with a real file read when the historical dump is available.
"""

from __future__ import annotations

import csv
import io
import logging
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from src.db import writer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MOCK_CSV = """date,time,actual,consensus,previous
2010-01-15,08:30,2.6,2.8,2.7
2012-06-14,08:30,1.7,1.9,2.3
2014-11-20,08:30,1.3,1.4,1.7
2016-08-16,08:30,0.8,1.0,1.0
2018-10-11,08:30,2.3,2.4,2.7
"""

EVENT_NAME = "US CPI YoY"


def _surprise_direction(actual: float, consensus: float) -> str:
    """Higher CPI YoY is USD-positive for this series."""
    if actual > consensus:
        return "BEAT"
    if actual < consensus:
        return "MISS"
    return "IN-LINE"


def parse_mock_csv(csv_text: str) -> list[dict[str, object]]:
    rows_out: list[dict[str, object]] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        d_raw = (row.get("date") or "").strip()
        t_raw = (row.get("time") or "").strip() or None
        actual = float(row["actual"])
        consensus = float(row["consensus"])
        previous = float(row["previous"])
        surprise_bps = actual - consensus
        direction = _surprise_direction(actual, consensus)
        parsed_date = date.fromisoformat(d_raw)
        payload = {
            "event_name": EVENT_NAME,
            "date": parsed_date.isoformat(),
            "time": t_raw,
            "actual": actual,
            "consensus": consensus,
            "previous": previous,
            "surprise_bps": surprise_bps,
            "surprise_direction": direction,
        }
        logger.info(
            "parsed row %s: surprise_bps=%s surprise_direction=%s",
            d_raw,
            surprise_bps,
            direction,
        )
        rows_out.append(payload)
    return rows_out


def main() -> int:
    rows = parse_mock_csv(MOCK_CSV)
    if not rows:
        logger.error("no rows parsed")
        return 1
    writer.write_historical_macro_surprises(rows)
    logger.info("upserted %s rows to historical_macro_surprises", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
