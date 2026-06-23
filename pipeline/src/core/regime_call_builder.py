"""Assemble a SignalRow and a RegimeCall from an IngestionSnapshot and layer outputs."""

from __future__ import annotations

from typing import Any

from src.regime.classifier import get_regime_category
from src.signals.volatility import compute_rvol
from src.types import (
    Layer2DirectionalOutput,
    Layer3ExecutionOutput,
    RegimeCall,
    SignalRow,
)

from .ingestion_snapshot import IngestionSnapshot


class RegimeCallBuilder:
    """Build ``SignalRow`` and ``RegimeCall`` artifacts from a validated snapshot.

    The builder does not run signal math itself; it takes the computed outputs of
    the three signal layers and assembles the persistence-ready row objects. This
    keeps fetcher/ingestion details isolated from regime-call construction.
    """

    def __init__(self, snapshot: IngestionSnapshot) -> None:
        self.snapshot = snapshot

    def build_signal_row(
        self,
        pair: str,
        *,
        rate_spread_2y: float | None = None,
        rate_spread_10y: float | None = None,
        rate_spread_10y_real: float | None = None,
        rate_z_tactical: float | None = None,
        rate_z_structural: float | None = None,
        z_blended: float | None = None,
        cot_percentile: float | None = None,
        cot_norm: float | None = None,
        realized_vol_20d: float | None = None,
        realized_vol_5d: float | None = None,
        implied_vol_30d: float | None = None,
        vol_norm: float | None = None,
        vol_expanding: bool = False,
        oi_delta: int | None = None,
        oi_norm: float | None = None,
        special_signal: float | None = None,
        fpi_signal: float | None = None,
        fpi_raw: dict[str, Any] | None = None,
        risk_adjusted_carry: float | None = None,
        days_since_cot: int = 0,
        cot_net_pos: int | None = None,
        cot_asset_mgr_net: int | None = None,
        cot_lev_money_net: int | None = None,
        structural_instability: bool = False,
        breakeven_inflation_10y: float | None = None,
        realized_vol_rank: float | None = None,
        skew_alignment: int | None = None,
        risk_reversal_25d: float | None = None,
        risk_reversal_source: str = "PENDING_REAL_DATA",
        historical_us10y: float | None = None,
    ) -> SignalRow:
        """Assemble the signal row for ``pair`` from the snapshot and layer outputs."""

        today_bar = self.snapshot.today_bar_for(pair)
        if today_bar is None:
            raise ValueError(f"No spot bars available for {pair} in snapshot")

        yest_bar = self.snapshot.yesterday_bar_for(pair) or today_bar

        spot = today_bar.close
        day_change = (
            (today_bar.close - yest_bar.close)
            if today_bar.close is not None and yest_bar.close is not None
            else 0.0
        )
        day_change_pct = (
            (day_change / yest_bar.close * 100.0)
            if yest_bar.close not in (None, 0.0)
            else 0.0
        )

        cross = self.snapshot.cross_asset
        us10y_value = self.snapshot.yields.get("us_10y")
        if us10y_value is None:
            us10y_value = historical_us10y

        volumes = [float(b.volume) for b in self.snapshot.spot_bars_for(pair) if b.volume > 0]
        volume_rvol = compute_rvol(volumes)

        fpi_flow: float | None = None
        if fpi_raw is not None:
            fpi_flow = fpi_raw.get("fpi_total_net_cr")

        macro = self.snapshot.macro or {}

        return SignalRow(
            pair=pair,
            date=today_bar.date,
            rate_diff_2y=rate_spread_2y,
            rate_diff_10y=rate_spread_10y,
            cot_percentile=cot_percentile,
            realized_vol_20d=realized_vol_20d,
            realized_vol_5d=realized_vol_5d,
            implied_vol_30d=implied_vol_30d,
            spot=spot,
            day_change=day_change,
            day_change_pct=day_change_pct,
            cross_asset_vix=cross.get("vix"),
            cross_asset_dxy=cross.get("dxy"),
            cross_asset_oil=cross.get("oil"),
            cross_asset_us10y=us10y_value,
            cross_asset_gold=cross.get("gold"),
            cross_asset_copper=cross.get("copper"),
            cross_asset_stoxx=cross.get("stoxx"),
            oi_delta=oi_delta,
            volume_rvol=volume_rvol,
            structural_instability=structural_instability,
            breakeven_inflation_10y=breakeven_inflation_10y,
            rate_diff_10y_real=rate_spread_10y_real,
            rate_z_tactical=rate_z_tactical,
            rate_z_structural=rate_z_structural,
            z_blended=z_blended,
            realized_vol_rank=realized_vol_rank,
            skew_alignment=skew_alignment,
            risk_reversal_25d=risk_reversal_25d,
            risk_reversal_source=risk_reversal_source,
            days_since_cot=days_since_cot,
            fpi_flow=fpi_flow,
            cot_net_pos=cot_net_pos,
            cot_asset_mgr_net=cot_asset_mgr_net,
            cot_lev_money_net=cot_lev_money_net,
            ecb_balance_sheet=macro.get("ecb_balance_sheet") if pair == "EURUSD" else None,
            bund_btp_spread=macro.get("bund_btp_spread") if pair == "EURUSD" else None,
            boj_policy_rate=macro.get("boj_policy_rate") if pair == "USDJPY" else None,
            india_vix=macro.get("india_vix") if pair == "USDINR" else None,
            inr_forward_premium=macro.get("inr_forward_premium") if pair == "USDINR" else None,
            data_quality_notes=None,
        )

    def build_regime_call(
        self,
        pair: str,
        *,
        signal_row: SignalRow,
        composite: float,
        confidence: float,
        regime: str,
        primary_driver: str,
        layer2: Layer2DirectionalOutput,
        layer3: Layer3ExecutionOutput,
        rate_direction: str,
        cot_norm: float | None = None,
        vol_norm: float | None = None,
        vol_expanding: bool = False,
        oi_norm: float | None = None,
        risk_reversal_25d: float | None = None,
        special_signal: float | None = None,
    ) -> RegimeCall:
        """Assemble the persistence-ready regime call for ``pair``."""

        bias = layer2["directional_bias"]
        predicted_direction = (
            "BULLISH" if bias == "LONG" else ("BEARISH" if bias == "SHORT" else "NEUTRAL")
        )

        cot_label = (
            "BULLISH"
            if cot_norm is not None and cot_norm > 0.15
            else ("BEARISH" if cot_norm is not None and cot_norm < -0.15 else "NEUTRAL")
        )
        vol_label = (
            "VOL_EXPANDING"
            if vol_expanding
            else (
                "BULLISH"
                if vol_norm is not None and vol_norm > 0.15
                else ("BEARISH" if vol_norm is not None and vol_norm < -0.15 else "NEUTRAL")
            )
        )
        oi_label = (
            "BULLISH"
            if oi_norm is not None and oi_norm > 0.15
            else ("BEARISH" if oi_norm is not None and oi_norm < -0.15 else "NEUTRAL")
        )
        rr_label = (
            "BULLISH"
            if risk_reversal_25d is not None and risk_reversal_25d > 0.15
            else (
                "BEARISH"
                if risk_reversal_25d is not None and risk_reversal_25d < -0.15
                else "NEUTRAL"
            )
        )

        special_label = {
            "EURUSD": "Bund-BTP + ECB BS",
            "USDJPY": "VIX + JPY Funding Stress",
            "USDINR": "Oil + DXY + EM Risk",
        }.get(pair)

        return RegimeCall(
            pair=pair,
            date=signal_row.date,
            regime=regime,
            confidence=confidence,
            signal_composite=composite,
            rate_signal=rate_direction,
            primary_driver=primary_driver,
            entry_timing=layer3["entry_timing"],
            position_size=layer3["position_size"],
            stop_level=layer3["stop_level"],
            data_quality_score=self.snapshot.dqs_score,
            stress_level=self.snapshot.stress_level,
            predicted_direction=predicted_direction,
            directional_bias=bias,
            conviction=layer2["conviction"],
            cot_signal=cot_label,
            vol_signal=vol_label,
            oi_signal=oi_label,
            rr_signal=rr_label,
            special_signal_value=special_signal,
            special_signal_label=special_label,
            regime_category=get_regime_category(regime),
            model_version="2.0-live",
        )
