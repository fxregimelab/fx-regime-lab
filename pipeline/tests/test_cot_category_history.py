"""Regression tests for homogeneous COT category history."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.signals.cot import compute_cot_smart_spread_percentile
from src.types import CotRow


def _row(
    week: int,
    *,
    asset_manager: int | None,
    leveraged_money: int | None,
    net_long: int = 999_999,
    pair: str = "EURUSD",
) -> CotRow:
    return CotRow(
        date=date(2026, 1, 2) + timedelta(weeks=week),
        pair=pair,
        net_long=net_long,
        open_interest=1_000,
        asset_mgr_net=asset_manager,
        lev_money_net=leveraged_money,
    )


def test_mixed_history_uses_only_complete_category_spreads() -> None:
    rows = [
        _row(0, asset_manager=10, leveraged_money=10),  # spread 0
        _row(1, asset_manager=None, leveraged_money=None, net_long=-1_000_000),
        _row(2, asset_manager=30, leveraged_money=20),  # spread 10
        _row(3, asset_manager=40, leveraged_money=None, net_long=-1_000_000),
        _row(4, asset_manager=50, leveraged_money=30),  # spread 20
        _row(5, asset_manager=35, leveraged_money=20),  # current spread 15
    ]

    result = compute_cot_smart_spread_percentile(rows, "EURUSD", min_reports=3)

    assert result == pytest.approx(200.0 / 3.0)


def test_all_missing_categories_do_not_fall_back_to_net_long() -> None:
    rows = [
        _row(i, asset_manager=None, leveraged_money=None, net_long=i * 100)
        for i in range(10)
    ]

    assert compute_cot_smart_spread_percentile(rows, "EURUSD", min_reports=1) is None


@pytest.mark.parametrize(
    ("asset_manager", "leveraged_money"),
    [(None, 5), (5, None), (None, None)],
)
def test_latest_eligible_report_missing_either_category_is_unavailable(
    asset_manager: int | None,
    leveraged_money: int | None,
) -> None:
    rows = [
        _row(i, asset_manager=i * 10, leveraged_money=0)
        for i in range(4)
    ]
    rows.append(
        _row(
            4,
            asset_manager=asset_manager,
            leveraged_money=leveraged_money,
            net_long=1_000_000,
        )
    )

    assert compute_cot_smart_spread_percentile(rows, "EURUSD", min_reports=3) is None


def test_as_of_preserves_report_cutoff_and_ignores_later_rows() -> None:
    rows = [
        _row(0, asset_manager=10, leveraged_money=10),  # spread 0
        _row(1, asset_manager=20, leveraged_money=10),  # spread 10
        _row(2, asset_manager=30, leveraged_money=10),  # spread 20
        _row(3, asset_manager=25, leveraged_money=10),  # cutoff/current spread 15
        _row(4, asset_manager=None, leveraged_money=None),
    ]

    result = compute_cot_smart_spread_percentile(
        rows,
        "EURUSD",
        as_of=rows[3].date,
        min_reports=3,
    )

    assert result == pytest.approx(200.0 / 3.0)


def test_conflicting_same_date_values_are_unavailable_in_any_arrival_order() -> None:
    history = [
        _row(i, asset_manager=i * 10, leveraged_money=0)
        for i in range(3)
    ]
    current_a = _row(3, asset_manager=40, leveraged_money=5)
    current_b = _row(3, asset_manager=45, leveraged_money=5)

    forward = compute_cot_smart_spread_percentile(
        [*history, current_a, current_b], "EURUSD", min_reports=3
    )
    reverse = compute_cot_smart_spread_percentile(
        [*history, current_b, current_a], "EURUSD", min_reports=3
    )

    assert forward is None
    assert reverse is None


def test_conflicting_historical_duplicate_is_unavailable() -> None:
    rows = [
        _row(0, asset_manager=10, leveraged_money=0),
        _row(1, asset_manager=20, leveraged_money=0),
        _row(1, asset_manager=20, leveraged_money=1),
        _row(2, asset_manager=30, leveraged_money=0),
        _row(3, asset_manager=40, leveraged_money=0),
    ]

    assert compute_cot_smart_spread_percentile(rows, "EURUSD", min_reports=2) is None


def test_equal_duplicates_are_neutral() -> None:
    rows = [
        _row(0, asset_manager=10, leveraged_money=10),
        _row(1, asset_manager=20, leveraged_money=10),
        _row(2, asset_manager=30, leveraged_money=10),
        _row(3, asset_manager=25, leveraged_money=10),
        _row(3, asset_manager=25, leveraged_money=10, net_long=-123),
    ]

    result = compute_cot_smart_spread_percentile(rows, "EURUSD", min_reports=3)

    assert result == pytest.approx(200.0 / 3.0)


def test_minimum_counts_only_usable_distinct_historical_reports() -> None:
    rows = [
        _row(0, asset_manager=10, leveraged_money=0),
        _row(1, asset_manager=None, leveraged_money=0),
        _row(2, asset_manager=30, leveraged_money=0),
        _row(3, asset_manager=40, leveraged_money=0),
    ]

    assert compute_cot_smart_spread_percentile(rows, "EURUSD", min_reports=3) is None


def test_current_report_without_reference_history_is_unavailable() -> None:
    rows = [_row(0, asset_manager=10, leveraged_money=0)]

    assert compute_cot_smart_spread_percentile(rows, "EURUSD", min_reports=0) is None


def test_report_window_does_not_expand_to_replace_missing_category_history() -> None:
    rows = [
        _row(0, asset_manager=0, leveraged_money=0),
        _row(1, asset_manager=10, leveraged_money=0),
        _row(2, asset_manager=20, leveraged_money=0),
        _row(3, asset_manager=None, leveraged_money=0),
        _row(4, asset_manager=40, leveraged_money=0),
        _row(5, asset_manager=50, leveraged_money=0),
    ]

    result = compute_cot_smart_spread_percentile(
        rows,
        "EURUSD",
        window_reports=4,
        min_reports=3,
    )

    assert result is None
