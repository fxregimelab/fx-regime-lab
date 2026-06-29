"""P1-T1: Historical validation backfill.

Backfills T+5/T+20 validation metrics for all regime_calls that lack
validation_log entries.  Uses historical_prices as the primary spot source
with yfinance fallback for missing dates.

Idempotent: re-running produces zero duplicates.
"""

from __future__ import annotations

import argparse
import datetime
import logging
from typing import Any

from src.backfill.historical_fetcher import fetch_historical_spot_yfinance
from src.db import writer
from src.validation.calculator import compute_horizon_metrics, horizon_metrics_to_payload
from src.validation.calendar import add_trading_days

logger = logging.getLogger(__name__)


def _date_from_raw(raw: Any) -> datetime.date:
    if isinstance(raw, datetime.date):
        return raw
    return datetime.date.fromisoformat(str(raw)[:10])


def get_spot_price(pair: str, target_date: datetime.date) -> float | None:
    """Read spot ``close`` from ``historical_prices``.  Fallback to yfinance."""
    row = writer.get_historical_price_for_date(pair, target_date.isoformat())
    if row is not None and row.get("close") is not None:
        return float(row["close"])

    # yfinance fallback — fetch a small window around the target date
    logger.info(
        "historical_prices miss for %s on %s; falling back to yfinance",
        pair,
        target_date.isoformat(),
    )
    bars = fetch_historical_spot_yfinance(
        pair,
        start=target_date,
        end=target_date,
    )
    for b in bars:
        if b.date == target_date:
            return float(b.close)
    # Weekend/holiday gap: use nearest earlier bar
    for b in sorted(bars, key=lambda x: x.date, reverse=True):
        if b.date <= target_date:
            return float(b.close)
    return None


def backfill_validation_for_call(
    call: dict[str, Any],
    *,
    dry_run: bool = False,
    as_of_date: datetime.date | None = None,
) -> bool:
    """Backfill validation metrics for a single regime call.

    Args:
        call: Regime call dict from ``regime_calls``.
        dry_run: If True, compute but do not write.
        as_of_date: Reference date for horizon reachability.  Defaults to today.

    Returns:
        True if the call was processed (written or skipped due to existing
        validation), False if horizon prices were missing.
    """
    call_id = call.get("id")
    call_date = _date_from_raw(call.get("date"))
    pair = str(call.get("pair"))
    predicted = str(call.get("rate_signal") or "")
    confidence = float(call.get("confidence") or 0.0)

    t5_date = add_trading_days(call_date, 5)
    t20_date = add_trading_days(call_date, 20)
    today = as_of_date if as_of_date is not None else datetime.date.today()

    # ── Idempotency check ─────────────────────────────────────────────────
    if call_id is not None:
        existing = writer.get_validation_log_entry(call_date, pair)
        if existing is not None and existing.get("brier_score_t5") is not None:
            logger.debug(
                "Skip backfill for %s %s: already validated", pair, call_date.isoformat()
            )
            return True

    # ── Spot at call date (S₀) ────────────────────────────────────────────
    s0 = get_spot_price(pair, call_date)
    if s0 is None:
        logger.warning(
            "Backfill skip: missing S0 for %s on %s", pair, call_date.isoformat()
        )
        return False

    payload: dict[str, Any] = {
        "call_date": call_date.isoformat(),
        "date": call_date.isoformat(),
        "pair": pair,
        "predicted_direction": predicted,
        "predicted_regime": call.get("regime"),
        "confidence": confidence,
    }
    if call_id is not None:
        payload["call_id"] = call_id

    # ── T+5 horizon ───────────────────────────────────────────────────────
    if today >= t5_date:
        s5 = get_spot_price(pair, t5_date)
        metrics_t5 = compute_horizon_metrics(s0, s5, predicted, confidence, pair)
        if metrics_t5 is not None:
            payload.update(horizon_metrics_to_payload(metrics_t5, "t5"))
        else:
            logger.warning(
                "Backfill skip T+5: missing S5 for %s on %s",
                pair,
                t5_date.isoformat(),
            )

    # ── T+20 horizon ──────────────────────────────────────────────────────
    if today >= t20_date:
        s20 = get_spot_price(pair, t20_date)
        metrics_t20 = compute_horizon_metrics(s0, s20, predicted, confidence, pair)
        if metrics_t20 is not None:
            payload.update(horizon_metrics_to_payload(metrics_t20, "t20"))
        else:
            logger.warning(
                "Backfill skip T+20: missing S20 for %s on %s",
                pair,
                t20_date.isoformat(),
            )

    has_t5 = payload.get("log_return_t5_bps") is not None
    has_t20 = payload.get("log_return_t20_bps") is not None
    if not has_t5 and not has_t20:
        logger.warning(
            "Backfill skip %s %s: no horizon prices available",
            pair,
            call_date.isoformat(),
        )
        return False

    if dry_run:
        logger.info(
            "[DRY-RUN] Would write validation for %s %s (T+5=%s T+20=%s)",
            pair,
            call_date.isoformat(),
            has_t5,
            has_t20,
        )
        return True

    writer.write_validation_row(payload)
    logger.info(
        "Backfilled validation for %s %s (T+5=%s T+20=%s)",
        pair,
        call_date.isoformat(),
        has_t5,
        has_t20,
    )
    return True


def run_backfill_all(
    limit: int | None = None,
    *,
    dry_run: bool = False,
    as_of_date: datetime.date | None = None,
) -> tuple[int, int]:
    """Backfill all unvalidated regime calls.

    Args:
        limit: Backfill only N oldest unvalidated calls.
        dry_run: Compute but do not write.
        as_of_date: Reference date for horizon reachability.  Defaults to today.

    Returns:
        ``(processed, skipped)`` where *processed* counts calls that were
        written (or already existed) and *skipped* counts calls where horizon
        prices were missing.
    """
    calls = writer.get_unvalidated_regime_calls(limit=limit)
    logger.info("Backfill: %d unvalidated calls found", len(calls))

    processed = 0
    skipped = 0
    pair_counts: dict[str, int] = {}

    for call in calls:
        pair = str(call.get("pair"))
        ok = backfill_validation_for_call(call, dry_run=dry_run, as_of_date=as_of_date)
        if ok:
            processed += 1
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
        else:
            skipped += 1

    total = processed + skipped
    logger.info(
        "Backfill complete: %d/%d processed, %d skipped (%s)",
        processed,
        total,
        skipped,
        ", ".join(f"{k}: {v}" for k, v in sorted(pair_counts.items())),
    )
    return processed, skipped


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Validation backfill for historical regime calls")
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write")
    parser.add_argument("--limit", type=int, help="Backfill only N oldest unvalidated calls")
    args = parser.parse_args()

    processed, skipped = run_backfill_all(limit=args.limit, dry_run=args.dry_run)
    logger.info("Backfill complete: %d processed, %d skipped", processed, skipped)
