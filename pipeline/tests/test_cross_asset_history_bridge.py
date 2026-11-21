"""Regression tests for cross-asset history across the staged snapshot bridge."""

from __future__ import annotations

import datetime
from typing import Any

import pytest

from src.core.ingestion_snapshot import IngestionSnapshot as CoreIngestionSnapshot
from src.fetchers.buffer_keys import KEY_CROSS_ASSET, KEY_FX_SPOT, KEY_YIELDS
from src.staged.adapters.fetcher import _map_core_to_staged
from src.staged.stages.signal_stage import SignalStage
from src.types import SpotBar

AS_OF = datetime.date(2026, 5, 20)


def _spot_bars(pair: str, base: float) -> list[SpotBar]:
    return [
        SpotBar(
            date=AS_OF - datetime.timedelta(days=39 - index),
            pair=pair,
            open=base + index * 0.01,
            high=base + index * 0.01,
            low=base + index * 0.01,
            close=base + index * 0.01,
            volume=100.0,
        )
        for index in range(40)
    ]


def _base_buffer(cross_asset: dict[str, Any]) -> dict[str, Any]:
    return {
        KEY_FX_SPOT: {
            "USDJPY": _spot_bars("USDJPY", 145.0),
            "USDINR": _spot_bars("USDINR", 85.0),
        },
        KEY_YIELDS: {"us_10y": 4.0},
        KEY_CROSS_ASSET: cross_asset,
    }


def test_cross_asset_history_reaches_signal_stage_for_jpy_and_inr() -> None:
    oil = [60.0 + index * 0.5 for index in range(31)]
    dxy = [96.5 + index * 0.25 for index in range(31)]
    vix = [12.0 + index * 0.2 for index in range(31)]
    raw_cross_asset = {
        "vix": vix[-1],
        "dxy": dxy[-1],
        "oil": oil[-1],
        "hist": {"vix": vix, "dxy": dxy, "oil": oil},
    }

    core = CoreIngestionSnapshot.from_buffer(
        AS_OF, _base_buffer(raw_cross_asset)
    )
    staged = _map_core_to_staged(core)

    jpy = SignalStage().run("USDJPY", staged)
    inr = SignalStage().run("USDINR", staged)

    assert jpy.special_signal == pytest.approx(-1.0)
    assert inr.special_signal == pytest.approx(1.0)
    assert jpy.composite is not None and jpy.composite < 0
    assert inr.composite is not None and inr.composite > 0

    # The core coercion detached accepted histories from the provider payload.
    vix[0] = 999.0
    oil[-1] = -999.0
    assert staged.cross_asset["hist"]["vix"][0] == 12.0
    assert staged.cross_asset["hist"]["oil"][-1] == 75.0


def test_cross_asset_history_validation_is_atomic_per_leg_and_detached() -> None:
    valid = [float(index) for index in range(31)]
    invalid_bool = [*valid]
    invalid_bool[10] = True
    invalid_nonfinite = [*valid]
    invalid_nonfinite[10] = float("nan")
    raw_cross_asset = {
        "vix": 10**1000,
        "dxy": float("inf"),
        "oil": "75.5",
        "gold": 2_500,
        "copper": float("-inf"),
        "bitcoin": 100_000.0,
        "hist": {
            "vix": valid,
            "dxy": invalid_bool,
            "oil": invalid_nonfinite,
            "gold": [*valid[:10], "bad", *valid[11:]],
            "copper": [*valid[:10], float("inf"), *valid[11:]],
            "iron_ore": [*valid[:10], float("-inf"), *valid[11:]],
            "stoxx": valid,
            "bund_btp_spread": valid,
            "ecb_balance_sheet": valid,
            "bitcoin": valid,
        },
    }

    core = CoreIngestionSnapshot.from_buffer(
        AS_OF, _base_buffer(raw_cross_asset)
    )
    history = core.cross_asset["hist"]

    assert core.cross_asset["vix"] is None
    assert core.cross_asset["dxy"] is None
    assert core.cross_asset["oil"] == 75.5
    assert core.cross_asset["gold"] == 2_500.0
    assert core.cross_asset["copper"] is None
    assert "bitcoin" not in core.cross_asset
    assert set(history) == {
        "vix",
        "stoxx",
        "bund_btp_spread",
        "ecb_balance_sheet",
    }
    assert history["vix"] == valid
    assert history["vix"] is not valid

    valid[0] = 999.0
    assert history["vix"][0] == 0.0


def test_all_invalid_cross_asset_history_is_omitted_and_degraded() -> None:
    huge = 10**1000
    core = CoreIngestionSnapshot.from_buffer(
        AS_OF,
        _base_buffer(
            {
                "hist": {
                    "vix": [1.0, huge],
                    "dxy": [1.0, True],
                    "oil": [1.0, "2.0"],
                    "gold": [1.0, float("inf")],
                    "copper": [1.0, float("-inf")],
                    "iron_ore": [],
                    "stoxx": (1.0, 2.0),
                }
            }
        ),
    )
    staged = _map_core_to_staged(core)

    assert "hist" not in core.cross_asset
    assert "hist" not in staged.cross_asset
    assert all(value is None for value in core.cross_asset.values())
    assert staged.health.status == "DEGRADED"
    assert "cross_asset" in staged.health.missing_fields


@pytest.mark.parametrize("pair", ["USDJPY", "USDINR"])
def test_missing_cross_asset_history_remains_unavailable(pair: str) -> None:
    core = CoreIngestionSnapshot.from_buffer(
        AS_OF,
        _base_buffer({"vix": 18.0, "dxy": 104.0, "oil": 75.0}),
    )
    staged = _map_core_to_staged(core)

    assert "hist" not in core.cross_asset
    assert "hist" not in staged.cross_asset
    with pytest.raises(ValueError, match="directional_inputs_unavailable"):
        SignalStage().run(pair, staged)
