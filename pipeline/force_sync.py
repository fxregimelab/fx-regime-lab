"""One-off backfill: run the daily pipeline for explicit ISO dates (bypasses Prefect UI).

Loads ``.env`` from repo root, then invokes the raw async ``run_daily`` flow function
(``run_daily.fn``) so no Prefect server is required.

Usage (from repo root)::

    cd pipeline && python force_sync.py

Requires: ``SUPABASE_*``, ``FRED_API_KEY``, ``OPENROUTER_API_KEY`` in environment.

Spot OHLC uses ``ALPHAVANTAGE_API_KEY`` first (see ``.env.example``); set it to avoid
Yahoo/yfinance spot failures. Optional: ``PREFECT_LOGGING_TO_API_WHEN_MISSING_FLOW=ignore``
when calling ``run_daily.fn`` outside a Prefect flow to suppress API log-handler noise.

Backfill pacing: **60s** async sleep between the two dates; desk-card OpenRouter calls use
**5s** between pairs (via ``FORCE_SYNC_DESK_PAIR_COOLDOWN_SEC``, set only for this script).

Post-run DB check (requires ``DATABASE_URL``, e.g. Supabase session pooler)::

    psql "$DATABASE_URL" -c \\
      "SELECT date, count(*) FROM desk_open_cards GROUP BY date ORDER BY date DESC LIMIT 2;"
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Set by ``main()`` so ``batch_desk_briefs_task`` runs desk AI one pair at a time with sleeps
# (see ``src.scheduler.orchestrator``). Cleared in ``finally`` so other runners stay parallel.
_DESK_PAIR_COOLDOWN_ENV = "FORCE_SYNC_DESK_PAIR_COOLDOWN_SEC"
_DESK_PAIR_COOLDOWN_SEC = "5"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")
    logging.basicConfig(level=logging.INFO)

    async def _run() -> None:
        from src.scheduler.orchestrator import run_daily

        os.environ[_DESK_PAIR_COOLDOWN_ENV] = _DESK_PAIR_COOLDOWN_SEC
        dates = ("2026-05-01", "2026-05-02")
        try:
            for i, d in enumerate(dates):
                if i > 0:
                    logging.info(
                        "force_sync: 60s cooldown between backfill dates before %s",
                        d,
                    )
                    await asyncio.sleep(60)
                print(f"=== force_sync run_daily({d!r}) ===", flush=True)
                await run_daily.fn(d)
        finally:
            os.environ.pop(_DESK_PAIR_COOLDOWN_ENV, None)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
