#!/usr/bin/env python3
"""Temporary one-off: backfill historical_prices (~10y) and refresh research_analogs.

Run from repo root:
  cd pipeline && python seed_history.py

Requires `.env` at repo root with Supabase credentials (same as daily pipeline).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from src.db import writer
from src.fetchers.cross_asset import fetch_max_history
from src.types import load_universe, pairs_from_universe

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

YEARS_BACK = 10


def backfill_prices() -> int:
    load_universe()
    total = 0
    for pair in pairs_from_universe(asset_class="FX"):
        n = fetch_max_history(pair, years_back=YEARS_BACK)
        total += n
        logger.info("historical_prices backfill %s: %s rows", pair, n)
    return total


def refresh_research_analogs() -> None:
    load_universe()
    for pair in pairs_from_universe(asset_class="FX"):
        call = writer.get_latest_regime_call(pair)
        if not call:
            logger.warning("No regime_call for %s — skip analogs", pair)
            continue
        as_of = str(call["date"])[:10]
        composite = float(call.get("signal_composite") or 0.0)
        tail = writer.get_historical_prices(pair, limit=15)
        if len(tail) < 6:
            logger.warning("Insufficient historical_prices tail for %s (%s rows)", pair, len(tail))
            continue
        recent_closes: list[float] = []
        for row in tail[-10:]:
            c = row.get("close")
            if c is not None:
                recent_closes.append(float(c))
        if len(recent_closes) < 6:
            logger.warning("Too few recent closes for %s", pair)
            continue
        current_trend = (
            (recent_closes[-1] / recent_closes[-6]) - 1.0
        ) * 100.0
        rows = writer.get_rpc_historical_analogs(pair, as_of, current_trend, composite)
        if not rows:
            logger.warning("match_historical_analogs returned empty for %s", pair)
            continue
        payload: list[dict[str, object]] = []
        for r in rows:
            md = r.get("match_date")
            match_date_str = str(md)[:10] if md is not None else ""
            payload.append(
                {
                    "as_of_date": as_of,
                    "pair": pair,
                    "rank": int(r.get("rank", 0)),
                    "match_date": match_date_str,
                    "match_score": float(r.get("match_score", 0.0)),
                    "forward_30d_return": r.get("forward_30d_return"),
                    "regime_stability": r.get("regime_stability"),
                    "context_label": r.get("context_label"),
                    "current_trend_5d": r.get("current_trend_5d"),
                    "matched_trend_5d": r.get("matched_trend_5d"),
                    "current_composite": r.get("current_composite"),
                }
            )
        writer.write_research_analogs(payload)
        logger.info(
            "research_analogs upserted for %s as_of=%s (%s matches)",
            pair,
            as_of,
            len(rows),
        )


def main() -> int:
    load_universe()
    logger.info(
        "Backfilling %s years per pair: %s",
        YEARS_BACK,
        ", ".join(pairs_from_universe(asset_class="FX")),
    )
    n = backfill_prices()
    logger.info("Total historical_prices rows written: %s", n)
    logger.info("Refreshing research_analogs via Supabase RPC")
    refresh_research_analogs()
    return 0


if __name__ == "__main__":
    sys.exit(main())
