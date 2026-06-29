"""Backfill validation_log with consistent costs, net returns, and net correctness.

This script corrects the data-quality issues found by _audit_validation.py:
- Re-applies the current COST_BPS_ROUND_TRIP to every row.
- Recomputes log_return_net_bps_* and correct_net_* from cost-adjusted returns.
- Repairs NEUTRAL rows that were incorrectly marked correct.
- Repairs the one USDJPY Brier-score inconsistency.

All DB writes go through src.db.writer.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping
from typing import Any

from dotenv import load_dotenv

load_dotenv("../.env.local")

from src.db import writer
from src.validation.engine import (
    COST_BPS_ROUND_TRIP,
    brier_score,
    is_correct,
    realized_direction,
)

logger = logging.getLogger(__name__)


def _is_correct_net(predicted: str, bps_net: float) -> bool:
    """Mirror of engine._is_correct_net (private, duplicated here for safety)."""
    p = predicted.strip().upper()
    if p == "BULLISH":
        return bps_net > 0.0
    if p == "BEARISH":
        return bps_net < 0.0
    if p == "NEUTRAL":
        return realized_direction(bps_net) == "NEUTRAL"
    return False


def _recompute_horizon(
    row: Mapping[str, Any],
    horizon: str,
    cost_bps: float,
) -> dict[str, Any] | None:
    """Return a dict of fields to update for one horizon, or None if nothing changes."""
    pred = str(row.get("predicted_direction") or "").strip().upper()
    if not pred:
        return None

    ret_key = f"log_return_{horizon}_bps"
    actual_key = f"actual_direction_{horizon}"
    correct_key = f"correct_{horizon}"
    brier_key = f"brier_score_{horizon}"
    net_ret_key = f"log_return_net_bps_{horizon}"
    net_correct_key = f"correct_net_{horizon}"
    cost_key = f"cost_bps_{horizon}"
    legacy_correct_key = f"correct_{horizon.replace('t', '')}d"
    legacy_brier_key = f"brier_{horizon.replace('t', '')}d"
    legacy_ret_key = f"actual_return_{horizon.replace('t', '')}d"

    ret = row.get(ret_key)
    if ret is None:
        # Horizon not matured; still enforce consistent cost if present.
        return {cost_key: cost_bps} if row.get(cost_key) != cost_bps else None

    ret = float(ret)
    net_ret = ret - cost_bps
    actual = str(row.get(actual_key) or "").upper()

    updates: dict[str, Any] = {cost_key: cost_bps}

    # Gross correctness vs actual direction.
    if actual:
        correct_gross = is_correct(pred, actual)
        updates[correct_key] = correct_gross
        updates[legacy_correct_key] = correct_gross

    # Net correctness and net return.
    correct_net = _is_correct_net(pred, net_ret)
    updates[net_ret_key] = net_ret
    updates[net_correct_key] = correct_net

    # Brier: only defined for directional predictions.
    if pred == "NEUTRAL":
        updates[brier_key] = None
        updates[legacy_brier_key] = None
    else:
        confidence = float(row.get("confidence") or 0.0)
        correct_for_brier = updates.get(correct_key, row.get(correct_key))
        if correct_for_brier is not None:
            updates[brier_key] = brier_score(confidence, correct_for_brier)
            updates[legacy_brier_key] = updates[brier_key]
            updates[legacy_ret_key] = ret / 10_000.0

    return updates


def _needs_update(row: Mapping[str, Any], updates: Mapping[str, Any]) -> bool:
    for key, value in updates.items():
        if row.get(key) != value:
            return True
    return False


def _build_corrected_row(
    row: Mapping[str, Any], updates: Mapping[str, Any]
) -> dict[str, Any]:
    """Return a full validation_log payload with corrections applied.

    Drops the old id/created_at/is_superseded so the DB assigns fresh values.
    """
    new_row = dict(row)
    new_row.update(updates)
    # Remove ledger bookkeeping fields so the new row is treated as a fresh insert.
    for drop_key in ("id", "created_at", "is_superseded"):
        new_row.pop(drop_key, None)
    return new_row


def main(dry_run: bool = False) -> None:
    logging.basicConfig(level=logging.INFO)

    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        chunk = (
            writer._client()
            .table("validation_log")
            .select("*")
            .eq("is_superseded", False)
            .range(offset, offset + 999)
            .execute()
            .data
        )
        if not chunk:
            break
        rows.extend(chunk)
        offset += 1000
        if len(chunk) < 1000:
            break

    logger.info("Loaded %d current validation_log rows", len(rows))

    old_ids: list[str | int] = []
    new_rows: list[dict[str, Any]] = []
    skipped = 0

    for row in rows:
        pair = str(row.get("pair") or "")
        cost_bps = COST_BPS_ROUND_TRIP.get(pair, 0.5)

        updates: dict[str, Any] = {}
        for horizon in ("t5", "t20"):
            horizon_updates = _recompute_horizon(row, horizon, cost_bps)
            if horizon_updates:
                updates.update(horizon_updates)

        if not updates or not _needs_update(row, updates):
            skipped += 1
            continue

        old_ids.append(row["id"])
        new_rows.append(_build_corrected_row(row, updates))

    logger.info(
        "Prepared %d corrections, skipped %d rows (dry_run=%s)",
        len(old_ids),
        skipped,
        dry_run,
    )

    if dry_run:
        return

    if not old_ids:
        logger.info("No corrections needed.")
        return

    writer.bulk_rewrite_validation_rows(old_ids, new_rows)
    logger.info("Bulk rewrite complete: %d rows superseded and re-inserted.", len(old_ids))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill validation_log cost/net-return/net-correctness fields."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count corrections without writing to the database.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
