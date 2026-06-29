"""SignalStage: pair-scoped signal math and Layer 1/2/3 execution."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from src.core.ingestion_snapshot import IngestionSnapshot as CoreIngestionSnapshot
from src.core.regime_call_builder import RegimeCallBuilder
from src.logic.layer2_directional import run_layer2_directional
from src.logic.layer3_execution import run_layer3_execution
from src.regime.classifier import classify_regime_layer1
from src.regime.composite import compute_composite, get_primary_driver
from src.regime.confidence import compute_confidence
from src.staged.contracts import IngestionSnapshot, SignalPipelineResult, StageHealth
from src.staged.signals.cot_family import CotFamily
from src.staged.signals.protocol import SignalFamily
from src.staged.signals.rate_family import RateFamily
from src.staged.signals.rate_history import RateHistoryProvider, SnapshotRateHistoryProvider
from src.staged.signals.special_family import SpecialFamily
from src.staged.signals.types import FamilyOutput
from src.staged.signals.vol_family import VolFamily
from src.types import (
    Layer1ClassifierContext,
    Layer1GateOutput,
    Layer2DirectionalOutput,
    Layer3ExecutionOutput,
    SpotBar,
)


def _to_core_snapshot(snapshot: IngestionSnapshot) -> CoreIngestionSnapshot:
    return CoreIngestionSnapshot(
        date=snapshot.date,
        spots=cast(dict[str, Sequence[SpotBar]], snapshot.spots),
        yields=dict(snapshot.yields),
        cot_rows=list(snapshot.cot_rows),
        cross_asset=dict(snapshot.cross_asset),
        macro=dict(snapshot.macro) if snapshot.macro is not None else None,
        dqs_score=snapshot.dqs_score,
        stress_level=snapshot.stress_level,
    )


def _default_families(history_provider: RateHistoryProvider) -> tuple[SignalFamily, ...]:
    return (
        RateFamily(history_provider=history_provider),
        CotFamily(),
        VolFamily(),
        SpecialFamily(),
    )


class SignalStage:
    """Run pair-scoped signal math and produce a SignalPipelineResult."""

    def __init__(
        self,
        families: Sequence[SignalFamily] | None = None,
        *,
        history_provider: RateHistoryProvider | None = None,
    ) -> None:
        self._history_provider = history_provider
        self._families = families

    def run(self, pair: str, snapshot: IngestionSnapshot) -> SignalPipelineResult:
        """Compute signals, layers, and assemble the result for ``pair``."""

        as_of = snapshot.date
        spot_bars = snapshot.spots.get(pair, ())
        spot_closes = tuple(float(b.close) for b in spot_bars if b.close is not None)

        history = self._history_provider or SnapshotRateHistoryProvider(snapshot)
        families = self._families or _default_families(history)

        # Run vol first so rate family can use rv20 for risk-adjusted carry.
        # Respect an injected VolFamily instance if one was provided.
        vol_family = next((f for f in families if isinstance(f, VolFamily)), None)
        if vol_family is None:
            vol_family = VolFamily()
        vol_partial = vol_family.compute(pair, snapshot)
        rv20 = vol_partial.vol.rv20 if vol_partial.vol is not None else None

        partials: list[FamilyOutput] = [vol_partial]
        for family in families:
            if isinstance(family, VolFamily):
                continue
            if isinstance(family, RateFamily):
                partials.append(family.compute(pair, snapshot, rv20=rv20))
            else:
                partials.append(family.compute(pair, snapshot))

        families_out = FamilyOutput.merge(*partials)
        rate = families_out.rate
        cot = families_out.cot
        vol = families_out.vol
        special = families_out.special

        if rate is None or cot is None or vol is None:
            raise ValueError(f"Incomplete family outputs for {pair}")

        rate_z_tactical = rate.norm_z.z_tactical
        rate_z_structural = rate.norm_z.z_structural
        z_blended = rate.norm_z.z_blended
        cot_norm = cot.norm
        vol_norm = vol.vol_norm
        special_signal = special.signal if special is not None else None

        composite = compute_composite(
            rate_norm=z_blended,
            cot_norm=cot_norm,
            vol_norm=vol_norm,
            oi_norm=cot.oi_norm,
            pair=pair,
            special_signal=special_signal,
        )
        if composite is None:
            composite = 0.0

        betas: dict[str, float] = {
            "rate": 0.0 if z_blended is None else float(z_blended),
            "cot": 0.0 if cot_norm is None else float(cot_norm),
            "vol": 0.0 if vol_norm is None else float(vol_norm),
            "oi": 0.0 if cot.oi_norm is None else float(cot.oi_norm),
            "special": special_signal if special_signal is not None else 0.0,
        }
        primary_driver = get_primary_driver(betas)

        confidence = compute_confidence(
            composite,
            rate_norm=z_blended,
            cot_norm=cot_norm,
            pair=pair,
            special_signal=special_signal,
        )

        min_layer1_len = max(len(spot_closes), 30)
        carry_series = history.carry_series(
            rate.risk_adjusted_carry,
            min_length=min_layer1_len,
        )
        bei_series = history.bei_series(
            rate.breakeven_inflation_10y,
            min_length=min_layer1_len,
        )

        layer1: Layer1GateOutput = classify_regime_layer1(
            Layer1ClassifierContext(
                pair=pair,
                composite=float(composite),
                vol_expanding=vol.vol_expanding,
                structural_instability=False,
                prior_regime_label=None,
                carry_risk_adjusted_chronological=carry_series,
                spot_closes_chronological=spot_closes,
                breakeven_inflation_chronological=bei_series,
                rate_diff_2y=rate.spread_2y,
                realized_vol_20d=vol.rv20,
            )
        )
        if layer1["invalidated"]:
            confidence = float(max(0.40, confidence * 0.50))

        layer2: Layer2DirectionalOutput = run_layer2_directional(
            composite=float(composite),
            z_tactical=z_blended,
            z_structural=rate_z_structural,
            rate_direction=rate.direction,
            positioning_percentile=cot.percentile,
            layer1_invalidated=layer1["invalidated"],
        )

        today_bar = next(
            (b for b in spot_bars if b.date == as_of),
            spot_bars[-1] if spot_bars else None,
        )
        spot = float(today_bar.close) if today_bar is not None else None
        rr_series: tuple[float, ...] = ()
        layer3: Layer3ExecutionOutput = run_layer3_execution(
            layer2=layer2,
            spot=spot,
            spot_bars=spot_bars,
            realized_vol_rank=vol.realized_vol_rank,
            risk_reversal_series_bps=rr_series,
        )

        conviction_cap = 0.42 + 0.10 * float(layer2["conviction"])
        confidence = min(float(confidence), conviction_cap)
        if snapshot.stress_level == "AMBER":
            confidence = min(float(confidence), 0.72)

        core_snapshot = _to_core_snapshot(snapshot)
        builder = RegimeCallBuilder(core_snapshot)
        signal_row = builder.build_signal_row(
            pair,
            families=families_out,
            skew_alignment=layer3["skew_alignment"],
            risk_reversal_25d=None,
            risk_reversal_source="PENDING_REAL_DATA",
        )

        health_notes: list[str] = list(families_out.health_notes)
        if layer1["invalidated"]:
            health_notes.append(f"layer1_invalidated:{','.join(layer1['stale_fields'])}")

        return SignalPipelineResult(
            pair=pair,
            date=as_of,
            signal_row=signal_row,
            layer1=layer1,
            layer2=layer2,
            layer3=layer3,
            snapshot=snapshot,
            health=StageHealth(
                stage_name="SignalStage",
                status="DEGRADED" if layer1["invalidated"] else "OK",
                notes=health_notes,
            ),
            rate_spread_2y=rate.spread_2y,
            rate_spread_10y=rate.spread_10y,
            rate_spread_10y_real=rate.spread_10y_real,
            rate_z_tactical=rate_z_tactical,
            rate_z_structural=rate_z_structural,
            z_blended=z_blended,
            cot_percentile=cot.percentile,
            cot_norm=cot_norm,
            realized_vol_20d=vol.rv20,
            realized_vol_5d=vol.rv5,
            implied_vol_30d=vol.implied_vol_30d,
            vol_norm=vol_norm,
            vol_expanding=vol.vol_expanding,
            oi_delta=cot.oi_delta,
            oi_norm=cot.oi_norm,
            special_signal=special_signal,
            risk_adjusted_carry=rate.risk_adjusted_carry,
            days_since_cot=cot.days_since_cot,
            cot_net_pos=cot.net_pos,
            cot_asset_mgr_net=cot.asset_mgr_net,
            cot_lev_money_net=cot.lev_money_net,
            structural_instability=False,
            breakeven_inflation_10y=rate.breakeven_inflation_10y,
            risk_reversal_25d=None,
            risk_reversal_source="PENDING_REAL_DATA",
            composite=composite,
            confidence=confidence,
            primary_driver=primary_driver,
            rate_direction=rate.direction,
        )
