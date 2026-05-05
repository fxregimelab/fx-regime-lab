"""Layer 1 gate, Marcus invalidation, and composite hysteresis tests."""

from __future__ import annotations

import numpy as np
import pytest

from src.logic import layer1_gate
from src.logic.layer1_gate import regime_from_composite_snapshot, run_layer1_gate
from src.models.regime_enums import FxRegime
from src.regime.classifier import VOL_EXPANDING_SUFFIX, classify_regime_layer1
from src.types import Layer1ClassifierContext


def _dense_ctx(**overrides: object) -> Layer1ClassifierContext:
    base_carry = tuple(1.94 + np.sin(i / 19.0) * 0.08 for i in range(268))
    base_spots = tuple(104.82 + np.sin(float(i)) * 3.1 + i * 0.002 for i in range(268))
    bei = tuple(2.02 + np.sin(float(i)) * 5e-3 for i in range(268))
    kwargs: dict[str, object] = {
        "pair": "EURUSD",
        "composite": 0.12,
        "vol_expanding": False,
        "structural_instability": False,
        "prior_regime_label": None,
        "carry_risk_adjusted_chronological": base_carry,
        "spot_closes_chronological": base_spots,
        "breakeven_inflation_chronological": bei,
        "rate_diff_2y": (-0.17),
        "realized_vol_20d": 0.076,
    }
    kwargs.update(overrides)
    return Layer1ClassifierContext(**kwargs)  # type: ignore[arg-type]


def test_marcus_stale_rate_invalidates() -> None:
    ctx = _dense_ctx(rate_diff_2y=None)
    out = classify_regime_layer1(ctx)
    assert out["invalidated"] is True
    assert FxRegime.NEUTRAL.value in out["regime"]
    assert "rate_diff_2y" in out["stale_fields"]
    assert out["z_rate"] is None
    assert out["d_spot"] is None


def test_carry_collapse_when_structural_flag() -> None:
    ctx = _dense_ctx(structural_instability=True)
    out = run_layer1_gate(ctx)
    assert out["invalidated"] is False
    assert out["raw_regime"] == FxRegime.CARRY_COLLAPSE.value


def test_usd_policy_breakout_when_pi_and_rates_align(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(layer1_gate, "rolling_zscore_last", lambda s, *_a, **_k: 2.3)

    bei = tuple(2.0 if i < 263 else 2.18 for i in range(268))
    ctx = _dense_ctx(
        composite=0.02,
        breakeven_inflation_chronological=bei,
    )
    out = run_layer1_gate(ctx)
    assert out["invalidated"] is False
    assert out["delta_pi"] is not None and abs(float(out["delta_pi"])) >= 0.12
    assert out["raw_regime"] == FxRegime.USD_POLICY_BREAKOUT.value


def test_carry_to_collapse_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(layer1_gate, "rolling_zscore_last", lambda s, *_a, **_k: 1.4)
    monkeypatch.setattr(layer1_gate, "momentum_last", lambda s, *_a, **_k: -0.38)
    out = run_layer1_gate(_dense_ctx(composite=-0.02))
    assert out["invalidated"] is False
    assert out["raw_regime"] == FxRegime.CARRY_COLLAPSE.value


def test_liquidity_shock_when_spot_returns_stress(monkeypatch: pytest.MonkeyPatch) -> None:
    def _branch_z(series: object, *_a: object, **_k: object) -> float | None:
        sz = len(series)  # type: ignore[arg-type]
        if sz <= 30:
            return 3.1
        return 0.36

    monkeypatch.setattr(layer1_gate, "rolling_zscore_last", _branch_z)

    out = run_layer1_gate(_dense_ctx(composite=0.0))
    assert out["invalidated"] is False
    assert out["raw_regime"] == FxRegime.LIQUIDITY_SHOCK.value


def test_hysteresis_holds_strong_bid_regime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(layer1_gate, "rolling_zscore_last", lambda s, *_a, **_k: 0.1)
    monkeypatch.setattr(layer1_gate, "momentum_last", lambda s, *_a, **_k: 0.04)

    ctx = _dense_ctx(
        composite=0.86,
        prior_regime_label=FxRegime.RISK_OFF_DOLLAR_BID.value,
    )
    out = run_layer1_gate(ctx)
    assert out["invalidated"] is False
    assert out["raw_regime"] == FxRegime.RISK_OFF_DOLLAR_BID.value


def test_vol_expanding_neutral_suffix() -> None:
    label = regime_from_composite_snapshot(0.0, "EURUSD", vol_expanding=True)
    assert label.endswith(VOL_EXPANDING_SUFFIX)
