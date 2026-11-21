"""Direction must not change evidence strength under mirrored inputs."""

import pytest

from src.logic.layer2_directional import run_layer2_directional


@pytest.mark.parametrize("magnitude", [0.0, 0.2, 0.8, 1.5, 2.0, 3.0])
@pytest.mark.parametrize("percentile", [50.0, 70.0, 92.0, 98.0])
def test_mirrored_evidence_has_equal_conviction(magnitude: float, percentile: float) -> None:
    outputs = [
        run_layer2_directional(
            composite=side * magnitude,
            z_tactical=side * 0.4,
            z_structural=side * 0.2,
            rate_direction="BULLISH" if side == 1 else "BEARISH",
            positioning_percentile=percentile if side == 1 else 100.0 - percentile,
            layer1_invalidated=False,
        )
        for side in (1, -1)
    ]
    long, short = outputs
    assert long["conviction"] == short["conviction"]
    assert long["crowd_penalty"] == pytest.approx(short["crowd_penalty"])
    assert long["crowd_veto"] == short["crowd_veto"]
    assert (long["directional_bias"], short["directional_bias"]) in {
        ("LONG", "SHORT"), ("NEUTRAL", "NEUTRAL"),
    }
