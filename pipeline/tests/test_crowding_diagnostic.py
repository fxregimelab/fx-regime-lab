"""Independent examples for the frozen crowding-description contract."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Any

import pytest

from src.analysis.asymmetry import compute_crowding_diagnostic, compute_pain_index
from src.types import CotRow, SpotBar


def _cot(
    observed: date,
    *,
    pair: str = "EURUSD",
    net: Any = 100,
    asset_mgr: Any = 60,
    lev_money: Any = -20,
) -> CotRow:
    return CotRow(
        date=observed,
        pair=pair,
        net_long=net,
        open_interest=1_000,
        asset_mgr_net=asset_mgr,
        lev_money_net=lev_money,
    )


def _spot(observed: date, close: float, *, pair: str = "EURUSD") -> SpotBar:
    return SpotBar(
        date=observed,
        pair=pair,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=0.0,
    )


def _run(
    *,
    pair: str = "EURUSD",
    direction: str | None = "BULLISH",
    cot_rows: list[CotRow] | None = None,
    spot_bars: list[SpotBar] | None = None,
    as_of: date = date(2026, 2, 9),
    call_id: int | None = 17,
) -> dict[str, Any]:
    return compute_crowding_diagnostic(
        pair=pair,
        as_of_date=as_of,
        predicted_direction=direction,
        cot_rows=[] if cot_rows is None else cot_rows,
        spot_bars=[] if spot_bars is None else spot_bars,
        call_id=call_id,
    )


def test_exact_schema_and_positive_eur_alignment() -> None:
    result = _run(cot_rows=[_cot(date(2026, 2, 3))])

    assert set(result) == {
        "version",
        "pair",
        "call_id",
        "as_of_date",
        "predicted_direction",
        "cot",
        "price",
        "participant_loss_estimate",
        "squeeze_probability",
        "point_in_time_qualified",
    }
    assert result["version"] == "crowding-description-v1"
    assert result["call_id"] == 17
    assert result["participant_loss_estimate"] is None
    assert result["squeeze_probability"] is None
    assert result["point_in_time_qualified"] is False
    assert result["cot"] == {
        "status": "PROVISIONAL",
        "report_date": "2026-02-03",
        "report_age_days": 6,
        "net_long": 100,
        "asset_mgr_net": 60,
        "lev_money_net": -20,
        "pair_direction": 1,
        "alignment": "ALIGNED",
        "series_definition": "UNKNOWN",
        "release_status": "UNVERIFIED",
        "rank_percentile": None,
        "reasons": [
            "CATEGORY_PROVENANCE_UNAVAILABLE",
            "RELEASE_METADATA_UNAVAILABLE",
        ],
    }


def test_positive_jpy_net_has_opposite_pair_orientation() -> None:
    result = _run(
        pair="USD/JPY",
        cot_rows=[_cot(date(2026, 2, 3), pair="USDJPY", net=100)],
    )

    assert result["pair"] == "USDJPY"
    assert result["cot"]["pair_direction"] == -1
    assert result["cot"]["alignment"] == "OPPOSED"


def test_negative_net_uses_actual_sign_and_not_legacy_rank() -> None:
    result = _run(
        direction="BEARISH",
        cot_rows=[_cot(date(2026, 2, 3), net=-100)],
    )

    assert result["cot"]["net_long"] == -100
    assert result["cot"]["pair_direction"] == -1
    assert result["cot"]["alignment"] == "ALIGNED"
    assert result["cot"]["rank_percentile"] is None


def test_zero_neutral_and_missing_direction_are_distinct() -> None:
    row = _cot(date(2026, 2, 3), net=0, asset_mgr=None, lev_money=None)
    flat = _run(cot_rows=[row])
    neutral = _run(direction="NEUTRAL", cot_rows=[row])
    missing = _run(direction=None, cot_rows=[row])

    assert flat["cot"]["pair_direction"] == 0
    assert flat["cot"]["alignment"] == "FLAT_REPORTED_NET"
    assert neutral["cot"]["alignment"] == "ABSTAINED"
    assert missing["cot"]["alignment"] == "UNAVAILABLE"
    assert "PREDICTED_DIRECTION_UNAVAILABLE" in missing["cot"]["reasons"]
    assert "ASSET_MGR_NET_UNAVAILABLE" in flat["cot"]["reasons"]
    assert "LEV_MONEY_NET_UNAVAILABLE" in flat["cot"]["reasons"]

    invalid_categories = _run(
        cot_rows=[_cot(date(2026, 2, 3), asset_mgr=True, lev_money=1.0)]
    )
    assert invalid_categories["cot"]["status"] == "PROVISIONAL"
    assert invalid_categories["cot"]["net_long"] == 100
    assert invalid_categories["cot"]["asset_mgr_net"] is None
    assert invalid_categories["cot"]["lev_money_net"] is None
    assert "INVALID_ASSET_MGR_NET" in invalid_categories["cot"]["reasons"]
    assert "INVALID_LEV_MONEY_NET" in invalid_categories["cot"]["reasons"]


def test_cot_selection_is_ordered_fenced_and_deduplicated_without_mutation() -> None:
    latest = _cot(date(2026, 2, 3), net=125)
    rows = [
        _cot(date(2026, 2, 10), net=-999),
        latest,
        _cot(date(2026, 2, 3), net=125),
        _cot(date(2026, 1, 27), net=-50),
        _cot(date(2026, 2, 4), pair="USDJPY", net=999),
    ]
    before = deepcopy(rows)

    forward = _run(cot_rows=rows)
    reverse = _run(cot_rows=list(reversed(rows)))

    assert forward["cot"] == reverse["cot"]
    assert forward["cot"]["report_date"] == "2026-02-03"
    assert forward["cot"]["net_long"] == 125
    assert rows == before

    valid = _cot(date(2026, 2, 3), net=1, asset_mgr=2, lev_money=3)
    type_mismatches = [
        _cot(date(2026, 2, 3), net=True, asset_mgr=2, lev_money=3),
        _cot(date(2026, 2, 3), net=1.0, asset_mgr=2, lev_money=3),
        _cot(date(2026, 2, 3), net=1, asset_mgr=True, lev_money=3),
        _cot(date(2026, 2, 3), net=1, asset_mgr=2.0, lev_money=3),
        _cot(date(2026, 2, 3), net=1, asset_mgr=2, lev_money=True),
        _cot(date(2026, 2, 3), net=1, asset_mgr=2, lev_money=3.0),
    ]
    for mismatch in type_mismatches:
        for same_date_rows in ([valid, mismatch], [mismatch, valid]):
            conflicted = _run(
                cot_rows=[_cot(date(2026, 1, 27), net=-50), *same_date_rows]
            )
            assert conflicted["cot"]["status"] == "UNAVAILABLE"
            assert "CONFLICTING_LATEST_COT_REPORT" in conflicted["cot"]["reasons"]


def test_conflicting_latest_cot_report_fails_closed_without_older_fallback() -> None:
    result = _run(
        cot_rows=[
            _cot(date(2026, 1, 27), net=50),
            _cot(date(2026, 2, 3), net=100),
            _cot(date(2026, 2, 3), net=101),
        ]
    )

    assert result["cot"]["status"] == "UNAVAILABLE"
    assert result["cot"]["report_date"] == "2026-02-03"
    assert result["cot"]["net_long"] is None
    assert "CONFLICTING_LATEST_COT_REPORT" in result["cot"]["reasons"]


@pytest.mark.parametrize("bad_net", [True, 1.0, "1", 9_007_199_254_740_992])
def test_malformed_and_overflowing_contract_values_fail_only_cot(bad_net: Any) -> None:
    bars = [_spot(date(2026, 1, 1) + timedelta(days=i), 100.0) for i in range(40)]
    result = _run(cot_rows=[_cot(date(2026, 2, 3), net=bad_net)], spot_bars=bars)

    assert result["cot"]["status"] == "UNAVAILABLE"
    assert "INVALID_NET_LONG" in result["cot"]["reasons"]
    assert result["price"]["status"] == "PROVISIONAL"
    assert result["price"]["mean_close_40"] == 100.0


def test_unsupported_inr_cot_does_not_disable_price() -> None:
    bars = [
        _spot(date(2026, 1, 1) + timedelta(days=i), 80.0, pair="USDINR")
        for i in range(40)
    ]
    result = _run(
        pair="USDINR",
        cot_rows=[_cot(date(2026, 2, 3), pair="USDINR", net=999)],
        spot_bars=bars,
    )

    assert result["cot"]["status"] == "UNAVAILABLE"
    assert result["cot"]["reasons"][0] == "UNSUPPORTED_COT_PAIR"
    assert result["price"]["mean_close_40"] == 80.0


def test_price_requires_40_observations_for_mean() -> None:
    start = date(2026, 1, 1)
    thirty_nine = [_spot(start + timedelta(days=i), 100.0) for i in range(39)]
    values = [90.0] * 20 + [110.0] * 20
    forty = [_spot(start + timedelta(days=i), value) for i, value in enumerate(values)]

    short = _run(spot_bars=thirty_nine)
    complete = _run(spot_bars=forty)

    assert short["price"]["observation_count"] == 39
    assert short["price"]["spot"] == 100.0
    assert short["price"]["mean_close_40"] is None
    assert short["price"]["relative_to_mean_pct"] is None
    assert complete["price"]["observation_count"] == 40
    assert complete["price"]["mean_close_40"] == pytest.approx(100.0)
    assert complete["price"]["relative_to_mean_pct"] == pytest.approx(10.0)

    underflow = _run(
        spot_bars=[_spot(start + timedelta(days=i), 5e-324) for i in range(40)]
    )
    assert underflow["price"]["status"] == "UNAVAILABLE"
    assert underflow["price"]["spot"] == 5e-324
    assert underflow["price"]["mean_close_40"] is None
    assert "INVALID_PRICE_ARITHMETIC" in underflow["price"]["reasons"]


def test_price_is_ordered_fenced_and_conflict_is_component_local() -> None:
    start = date(2026, 1, 1)
    bars = [_spot(start + timedelta(days=i), 100.0) for i in range(40)]
    bars.extend([_spot(date(2026, 2, 10), 999.0), _spot(date(2026, 2, 9), 100.0)])
    before = deepcopy(bars)
    fenced = _run(spot_bars=list(reversed(bars)))

    assert fenced["price"]["status"] == "PROVISIONAL"
    assert fenced["price"]["latest_date"] == "2026-02-09"
    assert fenced["price"]["mean_close_40"] == 100.0
    assert bars == before

    result = _run(
        cot_rows=[_cot(date(2026, 2, 3))],
        spot_bars=[*bars, _spot(date(2026, 2, 9), 101.0)],
    )

    assert result["price"]["status"] == "UNAVAILABLE"
    assert result["price"]["reasons"] == ["INVALID_SPOT_HISTORY"]
    assert result["cot"]["status"] == "PROVISIONAL"


def test_configuration_validation_and_retired_pain_api() -> None:
    with pytest.raises(ValueError, match="pair"):
        _run(pair="GBPUSD")
    with pytest.raises(ValueError, match="pair"):
        _run(pair="E/URUSD")
    with pytest.raises(ValueError, match="predicted_direction"):
        _run(direction="UP")
    invalid_direction: Any = []
    with pytest.raises(ValueError, match="predicted_direction"):
        _run(direction=invalid_direction)
    for call_id in (True, 0, -1, 9_007_199_254_740_992):
        with pytest.raises(ValueError, match="call_id"):
            _run(call_id=call_id)
    with pytest.raises(RuntimeError, match="compute_crowding_diagnostic"):
        compute_pain_index()
