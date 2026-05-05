"""Unit tests for Layer 2 directional conviction (strict, no I/O)."""

from __future__ import annotations

import pytest

from src.logic.layer2_directional import (
    conviction_multiplier_pi,
    crowding_metrics_pi,
    effective_rate_sign,
    marcus_b_rate_positioning_clash,
    positioning_sign_pi,
    run_layer2_directional,
)


def test_alignment_long_high_conviction_no_clash() -> None:
    out = run_layer2_directional(
        composite=1.5,
        z_tactical=0.8,
        z_structural=0.5,
        rate_direction="BULLISH",
        positioning_percentile=72.0,
        layer1_invalidated=False,
    )
    assert out["rate_positioning_clash"] is False
    assert out["directional_bias"] == "LONG"
    assert out["crowd_veto"] is False
    assert out["conviction"] >= 4


def test_bearish_short_when_no_veto() -> None:
    out = run_layer2_directional(
        composite=-0.8,
        z_tactical=-0.4,
        z_structural=-0.2,
        rate_direction="BEARISH",
        positioning_percentile=35.0,
        layer1_invalidated=False,
    )
    assert out["directional_bias"] == "SHORT"
    assert out["rate_positioning_clash"] is False


def test_marcus_b_clash_neutral_bias() -> None:
    out = run_layer2_directional(
        composite=1.2,
        z_tactical=0.9,
        z_structural=0.4,
        rate_direction="BULLISH",
        positioning_percentile=25.0,
        layer1_invalidated=False,
    )
    assert out["rate_positioning_clash"] is True
    assert out["directional_bias"] == "NEUTRAL"
    assert out["conviction"] <= 3


def test_extreme_crowding_veto_neutral() -> None:
    out = run_layer2_directional(
        composite=1.8,
        z_tactical=0.6,
        z_structural=0.3,
        rate_direction="BULLISH",
        positioning_percentile=98.0,
        layer1_invalidated=False,
    )
    assert out["crowd_veto"] is True
    assert out["crowd_flag"] is True
    assert out["directional_bias"] == "NEUTRAL"


def test_lower_tail_crowding_veto() -> None:
    out = run_layer2_directional(
        composite=-1.0,
        z_tactical=-0.5,
        z_structural=-0.3,
        rate_direction="BEARISH",
        positioning_percentile=2.0,
        layer1_invalidated=False,
    )
    assert out["crowd_veto"] is True
    assert out["directional_bias"] == "NEUTRAL"


def test_layer1_invalidated_forces_neutral_and_no_clash_telemetry() -> None:
    out = run_layer2_directional(
        composite=1.0,
        z_tactical=1.0,
        z_structural=0.0,
        rate_direction="NEUTRAL",
        positioning_percentile=20.0,
        layer1_invalidated=True,
    )
    assert out["directional_bias"] == "NEUTRAL"
    assert out["rate_positioning_clash"] is False


def test_positioning_percentile_none_handled() -> None:
    out = run_layer2_directional(
        composite=0.5,
        z_tactical=0.3,
        z_structural=None,
        rate_direction="BULLISH",
        positioning_percentile=None,
        layer1_invalidated=False,
    )
    assert out["positioning_percentile"] is None
    assert out["crowd_flag"] is False
    assert out["crowd_penalty"] == pytest.approx(0.0)
    assert out["directional_bias"] == "LONG"


def test_crowding_ramp_monotone_upper_tail() -> None:
    p90, _, _ = crowding_metrics_pi(90.0)
    p95, _, _ = crowding_metrics_pi(95.0)
    p99, _, _ = crowding_metrics_pi(99.0)
    assert p90 == pytest.approx(0.0)
    assert p95 > p90
    assert p99 > p95


def test_marcus_b_helper() -> None:
    assert marcus_b_rate_positioning_clash(1, -1) is True
    assert marcus_b_rate_positioning_clash(1, 1) is False
    assert marcus_b_rate_positioning_clash(1, 0) is False


def test_effective_rate_sign_prefers_z() -> None:
    assert effective_rate_sign("NEUTRAL", 0.5, None) == 1
    assert effective_rate_sign("BULLISH", None, None) == 1


def test_positioning_sign_deadband() -> None:
    assert positioning_sign_pi(52.0) == 0
    assert positioning_sign_pi(60.0) == 1
    assert positioning_sign_pi(40.0) == -1


def test_conviction_multiplier_bounds() -> None:
    m = conviction_multiplier_pi(50.0, 0.0, 1, 1)
    assert 0.52 <= m <= 1.08
