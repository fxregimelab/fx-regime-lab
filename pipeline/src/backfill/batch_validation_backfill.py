"""Batch replay through the shared immutable-evidence evaluator."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable, Mapping
from datetime import date
from typing import Any

from src.db import writer
from src.validation.calculator import (
    brier_score,
    directional_correctness,
    realized_direction,
    validate_probability,
)
from src.validation.evaluator import evaluate_call, normalize_call_id

logger = logging.getLogger(__name__)

_VALIDATION_PAIRS = ("EURUSD", "USDJPY", "USDINR")


def is_correct(predicted: str, realized: str) -> bool:
    return bool(directional_correctness(predicted, realized))


def apply_dead_band(bps: float, predicted: str) -> str:
    correct = directional_correctness(predicted, realized_direction(bps))
    if correct is None:
        return "NEUTRAL"
    return "CORRECT" if correct else "WRONG"


def compute_brier_score(conviction: float, outcome: str) -> float | None:
    probability = validate_probability(conviction)
    if outcome == "CORRECT":
        return brier_score(probability, True)
    if outcome == "WRONG":
        return brier_score(probability, False)
    if outcome == "NEUTRAL":
        return None
    raise ValueError(f"unsupported outcome: {outcome!r}")


def _get_spot(prices: Mapping[date, float], target: date) -> float | None:
    """Compatibility helper that permits only an exact calendar-date key."""
    return prices.get(target)


def _build_validation_rows(
    calls: list[dict[str, Any]],
    as_of: date,
    *,
    read_existing: Callable[[int], Mapping[str, Any] | None],
    read_entry: Callable[[int], Mapping[str, Any] | None],
    read_price: Callable[[str, date], Mapping[str, Any] | None],
) -> list[dict[str, Any]]:
    """Evaluate calls in order using the same readers as live validation."""
    rows: list[dict[str, Any]] = []
    for call in calls:
        try:
            call_id = normalize_call_id(call)
        except ValueError:
            logger.warning("Batch replay skip: missing persisted call_id")
            continue
        existing = read_existing(call_id)
        row = evaluate_call(
            call,
            as_of,
            existing,
            read_entry=read_entry,
            read_price=read_price,
        )
        if row is not None:
            rows.append(row)
    return rows


def _batch_insert(rows: list[dict[str, Any]], batch_size: int = 1000) -> None:
    """Persist rows through the canonical transactional writer."""
    for offset in range(0, len(rows), batch_size):
        batch = rows[offset : offset + batch_size]
        for row in batch:
            writer.write_validation_row(row)
        logger.info("Inserted batch %d-%d", offset, offset + len(batch) - 1)


def run_batch_backfill(
    *,
    dry_run: bool = False,
    as_of: date | None = None,
) -> tuple[int, int]:
    """Replay the complete three-pair call history without private connections."""
    evaluation_date = as_of or date.today()
    calls = [
        call
        for pair in _VALIDATION_PAIRS
        for call in writer.get_historical_regime_calls(pair, limit=None)
    ]
    rows = _build_validation_rows(
        calls,
        evaluation_date,
        read_existing=writer.get_validation_log_for_call,
        read_entry=writer.get_publication_signal_for_call,
        read_price=lambda pair, target: writer.get_exact_historical_price_for_date(
            pair, target.isoformat()
        ),
    )
    logger.info("Built %d validation revisions from %d calls", len(rows), len(calls))
    if not dry_run:
        _batch_insert(rows)
    return len(rows), len(calls) - len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    args = parser.parse_args()
    processed, skipped = run_batch_backfill(dry_run=args.dry_run, as_of=args.as_of)
    logger.info("Done: %d revisions, %d unchanged or unavailable", processed, skipped)


if __name__ == "__main__":
    main()
