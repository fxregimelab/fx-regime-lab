"""SignalStage: pair-scoped signal math and Layer 1/2/3 execution."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

import numpy as np

from src.core.spot_history import select_spot_history
from src.fetchers.open_interest import compute_oi_delta_from_cot, compute_oi_from_cot
from src.logic.layer2_directional import run_layer2_directional
from src.logic.layer3_execution import run_layer3_execution
from src.regime.classifier import classify_regime_layer1
from src.regime.composite import compute_composite
from src.regime.confidence import compute_confidence
from src.signals.cot import (
    compute_cot_percentile,
    compute_cot_smart_spread_percentile,
    normalize_cot_signal,
)
from src.signals.direction import directional_inputs
from src.signals.fpi import FPI_UNAVAILABLE_NOTES
from src.signals.rate import (
    RateNormZ,
    compute_risk_adjusted_carry_v2,
    rate_direction_from_spreads,
)
from src.signals.rate_inputs import (
    current_real_yield_spread,
    nominal_ten_year_context,
)
from src.signals.rate_observation import RateObservation, qualified_two_year_spread
from src.signals.special import compute_special_signal
from src.signals.volatility import (
    compute_realized_vol_rank_from_closes,
    compute_rvol,
    compute_vol_signal,
    is_vol_expanding,
    realized_vol21_series_annualized_pct,
)
from src.staged.contracts import IngestionSnapshot, SignalPipelineResult, StageHealth
from src.types import (
    CotRow,
    Layer1ClassifierContext,
    Layer1GateOutput,
    Layer2DirectionalOutput,
    Layer3ExecutionOutput,
    SignalRow,
)


def _rate_spread_2y(
    pair: str,
    yields: dict[str, float | None],
    observations: dict[str, RateObservation] | None = None,
    decision_at: datetime | None = None,
) -> float | None:
    """Scalar yields remain descriptive; qualification needs source evidence."""
    return qualified_two_year_spread(pair, observations or {}, decision_at=decision_at)


def _rate_spread_10y(pair: str, yields: dict[str, float | None]) -> float | None:
    """Unqualified nominal context; never substituted into forecast features."""
    return nominal_ten_year_context(pair, yields)


def _cot_rows_for_pair(rows: list[CotRow], pair: str) -> list[CotRow]:
    return sorted([r for r in rows if r.pair == pair], key=lambda r: r.date)


def _latest_cot_net_pos(rows: list[CotRow], pair: str) -> int | None:
    pair_rows = _cot_rows_for_pair(rows, pair)
    if not pair_rows:
        return None
    latest = pair_rows[-1]
    return int(latest.net_long)


def _latest_cot_breakdown(rows: list[CotRow], pair: str) -> tuple[int | None, int | None]:
    pair_rows = _cot_rows_for_pair(rows, pair)
    if not pair_rows:
        return None, None
    latest = pair_rows[-1]
    return latest.asset_mgr_net, latest.lev_money_net


def _days_since_cot(rows: list[CotRow], pair: str, as_of: date) -> int:
    pair_rows = _cot_rows_for_pair(rows, pair)
    if not pair_rows:
        return 999
    latest = pair_rows[-1].date
    return (as_of - latest).days


def _realized_vols(spot_closes: Sequence[float]) -> tuple[float | None, float | None]:
    """Return (rv20, rv5) annualized percentages from a close series."""

    arr = np.asarray(list(spot_closes), dtype=np.float64)
    if arr.size < 22 or np.any(arr <= 0):
        return None, None
    series = realized_vol21_series_annualized_pct(arr)
    tail = series[21:]
    if tail.size < 5:
        return None, None
    rv20 = float(np.nanmean(tail[-20:])) if tail.size >= 20 else float(tail[-1])
    rv5 = float(np.nanmean(tail[-5:]))
    return rv20, rv5


def _vol_threshold_90(spot_closes: Sequence[float]) -> float | None:
    """90th percentile of 21d RV for vol-expansion detection."""

    arr = np.asarray(list(spot_closes), dtype=np.float64)
    if arr.size < 22 or np.any(arr <= 0):
        return None
    series = realized_vol21_series_annualized_pct(arr)
    tail = series[21:]
    clean = tail[np.isfinite(tail)]
    if clean.size < 30:
        return None
    return float(np.percentile(clean, 90))


def _normalize_rate_signal(
    pair: str,
    spread: float | None,
    spread_structural: float | None,
) -> RateNormZ:
    """The staged snapshot contains no rate history from which to estimate Z."""
    return RateNormZ(z_tactical=None, z_structural=None, z_blended=None)


class SignalStage:
    """Run pair-scoped signal math and produce a SignalPipelineResult."""

    def run(self, pair: str, snapshot: IngestionSnapshot) -> SignalPipelineResult:
        """Compute signals, layers, and assemble the result for ``pair``."""

        as_of = snapshot.date
        spot_bars = select_spot_history(snapshot.spots.get(pair, ()), pair=pair, as_of=as_of)
        if len(spot_bars) < 2:
            raise ValueError(f"At least two causal spot observations are required for {pair}")
        spot_closes = tuple(float(b.close) for b in spot_bars)

        # Rate spreads
        rate_spread_2y = _rate_spread_2y(
            pair, snapshot.yields, snapshot.rate_observations, snapshot.rate_decision_at
        )
        rate_spread_10y = _rate_spread_10y(pair, snapshot.yields)
        bei = snapshot.yields.get("T10YIE")
        rate_spread_10y_real = current_real_yield_spread(pair, rate_spread_10y, snapshot.yields)

        # Rate normalization
        rate_norm_z = _normalize_rate_signal(pair, rate_spread_2y, rate_spread_10y_real)
        rate_z_tactical = rate_norm_z.z_tactical
        rate_z_structural = rate_norm_z.z_structural
        z_blended = rate_norm_z.z_blended
        rate_direction = rate_direction_from_spreads(
            rate_spread_2y,
            rate_spread_10y_real,
            z_tactical=rate_z_tactical,
        )

        # COT
        cot_pct = compute_cot_percentile(snapshot.cot_rows, pair, as_of=as_of)
        cot_norm = normalize_cot_signal(cot_pct)
        cot_smart = compute_cot_smart_spread_percentile(snapshot.cot_rows, pair, as_of=as_of)
        cot_smart_norm = normalize_cot_signal(cot_smart)
        if cot_norm is not None and cot_smart_norm is not None:
            cot_norm = 0.70 * cot_norm + 0.30 * cot_smart_norm
        if pair == "USDINR":
            cot_pct = None
            cot_norm = None
        oi_pct = compute_oi_from_cot(snapshot.cot_rows, pair)
        oi_norm = (
            float(max(-1.0, min(1.0, -(oi_pct - 50.0) / 50.0))) if oi_pct is not None else None
        )
        oi_delta = compute_oi_delta_from_cot(snapshot.cot_rows, pair)
        cot_net_pos = _latest_cot_net_pos(snapshot.cot_rows, pair)
        cot_asset_mgr_net, cot_lev_money_net = _latest_cot_breakdown(snapshot.cot_rows, pair)
        days_since_cot = _days_since_cot(snapshot.cot_rows, pair, as_of)

        # Volatility
        rv20, rv5 = _realized_vols(spot_closes)
        threshold_90 = _vol_threshold_90(spot_closes)
        vol_norm = compute_vol_signal(rv5, rv20, threshold_90)
        vol_expanding = (
            is_vol_expanding(float(rv5), float(threshold_90))
            if rv5 is not None and threshold_90 is not None
            else False
        )
        implied_vol_30d: float | None = None
        rv_rank = compute_realized_vol_rank_from_closes(spot_closes)

        # Special signal (EURUSD macro overrides; other pairs use cross-asset hist)
        cross_for_special: dict[str, Any] = dict(snapshot.cross_asset)
        special_signal = compute_special_signal(
            pair,
            cross_for_special,
            bund_btp_spread=(snapshot.macro or {}).get("bund_btp_spread"),
            ecb_balance_sheet=(snapshot.macro or {}).get("ecb_balance_sheet"),
        )

        directional = directional_inputs(
            pair, rate=rate_z_tactical, cot=cot_norm, special=special_signal, fpi=None
        )
        cot_norm, special_signal = directional.cot, directional.special

        # Composite and confidence
        composite = compute_composite(
            rate_norm=rate_z_tactical,
            cot_norm=cot_norm,
            vol_norm=vol_norm,
            oi_norm=oi_norm,
            pair=pair,
            special_signal=special_signal,
        )
        if composite is None:
            raise ValueError("directional_inputs_unavailable")

        primary_driver = "Static directional reference (unvalidated)"

        confidence = compute_confidence(
            composite,
            rate_norm=rate_z_tactical,
            cot_norm=cot_norm,
            pair=pair,
            special_signal=special_signal,
        )

        risk_adjusted_carry = compute_risk_adjusted_carry_v2(
            rate_spread_2y,
            rv20,
            implied_vol_30d,
            pair,
        )

        # Snapshots have current rates, not observed rate/inflation histories.
        carry_series: tuple[float, ...] = ()
        bei_series: tuple[float, ...] | None = None

        layer1: Layer1GateOutput = classify_regime_layer1(
            Layer1ClassifierContext(
                pair=pair,
                composite=float(composite),
                vol_expanding=vol_expanding,
                structural_instability=False,
                prior_regime_label=None,
                carry_risk_adjusted_chronological=carry_series,
                spot_closes_chronological=spot_closes,
                breakeven_inflation_chronological=bei_series,
                rate_diff_2y=rate_spread_2y,
                realized_vol_20d=rv20,
            )
        )
        if layer1["invalidated"]:
            confidence = float(max(0.40, confidence * 0.50))

        # Layer 2
        layer2: Layer2DirectionalOutput = run_layer2_directional(
            pair=pair,
            composite=float(composite),
            z_tactical=rate_z_tactical,
            z_structural=rate_z_structural,
            rate_direction=rate_direction,
            positioning_percentile=cot_pct,
            layer1_invalidated=layer1["invalidated"],
        )

        # Layer 3
        today_bar = spot_bars[-1]
        spot = float(today_bar.close)
        rr_series: tuple[float, ...] = ()
        layer3: Layer3ExecutionOutput = run_layer3_execution(
            layer2=layer2,
            spot=spot,
            spot_bars=spot_bars,
            realized_vol_rank=rv_rank,
            risk_reversal_series_bps=rr_series,
        )

        # Conviction cap identical to the legacy orchestrator path.
        conviction_cap = 0.42 + 0.10 * float(layer2["conviction"])
        confidence = min(float(confidence), conviction_cap)
        if snapshot.stress_level == "AMBER":
            confidence = min(float(confidence), 0.72)

        # Build the signal row via a lightweight inline assembly so the contract
        # stays independent of the core IngestionSnapshot type.
        volumes = [float(b.volume) for b in spot_bars if b.volume > 0]
        volume_rvol = compute_rvol(volumes)
        yest_bar = spot_bars[-2]
        day_change = today_bar.close - yest_bar.close
        day_change_pct = day_change / yest_bar.close * 100.0
        macro = snapshot.macro or {}

        fpi_notes = list(FPI_UNAVAILABLE_NOTES) if pair == "USDINR" else []
        signal_row = SignalRow(
            pair=pair,
            date=as_of,
            rate_diff_2y=rate_spread_2y,
            rate_diff_10y=rate_spread_10y,
            cot_percentile=cot_pct,
            realized_vol_20d=rv20,
            realized_vol_5d=rv5,
            implied_vol_30d=implied_vol_30d,
            spot=spot,
            day_change=day_change,
            day_change_pct=day_change_pct,
            cross_asset_vix=snapshot.cross_asset.get("vix"),
            cross_asset_dxy=snapshot.cross_asset.get("dxy"),
            cross_asset_oil=snapshot.cross_asset.get("oil"),
            cross_asset_us10y=snapshot.yields.get("us_10y"),
            cross_asset_gold=snapshot.cross_asset.get("gold"),
            cross_asset_copper=snapshot.cross_asset.get("copper"),
            cross_asset_stoxx=snapshot.cross_asset.get("stoxx"),
            oi_delta=oi_delta,
            volume_rvol=volume_rvol,
            structural_instability=False,
            breakeven_inflation_10y=bei,
            rate_diff_10y_real=rate_spread_10y_real,
            rate_z_tactical=rate_z_tactical,
            rate_z_structural=rate_z_structural,
            z_blended=z_blended,
            realized_vol_rank=rv_rank,
            skew_alignment=layer3["skew_alignment"],
            risk_reversal_25d=None,
            risk_reversal_source="PENDING_REAL_DATA",
            days_since_cot=days_since_cot,
            cot_net_pos=cot_net_pos,
            cot_asset_mgr_net=cot_asset_mgr_net,
            cot_lev_money_net=cot_lev_money_net,
            ecb_balance_sheet=macro.get("ecb_balance_sheet") if pair == "EURUSD" else None,
            bund_btp_spread=macro.get("bund_btp_spread") if pair == "EURUSD" else None,
            boj_policy_rate=macro.get("boj_policy_rate") if pair == "USDJPY" else None,
            india_vix=macro.get("india_vix") if pair == "USDINR" else None,
            inr_forward_premium=macro.get("inr_forward_premium") if pair == "USDINR" else None,
            data_quality_notes=["rate_inputs_unqualified", "rate_history_unavailable", *fpi_notes],
        )

        health_notes: list[str] = [
            "rate_inputs_unqualified",
            "rate_history_unavailable",
            *fpi_notes,
        ]
        if today_bar.date < as_of:
            health_notes.append("spot_observation_prior_session")
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
                status="DEGRADED",
                notes=health_notes,
            ),
            rate_spread_2y=rate_spread_2y,
            rate_spread_10y=rate_spread_10y,
            rate_spread_10y_real=rate_spread_10y_real,
            rate_z_tactical=rate_z_tactical,
            rate_z_structural=rate_z_structural,
            z_blended=z_blended,
            cot_percentile=cot_pct,
            cot_norm=cot_norm,
            realized_vol_20d=rv20,
            realized_vol_5d=rv5,
            implied_vol_30d=implied_vol_30d,
            vol_norm=vol_norm,
            vol_expanding=vol_expanding,
            oi_delta=oi_delta,
            oi_norm=oi_norm,
            special_signal=special_signal,
            risk_adjusted_carry=risk_adjusted_carry,
            days_since_cot=days_since_cot,
            cot_net_pos=cot_net_pos,
            cot_asset_mgr_net=cot_asset_mgr_net,
            cot_lev_money_net=cot_lev_money_net,
            structural_instability=False,
            breakeven_inflation_10y=bei,
            risk_reversal_25d=None,
            risk_reversal_source="PENDING_REAL_DATA",
            composite=composite,
            confidence=confidence,
            primary_driver=primary_driver,
            rate_direction=rate_direction,
        )
