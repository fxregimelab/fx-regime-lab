"""Assemble a SignalRow and a RegimeCall from an IngestionSnapshot and layer outputs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.policies.confidence_cap import DqsConfidenceCap, dqs_confidence_cap
from src.core.policies.labeler import DefaultSignalLabeler, SignalLabeler
from src.core.policies.macro_gater import DefaultPairMacroGater, PairMacroGater
from src.regime.classifier import get_regime_category
from src.signals.volatility import compute_rvol
from src.types import (
    Layer2DirectionalOutput,
    Layer3ExecutionOutput,
    RegimeCall,
    SignalRow,
)

from .ingestion_snapshot import IngestionSnapshot

if TYPE_CHECKING:
    from src.staged.signals.types import FamilyOutput

__all__ = ["RegimeCallBuilder", "dqs_confidence_cap"]


class RegimeCallBuilder:
    """Build ``SignalRow`` and ``RegimeCall`` artifacts from a validated snapshot.

    The builder does not run signal math itself; it takes the computed outputs of
    the three signal layers and assembles the persistence-ready row objects. This
    keeps fetcher/ingestion details isolated from regime-call construction.
    """

    def __init__(
        self,
        snapshot: IngestionSnapshot,
        *,
        labeler: SignalLabeler | None = None,
        macro_gater: PairMacroGater | None = None,
        confidence_cap: DqsConfidenceCap | None = None,
    ) -> None:
        self.snapshot = snapshot
        self._labeler = labeler or DefaultSignalLabeler()
        self._macro_gater = macro_gater or DefaultPairMacroGater()
        self._confidence_cap = confidence_cap or DqsConfidenceCap()

    def build_signal_row(
        self,
        pair: str,
        *,
        families: FamilyOutput | None = None,
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

        if families is not None:
            if families.rate is not None:
                rate = families.rate
                rate_spread_2y = rate_spread_2y if rate_spread_2y is not None else rate.spread_2y
                rate_spread_10y = (
                    rate_spread_10y if rate_spread_10y is not None else rate.spread_10y
                )
                rate_spread_10y_real = (
                    rate_spread_10y_real
                    if rate_spread_10y_real is not None
                    else rate.spread_10y_real
                )
                rate_z_tactical = (
                    rate_z_tactical if rate_z_tactical is not None else rate.norm_z.z_tactical
                )
                rate_z_structural = (
                    rate_z_structural if rate_z_structural is not None else rate.norm_z.z_structural
                )
                z_blended = z_blended if z_blended is not None else rate.norm_z.z_blended
                breakeven_inflation_10y = (
                    breakeven_inflation_10y
                    if breakeven_inflation_10y is not None
                    else rate.breakeven_inflation_10y
                )
                risk_adjusted_carry = (
                    risk_adjusted_carry
                    if risk_adjusted_carry is not None
                    else rate.risk_adjusted_carry
                )
            if families.cot is not None:
                cot = families.cot
                cot_percentile = (
                    cot_percentile if cot_percentile is not None else cot.percentile
                )
                cot_norm = cot_norm if cot_norm is not None else cot.norm
                oi_norm = oi_norm if oi_norm is not None else cot.oi_norm
                oi_delta = oi_delta if oi_delta is not None else cot.oi_delta
                days_since_cot = cot.days_since_cot
                cot_net_pos = cot_net_pos if cot_net_pos is not None else cot.net_pos
                cot_asset_mgr_net = (
                    cot_asset_mgr_net if cot_asset_mgr_net is not None else cot.asset_mgr_net
                )
                cot_lev_money_net = (
                    cot_lev_money_net if cot_lev_money_net is not None else cot.lev_money_net
                )
            if families.vol is not None:
                vol = families.vol
                realized_vol_20d = (
                    realized_vol_20d if realized_vol_20d is not None else vol.rv20
                )
                realized_vol_5d = realized_vol_5d if realized_vol_5d is not None else vol.rv5
                vol_norm = vol_norm if vol_norm is not None else vol.vol_norm
                vol_expanding = vol.vol_expanding  # noqa: F841
                implied_vol_30d = (
                    implied_vol_30d if implied_vol_30d is not None else vol.implied_vol_30d
                )
                realized_vol_rank = (
                    realized_vol_rank if realized_vol_rank is not None else vol.realized_vol_rank
                )
            if families.special is not None:
                special_signal = (
                    special_signal if special_signal is not None else families.special.signal
                )

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

        macro_fields = self._macro_gater.gate(pair, self.snapshot.macro)

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
            ecb_balance_sheet=macro_fields.ecb_balance_sheet,
            bund_btp_spread=macro_fields.bund_btp_spread,
            boj_policy_rate=macro_fields.boj_policy_rate,
            india_vix=macro_fields.india_vix,
            inr_forward_premium=macro_fields.inr_forward_premium,
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
        apply_dqs_cap: bool = True,
        model_version: str | None = None,
        strategy_version: str | None = None,
        data_source: str | None = None,
    ) -> RegimeCall:
        """Assemble the persistence-ready regime call for ``pair``."""

        final_confidence = float(confidence)
        if apply_dqs_cap:
            cap = self._confidence_cap.cap(self.snapshot.dqs_score)
            if cap is not None:
                final_confidence = min(final_confidence, cap)

        bias = layer2["directional_bias"]
        predicted_direction = (
            "BULLISH" if bias == "LONG" else ("BEARISH" if bias == "SHORT" else "NEUTRAL")
        )

        dqs_score = (
            round(float(self.snapshot.dqs_score), 2)
            if self.snapshot.dqs_score is not None
            else None
        )

        return RegimeCall(
            pair=pair,
            date=signal_row.date,
            regime=regime,
            confidence=final_confidence,
            signal_composite=composite,
            rate_signal=rate_direction,
            primary_driver=primary_driver,
            entry_timing=layer3["entry_timing"],
            position_size=layer3["position_size"],
            stop_level=layer3["stop_level"],
            data_quality_score=dqs_score,
            stress_level=self.snapshot.stress_level,
            predicted_direction=predicted_direction,
            directional_bias=bias,
            conviction=layer2["conviction"],
            cot_signal=self._labeler.label_cot(cot_norm),
            vol_signal=self._labeler.label_vol(vol_norm, vol_expanding=vol_expanding),
            oi_signal=self._labeler.label_oi(oi_norm),
            rr_signal=self._labeler.label_rr(risk_reversal_25d),
            special_signal_value=special_signal,
            special_signal_label=self._labeler.label_special(pair),
            regime_category=get_regime_category(regime),
            model_version=model_version if model_version is not None else "2.0-live",
            strategy_version=strategy_version if strategy_version is not None else "v2",
            data_source=data_source if data_source is not None else "live",
        )
