"""Backfill call_rationale for all historical regime_calls.

Usage::

    python -m src.backfill.generate_historical_rationale --dry-run
"""

from __future__ import annotations

import argparse
import logging
from datetime import date
from typing import Any, cast

from src.core.regime_persist import _build_call_rationale
from src.db.writer import _client
from src.types import SignalRow

logger = logging.getLogger(__name__)


def _load_historical_calls() -> list[dict[str, Any]]:
    """Load all regime_calls with their IDs, dates, and pairs."""
    out: list[dict[str, Any]] = []
    page_size = 1000
    offset = 0
    while True:
        res = (
            _client()
            .table("regime_calls")
            .select("id,date,pair,signal_composite")
            .order("date")
            .order("pair")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = cast(list[dict[str, Any]], res.data or [])
        if not rows:
            break
        for row in rows:
            d = date.fromisoformat(str(row["date"])[:10])
            comp = row["signal_composite"]
            out.append({
                "id": int(row["id"]),
                "date": d,
                "pair": row["pair"],
                "signal_composite": float(comp) if comp is not None else 0.0,
            })
        if len(rows) < page_size:
            break
        offset += page_size
    return out


def _load_signals_by_call(calls: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Load signal rows keyed by regime_call id via (date, pair) join."""
    pairs = sorted({c["pair"] for c in calls})
    dates = sorted({c["date"] for c in calls})
    if not pairs or not dates:
        return {}

    sig_rows: list[dict[str, Any]] = []
    page_size = 1000
    offset = 0
    while True:
        res = (
            _client()
            .table("signals")
            .select(
                "date,pair,cot_percentile,realized_vol_20d,realized_vol_5d,"
                "oi_delta,rate_z_tactical,rate_z_structural,fpi_flow,"
                "ecb_balance_sheet,bund_btp_spread,cot_asset_mgr_net,cot_lev_money_net,"
                "structural_instability,volume_rvol"
            )
            .in_("pair", pairs)
            .gte("date", min(dates).isoformat())
            .lte("date", max(dates).isoformat())
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = cast(list[dict[str, Any]], res.data or [])
        if not batch:
            break
        sig_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    sig_by_key: dict[tuple[date, str], dict[str, Any]] = {}

    def _f(val: Any) -> float | None:
        return float(val) if val is not None else None

    def _i(val: Any) -> int | None:
        return int(val) if val is not None else None

    for row in sig_rows:
        d = date.fromisoformat(str(row["date"])[:10])
        key = (d, row["pair"])
        sig_by_key[key] = {
            "date": d,
            "pair": row["pair"],
            "cot_percentile": _f(row.get("cot_percentile")),
            "realized_vol_20d": _f(row.get("realized_vol_20d")),
            "realized_vol_5d": _f(row.get("realized_vol_5d")),
            "oi_delta": _i(row.get("oi_delta")),
            "rate_z_tactical": _f(row.get("rate_z_tactical")),
            "rate_z_structural": _f(row.get("rate_z_structural")),
            "fpi_flow": _f(row.get("fpi_flow")),
            "ecb_balance_sheet": _f(row.get("ecb_balance_sheet")),
            "bund_btp_spread": _f(row.get("bund_btp_spread")),
            "cot_asset_mgr_net": _i(row.get("cot_asset_mgr_net")),
            "cot_lev_money_net": _i(row.get("cot_lev_money_net")),
            "structural_instability": (
                bool(row.get("structural_instability"))
                if row.get("structural_instability") is not None
                else False
            ),
            "volume_rvol": _f(row.get("volume_rvol")),
        }

    out: dict[int, dict[str, Any]] = {}
    for call in calls:
        key = (call["date"], call["pair"])
        if key in sig_by_key:
            out[call["id"]] = sig_by_key[key]
    return out


def run_backfill(*, dry_run: bool = False, batch_size: int = 500) -> tuple[int, int]:
    calls = _load_historical_calls()
    logger.info("Loaded %d regime_calls", len(calls))

    signals_by_call = _load_signals_by_call(calls)
    logger.info("Matched %d signal rows", len(signals_by_call))

    written = 0
    skipped = 0
    batch: list[dict[str, Any]] = []

    from postgrest.exceptions import APIError

    for call in calls:
        call_id = call["id"]
        sig_dict = signals_by_call.get(call_id)
        if sig_dict is None:
            skipped += 1
            continue

        sig = SignalRow(
            pair=sig_dict["pair"],
            date=sig_dict["date"],
            rate_diff_2y=None,
            rate_diff_10y=None,
            cot_percentile=sig_dict.get("cot_percentile"),
            realized_vol_20d=sig_dict.get("realized_vol_20d"),
            realized_vol_5d=sig_dict.get("realized_vol_5d"),
            implied_vol_30d=None,
            spot=None,
            day_change=None,
            day_change_pct=None,
            cross_asset_vix=None,
            cross_asset_dxy=None,
            cross_asset_oil=None,
            cross_asset_us10y=None,
            cross_asset_gold=None,
            cross_asset_copper=None,
            cross_asset_stoxx=None,
            oi_delta=sig_dict.get("oi_delta"),
            volume_rvol=sig_dict.get("volume_rvol"),
            structural_instability=sig_dict.get("structural_instability", False),
            rate_z_tactical=sig_dict.get("rate_z_tactical"),
            rate_z_structural=sig_dict.get("rate_z_structural"),
            fpi_flow=sig_dict.get("fpi_flow"),
            ecb_balance_sheet=sig_dict.get("ecb_balance_sheet"),
            bund_btp_spread=sig_dict.get("bund_btp_spread"),
            cot_asset_mgr_net=sig_dict.get("cot_asset_mgr_net"),
            cot_lev_money_net=sig_dict.get("cot_lev_money_net"),
        )

        rationale = _build_call_rationale(
            call_id=call_id,
            call_date=call["date"],
            pair=call["pair"],
            signals=sig,
            composite=call["signal_composite"],
        )
        batch.append(rationale)

        if len(batch) >= batch_size:
            if not dry_run:
                try:
                    _client().table("call_rationale").insert(batch).execute()
                except APIError as exc:
                    code = getattr(exc, "code", "")
                    if code in ("23505", "409"):
                        logger.warning("Batch conflict, falling back to single inserts")
                        for payload in batch:
                            try:
                                _client().table("call_rationale").insert(payload).execute()
                            except APIError:
                                pass
                    else:
                        raise
            written += len(batch)
            batch = []
            logger.info("Processed %d rationale rows", written)

    if batch:
        if not dry_run:
            try:
                _client().table("call_rationale").insert(batch).execute()
            except APIError as exc:
                code = getattr(exc, "code", "")
                if code in ("23505", "409"):
                    logger.warning("Batch conflict, falling back to single inserts")
                    for payload in batch:
                        try:
                            _client().table("call_rationale").insert(payload).execute()
                        except APIError:
                            pass
                else:
                    raise
        written += len(batch)

    logger.info("Backfill complete: %d written, %d skipped", written, skipped)
    return written, skipped


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    written, skipped = run_backfill(dry_run=args.dry_run, batch_size=args.batch_size)
    logger.info("Done: %d written, %d skipped", written, skipped)


if __name__ == "__main__":
    main()
