"""Retired synthetic risk-reversal backfill.

The old implementation derived an options-market field from realised volatility
and spot movement. That estimate was not an OTC 25-delta risk reversal and
cannot support changes to published signals or regime calls.

The compatibility entry point is now read-only. It provides a bounded inventory
of historical signal rows and rejects every write request before database access.
Any historical correction requires observed source data and a new, versioned
replay through the central publication boundary.
"""

from __future__ import annotations

import argparse
import logging

from src.db import writer as writer

logger = logging.getLogger(__name__)

PAIRS: tuple[str, ...] = ("EURUSD", "USDJPY", "USDINR")
DEFAULT_LIMIT_PER_PAIR = 1260
_WRITE_RETIRED_MESSAGE = (
    "Synthetic risk-reversal publication is retired. A versioned replay using "
    "observed OTC 25-delta risk-reversal data is required."
)


def backfill_risk_reversal_proxy(
    *,
    dry_run: bool = True,
    limit_per_pair: int = DEFAULT_LIMIT_PER_PAIR,
) -> tuple[int, int]:
    """Inspect bounded signal history without changing published data.

    The tuple is retained for callers of the former command. Its values are
    ``(signal_rows_inspected, regime_calls_changed)``; the second value is
    always zero because this retired path cannot publish or revise calls.
    """

    if dry_run is not True:
        raise RuntimeError(_WRITE_RETIRED_MESSAGE)
    if isinstance(limit_per_pair, bool) or not isinstance(limit_per_pair, int):
        raise ValueError("limit_per_pair must be a positive integer")
    if limit_per_pair <= 0:
        raise ValueError("limit_per_pair must be a positive integer")

    inspected = 0
    for pair in PAIRS:
        rows = writer.get_historical_signals(pair, limit=limit_per_pair)
        inspected += len(rows)
        logger.info(
            "Read-only inspection found %d historical signal rows for %s "
            "(bounded at %d)",
            len(rows),
            pair,
            limit_per_pair,
        )

    return inspected, 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect rows formerly targeted by the retired risk-reversal backfill"
    )
    parser.add_argument(
        "--limit-per-pair",
        type=int,
        default=DEFAULT_LIMIT_PER_PAIR,
        help="Maximum historical signal rows to inspect for each locked pair",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    signals_seen, calls_changed = backfill_risk_reversal_proxy(
        limit_per_pair=args.limit_per_pair
    )
    print(
        f"signal_rows_inspected={signals_seen} "
        f"regime_calls_changed={calls_changed}"
    )
