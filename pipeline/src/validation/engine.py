"""Live validation scan using immutable publication and close evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

from src.db import writer
from src.types import load_universe
from src.validation.calculator import brier_score as _canonical_brier_score
from src.validation.calculator import directional_correctness
from src.validation.calculator import log_return_bps as _canonical_log_return_bps
from src.validation.calculator import realized_direction as _canonical_realized_direction
from src.validation.coverage import ValidationRunResult, evaluate_validation_population

_VALIDATION_PAIRS = ("EURUSD", "USDJPY", "USDINR")


def _write_validation_rows(rows: Sequence[Mapping[str, Any]]) -> None:
    for row in rows:
        writer.write_validation_row(row)


def log_return_bps(s0: float, sh: float) -> float:
    """Compatibility wrapper for the canonical market-return calculation."""
    return _canonical_log_return_bps(s0, sh)


def realized_direction(bps: float, deadband: float = 5.0) -> str:
    """Compatibility wrapper for the canonical realized direction."""
    return _canonical_realized_direction(bps, deadband)


def is_correct(predicted: str, realized: str) -> bool:
    """Check whether a directional prediction matches the realized move."""
    return bool(directional_correctness(predicted, realized))


def brier_score(confidence: float, correct: bool) -> float | None:
    """Compatibility wrapper for the canonical binary Brier score."""
    return _canonical_brier_score(confidence, correct)


def run_validation(as_of_date: date | None = None) -> ValidationRunResult:
    """Evaluate the complete published population and report coverage health."""
    as_of = as_of_date or datetime.now(UTC).date()
    universe = load_universe()
    pairs = [
        pair
        for pair in _VALIDATION_PAIRS
        if isinstance(universe.get(pair), dict)
        and universe[pair].get("class") == "FX"
    ]

    populations = [
        (pair, writer.get_historical_regime_calls(pair, limit=None)) for pair in pairs
    ]
    result = evaluate_validation_population(
        populations,
        as_of,
        read_existing=writer.get_validation_log_for_call,
        read_entry=writer.get_publication_signal_for_call,
        read_price=lambda requested_pair, target: (
            writer.get_exact_historical_price_for_date(
                requested_pair, target.isoformat()
            )
        ),
        persist_rows=_write_validation_rows,
    )
    missing_pairs = [pair for pair in _VALIDATION_PAIRS if pair not in pairs]
    if missing_pairs:
        result.add_limitation(f"missing_pair_definitions={','.join(missing_pairs)}")
    return result
