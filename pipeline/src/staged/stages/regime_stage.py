"""RegimeStage: turn a SignalPipelineResult into a persistence-ready RegimeCall."""

from __future__ import annotations

from src.core.ingestion_snapshot import IngestionSnapshot as CoreIngestionSnapshot
from src.core.regime_call_builder import RegimeCallBuilder
from src.staged.contracts import IngestionSnapshot, SignalPipelineResult
from src.types import RegimeCall, SpotBar


def _to_core_snapshot(snapshot: IngestionSnapshot) -> CoreIngestionSnapshot:
    """Adapt the staged frozen snapshot to the core builder's snapshot type."""

    from collections.abc import Sequence
    from typing import cast

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


class RegimeStage:
    """Assemble a RegimeCall from a SignalPipelineResult."""

    def run(self, pair: str, signal_result: SignalPipelineResult) -> RegimeCall:
        """Build the regime call using the existing RegimeCallBuilder."""

        staged = signal_result.snapshot
        if staged is None:
            raise ValueError("SignalPipelineResult.snapshot is required for RegimeStage")
        snapshot = _to_core_snapshot(staged)
        builder = RegimeCallBuilder(snapshot)

        return builder.build_regime_call(
            pair=pair,
            signal_row=signal_result.signal_row,
            composite=signal_result.composite,
            confidence=signal_result.confidence,
            regime=signal_result.layer1["regime"],
            primary_driver=signal_result.primary_driver,
            layer2=signal_result.layer2,
            layer3=signal_result.layer3,
            rate_direction=signal_result.rate_direction,
            cot_norm=signal_result.cot_norm,
            vol_norm=signal_result.vol_norm,
            vol_expanding=signal_result.vol_expanding,
            oi_norm=signal_result.oi_norm,
            risk_reversal_25d=signal_result.risk_reversal_25d,
            special_signal=signal_result.special_signal,
        )
