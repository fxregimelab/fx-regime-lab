"""Pure payoff arithmetic for the private desk: price-R versus all-in parent-R.

Unit convention (``docs/specs/payoff-desk/01-mandate.md``):

``G``
    Initial cash loss from entry to the ORIGINAL stop on the original
    quantity: the price-stop risk in cash. Strictly positive.
``A``
    The frozen initial cost/gap reserve in cash. Never resized, never moved.
``D = G + A``
    The protected parent denominator (``immutable_initial_risk_usd``). The
    all-in risk, never the price-stop risk alone.
``k = A / G``
    The reserve expressed in price-R units.
``c = cost / G``
    The actual (or scenario) parent cost expressed in price-R units.

Exit prices are PRICE-R multiples of the original stop distance, always
normalised in the direction of the trade: ``0`` is the entry, ``-1`` is the
original stop and ``+1`` is one stop-distance in favour of the trade. A long
and a short use the same normalisation, so this arithmetic is side-agnostic
and the caller converts prices into price-R.

    gross_price_R  = sum(fraction_i * price_R_i)
    net_price_R    = gross_price_R - c
    net_parent_R   = net_price_R * G / (G + A)   ==   net_price_R / (1 + k)

``total_costs_cash`` is the TOTAL cost of the parent (entry plus exits) and is
charged exactly once, so a caller must not pre-charge entry costs per exit
leg. The caller supplies the frozen modelled cost ``C_hat`` (c_hat = C_hat/G)
for a planned admission scenario and the actual cost ``C`` (c = C/G) for
settlement; the same formulas apply to both, and the scenario's own costs are
used, never an unrelated average spread.

The reserve ``A`` is a denominator component only. It is never deducted from
the payoff, and neither ``D`` nor the initial ``A`` is replaced at settlement.

This module is arithmetic only: it reads no prices, contacts no broker,
writes no ledger, sizes nothing and never claims that a planned target is
reachable. A solved runner price is a requirement, never a promise.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext

from src.paper.contracts import ContractError

__all__ = [
    "ExitFill",
    "PayoffUnits",
    "RunnerRequirement",
    "compute_payoff",
    "solve_minimum_runner_price_r",
]

# Pinned so the arithmetic is deterministic whatever the ambient decimal
# context is, and so no value ever passes through binary floating point.
_PRECISION = 28
_ARITHMETIC = Context(prec=_PRECISION)


def _decimal(name: str, value: object) -> Decimal:
    """Return a finite Decimal; bool, int and float are rejected outright."""
    if isinstance(value, bool) or not isinstance(value, Decimal):
        raise ContractError(
            "INVALID_SCHEMA",
            f"{name}: a finite Decimal is required (bool, int and float are rejected)",
        )
    if not value.is_finite():
        raise ContractError("INVALID_NUMBER", f"{name}: a finite Decimal is required")
    return value


def _positive(name: str, value: object) -> Decimal:
    amount = _decimal(name, value)
    if amount <= 0:
        raise ContractError("INVALID_NUMBER", f"{name}: a positive Decimal is required")
    return amount


def _non_negative(name: str, value: object) -> Decimal:
    amount = _decimal(name, value)
    if amount < 0:
        raise ContractError("INVALID_NUMBER", f"{name}: a non-negative Decimal is required")
    return amount


def _fraction(name: str, value: object) -> Decimal:
    amount = _decimal(name, value)
    if amount < 0 or amount > 1:
        raise ContractError("LOT_SPLIT_INVALID", f"{name}: a fraction within 0..1 is required")
    return amount


@dataclass(frozen=True)
class ExitFill:
    """One closed slice of the original quantity, in normalised price-R.

    ``fraction`` is the share of the ORIGINAL quantity closed by this fill and
    ``price_r`` is the closed price in price-R units of the original stop
    distance. Neither field is an all-in parent-R value.
    """

    fraction: Decimal
    price_r: Decimal

    def __post_init__(self) -> None:
        _fraction("ExitFill.fraction", self.fraction)
        _decimal("ExitFill.price_r", self.price_r)


@dataclass(frozen=True)
class PayoffUnits:
    """One parent outcome with every unit named separately.

    The ``*_price_r`` fields are multiples of the ORIGINAL stop distance. The
    ``*_parent_r`` fields are multiples of the protected all-in denominator
    ``D = G + A``. The two scales never share a field.
    """

    initial_risk_cash: Decimal
    reserve_cash: Decimal
    all_in_risk_cash: Decimal
    cost_cash: Decimal
    gross_price_r: Decimal
    net_price_r: Decimal
    gross_cash: Decimal
    net_cash: Decimal
    gross_parent_r: Decimal
    net_parent_r: Decimal

    def __post_init__(self) -> None:
        for name, value in (
            ("initial_risk_cash", self.initial_risk_cash),
            ("reserve_cash", self.reserve_cash),
            ("all_in_risk_cash", self.all_in_risk_cash),
            ("cost_cash", self.cost_cash),
            ("gross_price_r", self.gross_price_r),
            ("net_price_r", self.net_price_r),
            ("gross_cash", self.gross_cash),
            ("net_cash", self.net_cash),
            ("gross_parent_r", self.gross_parent_r),
            ("net_parent_r", self.net_parent_r),
        ):
            _decimal(f"PayoffUnits.{name}", value)
        if self.all_in_risk_cash != self.initial_risk_cash + self.reserve_cash:
            raise ContractError(
                "INVALID_NUMBER",
                "PayoffUnits.all_in_risk_cash must equal the initial risk plus the frozen reserve",
            )


@dataclass(frozen=True)
class RunnerRequirement:
    """The algebraic runner price-R required by a planned net parent-R outcome.

    This is arithmetic, not a promise. It is not a feasibility certificate,
    not a guarantee that the market reaches the price, not permission to
    widen a stop or to manufacture a distant target, and not evidence that
    the target is reachable at all. Reachability, sizing and stop placement
    stay with the owner and the later runtime packets.
    """

    runner_price_r: Decimal
    runner_fraction: Decimal
    target_net_parent_r: Decimal
    required_net_price_r: Decimal
    required_gross_price_r: Decimal
    closed_gross_price_r: Decimal
    initial_risk_cash: Decimal
    reserve_cash: Decimal
    all_in_risk_cash: Decimal
    cost_cash: Decimal


def _closed_fractions(
    fills: Sequence[ExitFill], name: str
) -> tuple[Decimal, Decimal]:
    """Return (total closed fraction, gross price-R) for the given fills."""
    total = Decimal(0)
    gross = Decimal(0)
    for index, item in enumerate(fills):
        if not isinstance(item, ExitFill):
            raise ContractError("INVALID_SCHEMA", f"{name}[{index}]: ExitFill required")
        total += _fraction(f"{name}[{index}].fraction", item.fraction)
        gross += item.fraction * _decimal(f"{name}[{index}].price_r", item.price_r)
    return total, gross


def compute_payoff(
    *,
    initial_risk_cash: Decimal,
    reserve_cash: Decimal,
    fills: Sequence[ExitFill],
    total_costs_cash: Decimal,
) -> PayoffUnits:
    """Compute gross/net price-R and all-in parent-R for one parent outcome.

    ``fills`` must close the whole original quantity exactly once: the
    fractions sum to 1. ``total_costs_cash`` is the parent's total cost for
    this scenario (frozen modelled ``C_hat`` for a planned admission, actual
    ``C`` for settlement) and is charged exactly once here, so entry costs are
    not double counted because the parent has two exit legs.

    The initial risk and the frozen reserve are inputs. Neither is resized,
    moved or derived, the all-in denominator stays ``G + A``, and the reserve
    is never deducted from the payoff.
    """
    g = _positive("initial_risk_cash", initial_risk_cash)
    a = _non_negative("reserve_cash", reserve_cash)
    costs = _non_negative("total_costs_cash", total_costs_cash)
    if not fills:
        raise ContractError(
            "INVALID_SCHEMA", "compute_payoff: at least one closed fill is required"
        )
    with localcontext(_ARITHMETIC):
        total_fraction, gross_price_r = _closed_fractions(fills, "fills")
        if total_fraction != 1:
            raise ContractError(
                "LOT_SPLIT_INVALID",
                "compute_payoff: fill fractions must sum to exactly 1",
            )
        all_in = g + a
        gross_cash = gross_price_r * g
        net_cash = gross_cash - costs
        return PayoffUnits(
            initial_risk_cash=g,
            reserve_cash=a,
            all_in_risk_cash=all_in,
            cost_cash=costs,
            gross_price_r=gross_price_r,
            net_price_r=net_cash / g,
            gross_cash=gross_cash,
            net_cash=net_cash,
            gross_parent_r=gross_cash / all_in,
            net_parent_r=net_cash / all_in,
        )


def solve_minimum_runner_price_r(
    *,
    initial_risk_cash: Decimal,
    reserve_cash: Decimal,
    closed_fills: Sequence[ExitFill],
    runner_fraction: Decimal,
    target_net_parent_r: Decimal,
    total_costs_cash: Decimal,
) -> RunnerRequirement:
    """Solve the minimum runner price-R for a planned net parent-R outcome.

    The runner is the unclosed part of the original quantity. The closed
    fills plus the runner fraction must sum to 1, and the runner fraction
    must be positive: a fully closed plan has no runner leg to solve and is
    rejected rather than answered with an infinity.

    The returned price-R is the algebraic threshold at which the planned
    outcome holds under the stated cost scenario. It is not a feasibility
    certificate and not a guarantee that the market reaches it.
    """
    g = _positive("initial_risk_cash", initial_risk_cash)
    a = _non_negative("reserve_cash", reserve_cash)
    costs = _non_negative("total_costs_cash", total_costs_cash)
    target = _decimal("target_net_parent_r", target_net_parent_r)
    runner = _fraction("runner_fraction", runner_fraction)
    if runner <= 0:
        raise ContractError(
            "LOT_SPLIT_INVALID",
            "solve_minimum_runner_price_r: the runner fraction must be positive; a fully "
            "closed plan has no runner leg to solve",
        )
    with localcontext(_ARITHMETIC):
        closed_fraction, closed_gross = _closed_fractions(closed_fills, "closed_fills")
        if closed_fraction + runner != 1:
            raise ContractError(
                "LOT_SPLIT_INVALID",
                "solve_minimum_runner_price_r: closed fills plus the runner fraction must "
                "sum to exactly 1",
            )
        all_in = g + a
        cost_ratio = costs / g
        required_net_price_r = target * all_in / g
        required_gross_price_r = required_net_price_r + cost_ratio
        runner_price_r = (required_gross_price_r - closed_gross) / runner
        return RunnerRequirement(
            runner_price_r=runner_price_r,
            runner_fraction=runner,
            target_net_parent_r=target,
            required_net_price_r=required_net_price_r,
            required_gross_price_r=required_gross_price_r,
            closed_gross_price_r=closed_gross,
            initial_risk_cash=g,
            reserve_cash=a,
            all_in_risk_cash=all_in,
            cost_cash=costs,
        )
