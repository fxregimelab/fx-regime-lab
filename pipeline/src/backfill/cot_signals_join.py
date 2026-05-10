"""Join historical COT data into ``signals`` table.

Computes COT percentile (52-week), lev_money_net, asset_mgr_net,
net_pos, and OI delta for each signals row, then UPDATEs directly.
"""

from __future__ import annotations

import argparse
import logging
import ssl
from collections import defaultdict
from datetime import date
from typing import Any

import pg8000.native

logger = logging.getLogger(__name__)


def _pg_conn() -> Any:
    ctx = ssl._create_unverified_context()
    return pg8000.native.Connection(
        host="db.weaaacohvzzgkgxzpaee.supabase.co",
        database="postgres",
        user="postgres",
        password="FXRegimelab04553",
        ssl_context=ctx,
    )


def _load_cot_rows() -> dict[str, list[dict[str, Any]]]:
    """Load historical_cot rows grouped by pair, sorted by date ascending."""
    conn = _pg_conn()
    result = conn.run(
        "SELECT date, pair, net_long, lev_money_net, asset_mgr_net, open_interest "
        "FROM historical_cot ORDER BY pair, date"
    )
    conn.close()

    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in result:
        d = row[0] if isinstance(row[0], date) else date.fromisoformat(str(row[0])[:10])
        by_pair[row[1]].append({
            "date": d,
            "net_long": int(row[2]) if row[2] is not None else None,
            "lev_money_net": int(row[3]) if row[3] is not None else None,
            "asset_mgr_net": int(row[4]) if row[4] is not None else None,
            "open_interest": int(row[5]) if row[5] is not None else None,
        })
    return dict(by_pair)


def _load_signal_dates() -> list[dict[str, Any]]:
    conn = _pg_conn()
    result = conn.run(
        "SELECT id, pair, date FROM signals "
        "WHERE pair IN ('EURUSD','USDJPY','USDINR') ORDER BY pair, date"
    )
    conn.close()
    rows: list[dict[str, Any]] = []
    for row in result:
        d = row[2] if isinstance(row[2], date) else date.fromisoformat(str(row[2])[:10])
        rows.append({"id": int(row[0]), "pair": row[1], "date": d})
    return rows


def _percentile_rank(value: int, series: list[int]) -> float | None:
    if not series:
        return None
    # Rank = number of values <= current / total
    rank = sum(1 for v in series if v <= value)
    return round(rank / len(series) * 100, 1)


def _build_updates(
    signals: list[dict[str, Any]],
    cot_by_pair: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []

    for sig in signals:
        pair = sig["pair"]
        sdate = sig["date"]
        cot_series = cot_by_pair.get(pair, [])
        if not cot_series:
            continue

        # Find nearest prior COT report date
        best: dict[str, Any] | None = None
        best_prev: dict[str, Any] | None = None
        for idx, cot in enumerate(cot_series):
            if cot["date"] <= sdate:
                best = cot
                best_prev = cot_series[idx - 1] if idx > 0 else None
            else:
                break

        if best is None:
            continue

        # 52-week lookback for percentile (up to and including best date)
        lookback = [
            c["net_long"] for c in cot_series
            if c["date"] <= best["date"]
            and c["date"] > best["date"].replace(year=best["date"].year - 1)
            and c["net_long"] is not None
        ]
        cot_percentile = None
        if best["net_long"] is not None and lookback:
            cot_percentile = _percentile_rank(best["net_long"], lookback)

        oi_delta = None
        if (
            best["open_interest"] is not None
            and best_prev is not None
            and best_prev["open_interest"] is not None
        ):
            oi_delta = int(best["open_interest"] - best_prev["open_interest"])

        updates.append({
            "id": sig["id"],
            "cot_percentile": cot_percentile,
            "cot_lev_money_net": best["lev_money_net"],
            "cot_asset_mgr_net": best["asset_mgr_net"],
            "cot_net_pos": best["net_long"],
            "oi_delta": oi_delta,
        })

    return updates


def _batch_update(updates: list[dict[str, Any]], batch_size: int = 500) -> int:
    if not updates:
        return 0
    conn = _pg_conn()
    total = 0
    for i in range(0, len(updates), batch_size):
        batch = updates[i : i + batch_size]
        # Build a single CASE-based UPDATE for the batch
        ids = [u["id"] for u in batch]
        # percentile
        case_percentile = " ".join(
            f"WHEN {u['id']} THEN {u['cot_percentile']}"
            if u["cot_percentile"] is not None
            else f"WHEN {u['id']} THEN NULL"
            for u in batch
        )
        case_lev = " ".join(
            f"WHEN {u['id']} THEN {u['cot_lev_money_net']}"
            if u["cot_lev_money_net"] is not None
            else f"WHEN {u['id']} THEN NULL"
            for u in batch
        )
        case_asset = " ".join(
            f"WHEN {u['id']} THEN {u['cot_asset_mgr_net']}"
            if u["cot_asset_mgr_net"] is not None
            else f"WHEN {u['id']} THEN NULL"
            for u in batch
        )
        case_net = " ".join(
            f"WHEN {u['id']} THEN {u['cot_net_pos']}"
            if u["cot_net_pos"] is not None
            else f"WHEN {u['id']} THEN NULL"
            for u in batch
        )
        case_oi = " ".join(
            f"WHEN {u['id']} THEN {u['oi_delta']}"
            if u["oi_delta"] is not None
            else f"WHEN {u['id']} THEN NULL"
            for u in batch
        )

        sql = f"""
        UPDATE signals SET
            cot_percentile = CASE id {case_percentile} END,
            cot_lev_money_net = CASE id {case_lev} END,
            cot_asset_mgr_net = CASE id {case_asset} END,
            cot_net_pos = CASE id {case_net} END,
            oi_delta = CASE id {case_oi} END
        WHERE id = ANY(:ids)
        """
        conn.run(sql, ids=ids)
        total += len(batch)
    conn.close()
    return total


def run_join(*, dry_run: bool = False) -> tuple[int, int]:
    cot_by_pair = _load_cot_rows()
    logger.info("Loaded COT data for %d pairs", len(cot_by_pair))
    for pair, rows in cot_by_pair.items():
        logger.info("  %s: %d rows", pair, len(rows))

    signals = _load_signal_dates()
    logger.info("Loaded %d signals rows", len(signals))

    updates = _build_updates(signals, cot_by_pair)
    logger.info("Built %d updates", len(updates))

    if dry_run:
        logger.info("[DRY-RUN] Would update %d signals rows", len(updates))
        return len(updates), 0

    updated = _batch_update(updates)
    logger.info("Updated %d signals rows", updated)
    return updated, len(signals) - updated


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    updated, skipped = run_join(dry_run=args.dry_run)
    logger.info("Done: %d updated, %d skipped", updated, skipped)


if __name__ == "__main__":
    main()
