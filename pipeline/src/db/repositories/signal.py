"""Signal table repository (internal — use ``src.db.writer``)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from supabase import Client

from src.db.repositories.common import date_iso
from src.types import SignalRow


class SignalRepository:
    def __init__(self, client_factory: Callable[[], Client]) -> None:
        self._client_factory = client_factory

    def write_signal_row(self, row: SignalRow) -> None:
        """Upsert signal row with all available metrics."""
        payload: dict[str, Any] = {
            "pair": row.pair,
            "date": date_iso(row.date),
            "rate_diff_2y": row.rate_diff_2y,
            "rate_diff_10y": row.rate_diff_10y,
            "cot_percentile": row.cot_percentile,
            "realized_vol_20d": row.realized_vol_20d,
            "realized_vol_5d": row.realized_vol_5d,
            "implied_vol_30d": row.implied_vol_30d,
            "spot": row.spot,
            "day_change": row.day_change,
            "day_change_pct": row.day_change_pct,
            "cross_asset_vix": row.cross_asset_vix,
            "cross_asset_dxy": row.cross_asset_dxy,
            "cross_asset_oil": row.cross_asset_oil,
            "cross_asset_us10y": row.cross_asset_us10y,
            "cross_asset_gold": row.cross_asset_gold,
            "cross_asset_copper": row.cross_asset_copper,
            "cross_asset_stoxx": row.cross_asset_stoxx,
            "oi_delta": row.oi_delta,
            "volume_rvol": row.volume_rvol,
            "structural_instability": row.structural_instability,
            "breakeven_inflation_10y": row.breakeven_inflation_10y,
            "rate_diff_10y_real": row.rate_diff_10y_real,
            "rate_z_tactical": row.rate_z_tactical,
            "rate_z_structural": row.rate_z_structural,
            "z_blended": row.z_blended,
            "realized_vol_rank": row.realized_vol_rank,
            "skew_alignment": row.skew_alignment,
            "risk_reversal_25d": row.risk_reversal_25d,
            "fpi_flow": row.fpi_flow,
            "cot_net_pos": row.cot_net_pos,
            "cot_asset_mgr_net": row.cot_asset_mgr_net,
            "cot_lev_money_net": row.cot_lev_money_net,
            "ecb_balance_sheet": row.ecb_balance_sheet,
            "bund_btp_spread": row.bund_btp_spread,
            "boj_policy_rate": row.boj_policy_rate,
            "india_vix": row.india_vix,
            "inr_forward_premium": row.inr_forward_premium,
        }
        self._client_factory().table("signals").upsert(
            payload, on_conflict="pair,date"
        ).execute()

    def get_signal_for_pair_date(
        self, pair: str, date_str: str
    ) -> dict[str, Any] | None:
        res = (
            self._client_factory()
            .table("signals")
            .select("*")
            .eq("pair", pair)
            .eq("date", date_str)
            .execute()
        )
        data = cast(list[dict[str, Any]], res.data or [])
        return data[0] if data else None

    def get_historical_signals(
        self, pair: str, limit: int = 1260
    ) -> list[dict[str, Any]]:
        res = (
            self._client_factory()
            .table("signals")
            .select(
                "date,rate_diff_2y,rate_diff_10y,breakeven_inflation_10y,"
                "cot_percentile,realized_vol_5d,realized_vol_20d,oi_delta,spot,cross_asset_us10y",
            )
            .eq("pair", pair)
            .order("date", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], res.data or [])
