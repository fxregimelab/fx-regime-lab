"""Replay validation from immutable publication and exact close evidence."""

from __future__ import annotations

import argparse
import datetime
import logging
from typing import Any

from src.db import writer
from src.validation.calculator import (
    EVALUATION_VERSION,
    brier_score,
    directional_correctness,
    realized_direction,
    validate_probability,
)
from src.validation.evaluator import evaluate_call, normalize_call_id

logger = logging.getLogger(__name__)


def get_spot_price(pair: str, target_date: datetime.date) -> float | None:
    """Compatibility reader for the exact stored close; no provider fallback."""
    row = writer.get_exact_historical_price_for_date(pair, target_date.isoformat())
    return None if row is None else row.get("close")


def apply_dead_band(bps: float, predicted: str) -> str:
    """Map the canonical directional event to the legacy outcome label."""
    correct = directional_correctness(predicted, realized_direction(bps))
    if correct is None:
        return "NEUTRAL"
    return "CORRECT" if correct else "WRONG"


def compute_brier_score_from_outcome(conviction: float, outcome: str) -> float | None:
    """Calculate the canonical Brier score from a legacy outcome label."""
    probability = validate_probability(conviction)
    if outcome == "CORRECT":
        return brier_score(probability, True)
    if outcome == "WRONG":
        return brier_score(probability, False)
    if outcome == "NEUTRAL":
        return None
    raise ValueError(f"unsupported outcome: {outcome!r}")


def backfill_validation_for_call(
    call: dict[str, Any],
    *,
    dry_run: bool = False,
    as_of_date: datetime.date | None = None,
) -> bool:
    """Evaluate one published call; dry runs perform no write."""
    try:
        call_id = normalize_call_id(call)
    except ValueError:
        logger.warning("Backfill skip: missing persisted call_id")
        return False
    existing = writer.get_validation_log_for_call(call_id)
    row = evaluate_call(
        call,
        as_of_date or datetime.date.today(),
        existing,
        read_entry=writer.get_publication_signal_for_call,
        read_price=lambda pair, target: writer.get_exact_historical_price_for_date(
            pair, target.isoformat()
        ),
    )
    if row is None:
        return bool(
            existing
            and existing.get("call_id") == call_id
            and existing.get("evaluation_version") == EVALUATION_VERSION
            and existing.get("log_return_t5_bps") is not None
            and existing.get("log_return_t20_bps") is not None
        )
    if dry_run:
        logger.info("[DRY-RUN] Would write validation for call %s", call_id)
        return True
    writer.write_validation_row(row)
    logger.info("Backfilled validation for call %s", call_id)
    return True


def run_backfill_all(
    limit: int | None = None,
    *,
    dry_run: bool = False,
    as_of_date: datetime.date | None = None,
) -> tuple[int, int]:
    """Visit the complete incomplete-call backlog, optionally bounded by limit."""
    calls = writer.get_unvalidated_regime_calls(limit=limit)
    processed = 0
    skipped = 0
    for call in calls:
        if backfill_validation_for_call(
            call, dry_run=dry_run, as_of_date=as_of_date
        ):
            processed += 1
        else:
            skipped += 1
    logger.info(
        "Backfill complete: %d/%d processed, %d unavailable",
        processed,
        processed + skipped,
        skipped,
    )
    return processed, skipped


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Validation replay for published calls")
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write")
    parser.add_argument("--limit", type=int, help="Visit only N oldest incomplete calls")
    args = parser.parse_args()
    run_backfill_all(limit=args.limit, dry_run=args.dry_run)
