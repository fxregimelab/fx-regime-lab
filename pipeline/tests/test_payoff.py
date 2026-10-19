"""Oracle tests for the pure payoff arithmetic slice (PD-01).

Pinned oracle sources:

* ``docs/specs/payoff-desk/01-mandate.md`` - unit definitions, the all-in
  denominator ``D = G + A`` and the runner requirement ``5 + 6k + 2c``.
* ``docs/specs/payoff-desk/04-payoff-study.md`` - hand cases 1-13, including
  the ``G=100, A=10, cost=10`` parent that needs a 5.8R runner for 3 parent-R
  and fails at 5.2R.

The module under test is arithmetic over ``Decimal`` inputs only: it reads no
prices and touches no broker, model, database or network.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from src.paper.backtest.payoff import (
    ExitFill,
    PayoffUnits,
    RunnerRequirement,
    compute_payoff,
    solve_minimum_runner_price_r,
)
from src.paper.contracts import ContractError

TOLERANCE = Decimal("1e-25")


def fill(fraction: str, price_r: str) -> ExitFill:
    """One closed slice: fraction of the original quantity at a price-R."""
    return ExitFill(Decimal(fraction), Decimal(price_r))


def _untyped(value: object) -> Decimal:
    """Deliver a non-Decimal through the Decimal API to prove it is rejected."""
    return cast(Decimal, value)


def _payoff(
    *,
    initial_risk_cash: Decimal = Decimal("100"),
    reserve_cash: Decimal = Decimal("0"),
    fills: tuple[ExitFill, ...] = (fill("1", "1"),),
    total_costs_cash: Decimal = Decimal("0"),
) -> PayoffUnits:
    return compute_payoff(
        initial_risk_cash=initial_risk_cash,
        reserve_cash=reserve_cash,
        fills=fills,
        total_costs_cash=total_costs_cash,
    )


def _solve(
    *,
    initial_risk_cash: Decimal = Decimal("100"),
    reserve_cash: Decimal = Decimal("0"),
    closed_fills: tuple[ExitFill, ...] = (),
    runner_fraction: Decimal = Decimal("1"),
    target_net_parent_r: Decimal = Decimal("3"),
    total_costs_cash: Decimal = Decimal("0"),
) -> RunnerRequirement:
    return solve_minimum_runner_price_r(
        initial_risk_cash=initial_risk_cash,
        reserve_cash=reserve_cash,
        closed_fills=closed_fills,
        runner_fraction=runner_fraction,
        target_net_parent_r=target_net_parent_r,
        total_costs_cash=total_costs_cash,
    )


# --- study cases 1-5: the blended price-R arithmetic -------------------------


def test_half_at_one_r_plus_runner_at_three_r_is_two_price_r() -> None:
    """Study case 4: half at +1R then runner at +3R is +2R gross, NOT +3R."""
    units = _payoff(fills=(fill("0.5", "1"), fill("0.5", "3")))
    assert units.gross_price_r == Decimal("2")
    assert units.net_price_r == Decimal("2")
    assert units.gross_cash == Decimal("200")
    assert units.net_cash == Decimal("200")
    assert units.net_parent_r == Decimal("2")


def test_half_at_one_r_plus_runner_at_five_r_is_three_gross_price_r() -> None:
    """Study case 5: a +5R runner is +3R GROSS; costs make the net smaller."""
    units = _payoff(fills=(fill("0.5", "1"), fill("0.5", "5")), total_costs_cash=Decimal("10"))
    assert units.gross_price_r == Decimal("3")
    assert units.net_price_r == Decimal("2.9")
    assert units.net_cash == Decimal("290")
    assert units.net_parent_r == Decimal("2.9")
    assert units.net_parent_r < units.gross_price_r


def test_costs_are_charged_once_for_the_parent_not_once_per_exit_leg() -> None:
    """Two exit legs, one parent cost: charge 10 once, never 20.

    The caller owns the cost model; the module charges the supplied parent
    total exactly once, so an entry cost is not double counted because the
    parent has two exit legs.
    """
    units = _payoff(fills=(fill("0.5", "1"), fill("0.5", "5")), total_costs_cash=Decimal("10"))
    assert units.cost_cash == Decimal("10")
    assert units.net_price_r == units.gross_price_r - units.cost_cash / units.initial_risk_cash
    assert units.net_price_r == Decimal("2.9")
    assert units.net_cash == units.gross_cash - units.cost_cash


# --- units: price-R, cash and all-in parent-R are separate -------------------


def test_parent_denominator_is_all_in_g_plus_a_and_never_g_alone() -> None:
    """D = G + A. A 3 price-R outcome on G=100/A=10 is NOT 3 parent-R."""
    units = _payoff(reserve_cash=Decimal("10"), fills=(fill("1", "3"),))
    assert units.initial_risk_cash == Decimal("100")
    assert units.reserve_cash == Decimal("10")
    assert units.all_in_risk_cash == Decimal("110")
    assert units.gross_price_r == Decimal("3")
    assert units.gross_cash == Decimal("300")
    assert units.gross_parent_r == Decimal("300") / Decimal("110")
    assert units.net_parent_r < units.gross_price_r


def test_units_reconcile_across_cash_price_r_and_parent_r() -> None:
    """Every named unit reconciles: cash = price-R * G, parent-R = cash / D."""
    units = _payoff(
        reserve_cash=Decimal("10"),
        fills=(fill("0.5", "1"), fill("0.5", "5.8")),
        total_costs_cash=Decimal("10"),
    )
    assert units.all_in_risk_cash == units.initial_risk_cash + units.reserve_cash
    assert units.net_cash == units.gross_cash - units.cost_cash
    assert abs(units.gross_cash - units.gross_price_r * units.initial_risk_cash) < TOLERANCE
    assert abs(units.net_cash - units.net_price_r * units.initial_risk_cash) < TOLERANCE
    assert abs(units.gross_parent_r * units.all_in_risk_cash - units.gross_cash) < TOLERANCE
    assert abs(units.net_parent_r * units.all_in_risk_cash - units.net_cash) < TOLERANCE
    assert abs(
        units.net_price_r - (units.gross_price_r - units.cost_cash / units.initial_risk_cash)
    ) < TOLERANCE


def test_initial_risk_and_denominator_are_not_mutated_by_the_calculation() -> None:
    """The frozen reserve and the initial risk are inputs, never outputs."""
    fills = (fill("0.5", "1"), fill("0.5", "5.8"))
    first = _payoff(reserve_cash=Decimal("10"), fills=fills, total_costs_cash=Decimal("10"))
    second = _payoff(reserve_cash=Decimal("10"), fills=fills, total_costs_cash=Decimal("10"))
    assert first == second
    assert first.all_in_risk_cash == Decimal("110")
    assert first.initial_risk_cash == Decimal("100")
    assert first.reserve_cash == Decimal("10")


# --- study case 13: the all-in parent-R admission ----------------------------


def test_runner_at_five_point_eight_reaches_three_parent_r() -> None:
    """G=100, A=10, cost=10: half at 1R and runner at 5.8R gives 330/110 = 3R."""
    units = _payoff(
        reserve_cash=Decimal("10"),
        fills=(fill("0.5", "1"), fill("0.5", "5.8")),
        total_costs_cash=Decimal("10"),
    )
    assert units.gross_price_r == Decimal("3.4")
    assert units.net_price_r == Decimal("3.3")
    assert units.net_cash == Decimal("330")
    assert units.all_in_risk_cash == Decimal("110")
    assert units.net_parent_r == Decimal("330") / Decimal("110")
    assert units.net_parent_r == Decimal("3")


def test_runner_at_five_point_two_fails_three_parent_r() -> None:
    """5.2R gives 3 price-R net but only 300/110 = 2.727 parent-R: admission fails."""
    units = _payoff(
        reserve_cash=Decimal("10"),
        fills=(fill("0.5", "1"), fill("0.5", "5.2")),
        total_costs_cash=Decimal("10"),
    )
    assert units.gross_price_r == Decimal("3.1")
    assert units.net_price_r == Decimal("3")
    assert units.net_cash == Decimal("300")
    assert units.net_parent_r == Decimal("300") / Decimal("110")
    assert units.net_parent_r < Decimal("3")


# --- solving the minimum runner price-R --------------------------------------


def test_minimum_runner_price_r_matches_the_mandate_closed_form() -> None:
    """Half at 1R needs runner >= 5 + 6k + 2c price-R for 3 all-in parent-R."""
    requirement = _solve(
        reserve_cash=Decimal("10"),
        closed_fills=(fill("0.5", "1"),),
        runner_fraction=Decimal("0.5"),
        target_net_parent_r=Decimal("3"),
        total_costs_cash=Decimal("10"),
    )
    assert requirement.runner_price_r == Decimal("5.8")
    assert requirement.runner_price_r == (
        Decimal("5") + Decimal("6") * Decimal("0.1") + Decimal("2") * Decimal("0.1")
    )
    assert requirement.required_net_price_r == Decimal("3.3")
    assert requirement.required_gross_price_r == Decimal("3.4")
    assert requirement.closed_gross_price_r == Decimal("0.5")
    assert requirement.runner_fraction == Decimal("0.5")


def test_solved_runner_round_trips_to_the_target_parent_r() -> None:
    """The solved runner price is the threshold that reproduces the target."""
    requirement = _solve(
        reserve_cash=Decimal("10"),
        closed_fills=(fill("0.5", "1"),),
        runner_fraction=Decimal("0.5"),
        target_net_parent_r=Decimal("3"),
        total_costs_cash=Decimal("10"),
    )
    units = _payoff(
        reserve_cash=Decimal("10"),
        fills=(fill("0.5", "1"), fill("0.5", str(requirement.runner_price_r))),
        total_costs_cash=Decimal("10"),
    )
    assert units.net_cash == Decimal("330")
    assert units.net_parent_r == Decimal("3")


def test_no_partial_plan_needs_price_target_of_three_times_one_plus_k_plus_c() -> None:
    """Mandate: a no-partial plan needs price target >= 3*(1+k) + c."""
    requirement = _solve(
        reserve_cash=Decimal("10"),
        runner_fraction=Decimal("1"),
        target_net_parent_r=Decimal("3"),
        total_costs_cash=Decimal("10"),
    )
    assert requirement.runner_price_r == Decimal("3.4")
    assert requirement.runner_price_r == (
        Decimal("3") * (Decimal("1") + Decimal("0.1")) + Decimal("0.1")
    )


def test_zero_partial_plan_is_the_single_leg_plan() -> None:
    """A zero partial fraction is a no-partial plan, not a missing leg."""
    requirement = _solve(runner_fraction=Decimal("1"), target_net_parent_r=Decimal("3"))
    assert requirement.runner_price_r == Decimal("3")
    assert requirement.closed_gross_price_r == Decimal("0")


def test_fully_closed_plan_has_no_runner_to_solve_and_returns_no_infinity() -> None:
    """A settled plan has no runner leg: fail closed instead of dividing by zero."""
    with pytest.raises(ContractError) as excinfo:
        _solve(closed_fills=(fill("1", "1"),), runner_fraction=Decimal("0"))
    assert excinfo.value.code == "LOT_SPLIT_INVALID"
    assert "runner" in excinfo.value.detail
    assert "Infinity" not in str(excinfo.value)


def test_runner_fraction_must_be_within_zero_and_one() -> None:
    with pytest.raises(ContractError) as excinfo:
        _solve(runner_fraction=Decimal("1.5"))
    assert excinfo.value.code == "LOT_SPLIT_INVALID"
    with pytest.raises(ContractError):
        _solve(runner_fraction=Decimal("-0.5"))


def test_solver_rejects_a_plan_whose_quantities_do_not_sum_to_one() -> None:
    with pytest.raises(ContractError) as excinfo:
        _solve(closed_fills=(fill("0.5", "1"),), runner_fraction=Decimal("0.4"))
    assert excinfo.value.code == "LOT_SPLIT_INVALID"


# --- partial structure edge cases -------------------------------------------


def test_zero_fraction_fill_contributes_nothing_to_the_gross() -> None:
    units = _payoff(fills=(fill("0", "5"), fill("1", "2")))
    assert units.gross_price_r == Decimal("2")
    assert units.gross_cash == Decimal("200")


def test_full_size_partial_settles_the_whole_parent() -> None:
    """A 100% partial is a complete settlement with no runner left."""
    units = _payoff(reserve_cash=Decimal("10"), fills=(fill("1", "1"),))
    assert units.gross_price_r == Decimal("1")
    assert units.gross_cash == Decimal("100")
    assert units.net_parent_r == Decimal("100") / Decimal("110")


# --- long/short symmetry in normalised price-R --------------------------------


def test_long_and_short_normalized_price_r_give_identical_payoff() -> None:
    """Price-R is normalised in the trade direction, so the math is symmetric."""
    long_entry, long_stop = Decimal("100"), Decimal("99")
    short_entry, short_stop = Decimal("100"), Decimal("101")

    def price_r(is_long: bool, exit_price: Decimal) -> Decimal:
        if is_long:
            return (exit_price - long_entry) / (long_entry - long_stop)
        return (short_entry - exit_price) / (short_stop - short_entry)

    long_fills = (
        fill("0.5", str(price_r(True, Decimal("101")))),
        fill("0.5", str(price_r(True, Decimal("103")))),
    )
    short_fills = (
        fill("0.5", str(price_r(False, Decimal("99")))),
        fill("0.5", str(price_r(False, Decimal("97")))),
    )
    assert long_fills == short_fills
    long_units = _payoff(
        reserve_cash=Decimal("10"), fills=long_fills, total_costs_cash=Decimal("10")
    )
    short_units = _payoff(
        reserve_cash=Decimal("10"), fills=short_fills, total_costs_cash=Decimal("10")
    )
    assert long_units == short_units
    assert long_units.gross_price_r == Decimal("2")
    assert long_units.net_parent_r == short_units.net_parent_r


# --- precision, types and validation -----------------------------------------


def test_decimal_arithmetic_is_exact_and_never_binary_float() -> None:
    """Decimal inputs keep their scale; no float ever enters the result."""
    units = _payoff(
        initial_risk_cash=Decimal("0.1"),
        reserve_cash=Decimal("0.2"),
        fills=(fill("0.5", "0.1"), fill("0.5", "0.2")),
        total_costs_cash=Decimal("0.01"),
    )
    assert units.gross_price_r == Decimal("0.15")
    assert units.net_price_r == Decimal("0.05")
    assert units.net_cash == Decimal("0.005")
    assert units.all_in_risk_cash == Decimal("0.3")
    assert units.net_parent_r == Decimal("0.005") / Decimal("0.3")
    assert isinstance(units.net_parent_r, Decimal)
    assert not isinstance(units.net_parent_r, float)
    assert abs(units.net_parent_r * Decimal("0.3") - Decimal("0.005")) < TOLERANCE


@pytest.mark.parametrize(
    "value",
    [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity"), True, False, 100, 100.5],
)
def test_non_finite_and_non_decimal_inputs_are_rejected(value: object) -> None:
    with pytest.raises(ContractError):
        _payoff(initial_risk_cash=_untyped(value))
    with pytest.raises(ContractError):
        _payoff(reserve_cash=_untyped(value))
    with pytest.raises(ContractError):
        _payoff(total_costs_cash=_untyped(value))


def test_non_finite_exit_prices_are_rejected() -> None:
    with pytest.raises(ContractError):
        ExitFill(Decimal("1"), Decimal("NaN"))
    with pytest.raises(ContractError):
        ExitFill(Decimal("1"), Decimal("Infinity"))
    with pytest.raises(ContractError):
        _payoff(fills=(fill("1", "NaN"),))


def test_initial_risk_must_be_positive_and_reserve_non_negative() -> None:
    with pytest.raises(ContractError) as excinfo:
        _payoff(initial_risk_cash=Decimal("0"))
    assert excinfo.value.code == "INVALID_NUMBER"
    with pytest.raises(ContractError):
        _payoff(initial_risk_cash=Decimal("-100"))
    with pytest.raises(ContractError):
        _payoff(reserve_cash=Decimal("-1"))


def test_negative_costs_are_rejected() -> None:
    with pytest.raises(ContractError) as excinfo:
        _payoff(total_costs_cash=Decimal("-1"))
    assert excinfo.value.code == "INVALID_NUMBER"


def test_fill_fractions_must_conserve_quantity() -> None:
    with pytest.raises(ContractError) as excinfo:
        _payoff(fills=(fill("0.5", "1"), fill("0.4", "5")))
    assert excinfo.value.code == "LOT_SPLIT_INVALID"
    with pytest.raises(ContractError):
        _payoff(fills=(fill("0.5", "1"), fill("0.6", "5")))


def test_fractions_outside_zero_to_one_are_rejected() -> None:
    with pytest.raises(ContractError) as excinfo:
        ExitFill(Decimal("1.5"), Decimal("1"))
    assert excinfo.value.code == "LOT_SPLIT_INVALID"
    with pytest.raises(ContractError):
        ExitFill(Decimal("-0.1"), Decimal("1"))


def test_empty_fills_are_rejected() -> None:
    with pytest.raises(ContractError) as excinfo:
        _payoff(fills=())
    assert excinfo.value.code == "INVALID_SCHEMA"


# --- honesty: arithmetic only, no feasibility or guarantee claim -------------


def test_no_feasibility_or_guarantee_is_claimed() -> None:
    units = _payoff(reserve_cash=Decimal("10"), fills=(fill("0.5", "1"), fill("0.5", "5.8")))
    requirement = _solve(
        reserve_cash=Decimal("10"),
        closed_fills=(fill("0.5", "1"),),
        runner_fraction=Decimal("0.5"),
        target_net_parent_r=Decimal("3"),
        total_costs_cash=Decimal("10"),
    )
    for name in ("feasible", "reachable", "guaranteed", "probability", "hit_probability"):
        assert not hasattr(units, name)
        assert not hasattr(requirement, name)
    doc = (solve_minimum_runner_price_r.__doc__ or "").lower()
    assert "not a feasibility" in doc
    assert "not a guarantee" in doc


def test_payoff_module_performs_no_io_and_calls_no_service() -> None:
    """The slice is arithmetic: no files, sockets, brokers, models or databases."""
    source = (
        Path(__file__).resolve().parents[1] / "src" / "paper" / "backtest" / "payoff.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "import os",
        "import socket",
        "import subprocess",
        "import requests",
        "import httpx",
        "urllib",
        "sqlite3",
        "psycopg",
        "supabase",
        "open(",
    ):
        assert forbidden not in source, forbidden
