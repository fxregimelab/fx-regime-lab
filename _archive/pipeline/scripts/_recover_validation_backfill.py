"""Recover from a partial validation_log backfill.

The original bulk backfill succeeded in marking old rows superseded but failed
before inserting the corrected versions because the production unique index on
validation_log.call_id was not partial on is_superseded. After the index is
fixed, this script re-inserts corrected rows for every superseded row that does
not already have a current (non-superseded) replacement, and re-corrects the
small number of rows that were left non-superseded.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping
from datetime import date
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
        return {cost_key: cost_bps} if row.get(cost_key) != cost_bps else None

    ret = float(ret)
    net_ret = ret - cost_bps
    actual = str(row.get(actual_key) or "").upper()

    updates: dict[str, Any] = {cost_key: cost_bps}

    if actual:
        correct_gross = is_correct(pred, actual)
        updates[correct_key] = correct_gross
        updates[legacy_correct_key] = correct_gross

    updates[net_ret_key] = net_ret
    updates[net_correct_key] = _is_correct_net(pred, net_ret)

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
    new_row = dict(row)
    new_row.update(updates)
    for drop_key in ("id", "created_at", "is_superseded"):
        new_row.pop(drop_key, None)
    return new_row


def main(dry_run: bool = False) -> None:
    logging.basicConfig(level=logging.INFO)
    client = writer._client()

    # Fetch every row in the ledger (superseded and current).
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        chunk = (
            client.table("validation_log")
            .select("*")
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

    logger.info("Loaded %d validation_log rows", len(rows))

    by_id = {r["id"]: r for r in rows}
    current_by_call_id: dict[Any, dict[str, Any]] = {}
    superseded_by_call_id: dict[Any, dict[str, Any]] = {}
    current_without_call_id: list[dict[str, Any]] = []
    superseded_without_call_id: list[dict[str, Any]] = []

    for r in rows:
        if r.get("is_superseded"):
            if r.get("call_id") is not None:
                superseded_by_call_id[r["call_id"]] = r
            else:
                superseded_without_call_id.append(r)
        else:
            if r.get("call_id") is not None:
                current_by_call_id[r["call_id"]] = r
            else:
                current_without_call_id.append(r)

    logger.info(
        "Current rows: %d with call_id, %d without; Superseded sources: %d with call_id, %d without",
        len(current_by_call_id),
        len(current_without_call_id),
        len(superseded_by_call_id),
        len(superseded_without_call_id),
    )

    old_ids_to_supersede: list[str | int] = []
    rows_to_insert: list[dict[str, Any]] = []

    # 1. Re-correct rows that are still current.
    for row in list(current_by_call_id.values()) + current_without_call_id:
        pair = str(row.get("pair") or "")
        cost_bps = COST_BPS_ROUND_TRIP.get(pair, 0.5)
        updates: dict[str, Any] = {}
        for horizon in ("t5", "t20"):
            horizon_updates = _recompute_horizon(row, horizon, cost_bps)
            if horizon_updates:
                updates.update(horizon_updates)
        if not updates or not _needs_update(row, updates):
            continue
        old_ids_to_supersede.append(row["id"])
        rows_to_insert.append(_build_corrected_row(row, updates))

    today_str = date.today().isoformat()

    # 2. Re-insert corrected versions for superseded rows that have no current replacement.
    for row in list(superseded_by_call_id.values()) + superseded_without_call_id:
        call_id = row.get("call_id")
        if call_id is not None and call_id in current_by_call_id:
            # A current row (possibly just corrected) already exists for this call.
            continue
        call_date = str(row.get("call_date") or "")
        if call_date > today_str:
            # Do not resurrect intentionally superseded future-dated rows (e.g. test fixtures).
            continue
        pair = str(row.get("pair") or "")
        cost_bps = COST_BPS_ROUND_TRIP.get(pair, 0.5)
        updates: dict[str, Any] = {}
        for horizon in ("t5", "t20"):
            horizon_updates = _recompute_horizon(row, horizon, cost_bps)
            if horizon_updates:
                updates.update(horizon_updates)
        if not updates:
            updates = {"cost_bps_t5": cost_bps, "cost_bps_t20": cost_bps}
        rows_to_insert.append(_build_corrected_row(row, updates))

    logger.info(
        "Recovery plan: supersede %d current rows, insert %d corrected rows (dry_run=%s)",
        len(old_ids_to_supersede),
        len(rows_to_insert),
        dry_run,
    )

    if dry_run:
        return

    if old_ids_to_supersede:
        for i in range(0, len(old_ids_to_supersede), 500):
            chunk = old_ids_to_supersede[i : i + 500]
            client.table("validation_log").update({"is_superseded": True}).in_(
                "id", chunk
            ).execute()
        logger.info("Superseded %d current rows.", len(old_ids_to_supersede))

    if rows_to_insert:
        inserted = 0
        batch_size = 100
        for i in range(0, len(rows_to_insert), batch_size):
            batch = rows_to_insert[i : i + batch_size]
            try:
                writer._strip_unknown_validation_columns(batch)
                inserted += len(batch)
                logger.info("Inserted batch %d/%d (%d rows).", i // batch_size + 1, (len(rows_to_insert) + batch_size - 1) // batch_size, len(batch))
            except Exception:
                # Try smaller batches before giving up.
                logger.warning("Batch of %d failed; retrying one-by-one.", len(batch))
                for single in batch:
                    writer._strip_unknown_validation_columns([single])
                    inserted += 1
        logger.info("Inserted %d corrected rows total.", inserted)
    else:
        logger.info("No rows to insert.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recover validation_log after partial supersede backfill."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count planned corrections without writing.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
