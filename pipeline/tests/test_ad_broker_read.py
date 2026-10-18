"""Offline AD-T07 contract oracles; no terminal, network or order access."""

from dataclasses import replace
from typing import Any

import pytest

from src.paper.broker import (
    Account,
    BrokerItem,
    BrokerItems,
    BrokerReadPort,
    CompletedBar,
    Instrument,
    Tick,
)
from src.paper.broker_mcp import McpBrokerRead, ReadBinding
from src.paper.clock import ClockProfile, ClockSample, TimestampEvidence
from src.paper.contracts import ContractError


def profile() -> ClockProfile:
    evidence = TimestampEvidence("official MT5 contract fixture", "a" * 64,
                                 "utc_epoch_seconds")
    samples = tuple(ClockSample(t, t, t + 7200, 7200, .1, bar)
                    for t, bar in ((899.0, 0.0), (900.0, 900.0), (901.0, 900.0)))
    return ClockProfile.observe(samples, evidence, 900.0, 1200.0)


def account() -> Account:
    return Account("a" * 64, "terminal-fixture", "USD", 0, 2, 10000., 10000., 900.)


def instrument() -> Instrument:
    return Instrument("EURUSD", "EURUSDm", 5, .00001, .00001, 1., 1.,
                      100000., .01, 100., .01, 0, 0, 900.)


def test_clock_observed_close_and_no_double_offset_conversion() -> None:
    p = profile()
    assert p.to_utc_epoch(901., 902.) == 901.
    assert p.uncertainty_seconds == .1
    assert len(p.profile_id) == 64


@pytest.mark.parametrize("fault", ["few", "no_close", "offset", "uncertainty", "docs"])
def test_clock_fails_closed(fault: str) -> None:
    samples = [ClockSample(t, t, t + 7200, 7200, .1, bar)
               for t, bar in ((899., 0.), (900., 900.), (901., 900.))]
    evidence = TimestampEvidence("official fixture", "a" * 64, "utc_epoch_seconds")
    if fault == "few":
        samples = samples[:2]
    if fault == "no_close":
        samples = [replace(s, bar_open_epoch=0.) for s in samples]
    if fault == "offset":
        samples[-1] = replace(samples[-1], terminal_offset_seconds=3600)
    if fault == "uncertainty":
        samples[-1] = replace(samples[-1], uncertainty_seconds=2.)
    if fault == "docs":
        evidence = replace(evidence, content_sha256="")
    with pytest.raises(ContractError):
        ClockProfile.observe(tuple(samples), evidence, 900., 1200.)


@pytest.mark.parametrize("mode", [1, 2, "0", False])
def test_real_or_contest_account_rejected_despite_trial_name(mode: Any) -> None:
    with pytest.raises(ContractError):
        replace(account(), trade_mode=mode, terminal_identity="Trial server")


def test_hedging_required() -> None:
    with pytest.raises(ContractError, match="NETTING_UNSUPPORTED"):
        replace(account(), margin_mode=0)


def test_account_positive_and_read_only_surface() -> None:
    assert account().trade_mode == 0
    assert not hasattr(BrokerReadPort, "send_order")
    assert not hasattr(McpBrokerRead, "send_order")


@pytest.mark.parametrize("change", [{"symbol": "EURUSD"}, {"tick_value_loss": 0.},
    {"tick_size": float("nan")}, {"freeze_level": None}, {"stops_level": -1},
    {"volume_step": 0.}, {"volume_min": 101.}, {"digits": True}])
def test_instrument_rejects_unsafe_fields(change: dict[str, Any]) -> None:
    with pytest.raises(ContractError):
        replace(instrument(), **change)


def test_exact_both_pair_instruments() -> None:
    assert instrument().symbol == "EURUSDm"
    assert replace(instrument(), pair="USDJPY", symbol="USDJPYm", digits=3).pair == "USDJPY"


@pytest.mark.parametrize("stamp", [897., 902., float("nan")])
def test_stale_future_nonfinite_ticks(stamp: float) -> None:
    with pytest.raises(ContractError):
        Tick("EURUSD", "EURUSDm", 1.1, 1.2, stamp, 900.).validate_at(900., profile())


def test_tick_positive_then_frozen_feed_rejected() -> None:
    tick = Tick("EURUSD", "EURUSDm", 1.1, 1.2, 900., 900.)
    tick.validate_at(901., profile())
    with pytest.raises(ContractError, match="TICK_STALE"):
        tick.validate_at(903., profile())


def bar() -> CompletedBar:
    return CompletedBar("EURUSD", "EURUSDm", "M15", 0., 900., 900., 901.,
                        0., profile().profile_id, 1.1, 1.3, 1., 1.2, 20., 2.)


def test_completed_bar_cutoff_and_original_epoch() -> None:
    bar().validate_at(901., profile())
    with pytest.raises(ContractError, match="BAR_INCOMPLETE"):
        bar().validate_at(899., profile())
    with pytest.raises(ContractError):
        replace(bar(), original_epoch=7200.).validate_at(901., profile())


@pytest.mark.parametrize("change", [{"available_at": 902.}, {"low": 1.25},
    {"timeframe": "M5"}, {"volume": -1.}, {"clock_profile_id": "b" * 64}])
def test_completed_bar_rejects_bad_input(change: dict[str, Any]) -> None:
    with pytest.raises(ContractError):
        replace(bar(), **change).validate_at(901., profile())


def test_unregistered_transport_never_calls() -> None:
    def forbidden(name: str, args: dict[str, object]) -> object:
        pytest.fail("unregistered transport invoked")
    reader = McpBrokerRead(forbidden, {}, profile(), lambda: 901.)
    with pytest.raises(ContractError, match="SOURCE_INCOMPLETE"):
        reader.account()


def test_registered_fixture_transport_and_stale_state() -> None:
    calls: list[str] = []
    def invoke(name: str, args: dict[str, object]) -> object:
        calls.append(name)
        assert args == {}
        return account()
    binding = ReadBinding("fixture.account.read", "a" * 64, True,
                          lambda args: args, lambda raw: raw)
    reader = McpBrokerRead(invoke, {"account": binding}, profile(), lambda: 901.)
    assert reader.account() == account()
    assert calls == ["fixture.account.read"]
    reader = McpBrokerRead(invoke, {"account": binding}, profile(), lambda: 906.)
    with pytest.raises(ContractError, match="BROKER_STATE_STALE"):
        reader.account()


def test_registration_rejects_non_readonly_and_bad_decoded_shape() -> None:
    with pytest.raises(ContractError):
        ReadBinding("fixture.write", "a" * 64, False, lambda x: x, lambda x: x)
    binding = ReadBinding("fixture.read", "a" * 64, True, lambda x: x, lambda x: x)
    reader = McpBrokerRead(lambda n, a: {"trade_mode": 0}, {"account": binding},
                           profile(), lambda: 901.)
    with pytest.raises(ContractError, match="INVALID_SCHEMA"):
        reader.account()


def test_clock_profile_not_usable_before_final_observation_or_after_expiry() -> None:
    for now in (900., 1201.):
        with pytest.raises(ContractError, match="CLOCK_UNVERIFIED"):
            profile().to_utc_epoch(900., now)


def items() -> BrokerItems:
    item = BrokerItem(1, "EURUSD", "EURUSDm", "long", .01, 1.1, 1., 1.3,
                      0., -.1, 0., "USD", 123, "fixture-parent-A", 900.)
    return BrokerItems("a" * 64, 900., (item,))


def test_nonempty_all_semantic_methods_and_position_one_bars() -> None:
    response: dict[str, object] = {"tick": Tick("EURUSD", "EURUSDm", 1.1, 1.2, 900., 901.),
                                  "instrument": instrument(), "account": account(),
                                  "positions": items(), "orders": items(), "deals": items(),
                                  "bars": (bar(),)}
    args_seen: dict[str, dict[str, object]] = {}
    def invoke(name: str, args: dict[str, object]) -> object:
        args_seen[name] = args
        return response[name]
    bindings = {name: ReadBinding(name, "a" * 64, True, lambda x: x, lambda x: x)
                for name in response}
    reader: BrokerReadPort = McpBrokerRead(invoke, bindings, profile(), lambda: 901.)
    assert reader.tick("EURUSD").bid == 1.1
    assert reader.instrument("EURUSD").volume_step == .01
    assert reader.account().currency == "USD"
    assert len(reader.positions().items) == 1
    assert len(reader.orders().items) == 1
    assert len(reader.deals(0., 901.).items) == 1
    assert len(reader.bars("EURUSD", "M15", 1)) == 1
    assert args_seen["bars"]["start_position"] == 1


@pytest.mark.parametrize("rows", [(bar(), bar()), (), (replace(bar(), pair="USDJPY",
                                                           symbol="USDJPYm"),)])
def test_transport_rejects_duplicate_empty_or_cross_pair_bars(
    rows: tuple[CompletedBar, ...],
) -> None:
    binding = ReadBinding("fixture.bars", "a" * 64, True, lambda x: x, lambda x: x)
    reader = McpBrokerRead(lambda n, a: rows, {"bars": binding}, profile(), lambda: 901.)
    with pytest.raises(ContractError):
        reader.bars("EURUSD", "M15", 2)


def test_decode_error_and_transport_error_propagate_without_retry() -> None:
    attempts: list[str] = []
    def broken(name: str, args: dict[str, object]) -> object:
        attempts.append(name)
        raise TimeoutError("fixture-only error")
    binding = ReadBinding("fixture.account", "a" * 64, True, lambda x: x, lambda x: x)
    reader = McpBrokerRead(broken, {"account": binding}, profile(), lambda: 901.)
    with pytest.raises(TimeoutError):
        reader.account()
    assert attempts == ["fixture.account"]


def test_stale_reconciliation_and_bad_deal_interval() -> None:
    binding = ReadBinding("fixture.positions", "a" * 64, True, lambda x: x, lambda x: x)
    reader = McpBrokerRead(lambda n, a: items(), {"positions": binding},
                           profile(), lambda: 906.)
    with pytest.raises(ContractError, match="BROKER_STATE_STALE"):
        reader.positions()
    with pytest.raises(ContractError, match="INVALID_SCHEMA"):
        reader.deals(906., 907.)


@pytest.mark.parametrize("change", [{"ask": 1.}, {"bid": 0.}, {"bid": float("inf")},
                                    {"acquired_at": float("nan")}])
def test_bad_quote_fields(change: dict[str, Any]) -> None:
    with pytest.raises(ContractError):
        replace(Tick("EURUSD", "EURUSDm", 1.1, 1.2, 900., 901.), **change)


def test_broker_snapshot_duplicate_ticket_rejected() -> None:
    with pytest.raises(ContractError):
        replace(items(), items=items().items * 2)


def test_unexplained_completed_bar_gap_is_not_forward_filled() -> None:
    first = replace(bar(), open_at=0., original_epoch=0., close_at=900.,
                    available_at=900., acquired_at=901.)
    second = replace(bar(), open_at=1800., original_epoch=1800., close_at=2700.,
                     available_at=2700., acquired_at=2701.)
    clock = replace(profile(), valid_until=3000.)
    first = replace(first, clock_profile_id=clock.profile_id)
    second = replace(second, clock_profile_id=clock.profile_id)
    binding = ReadBinding("fixture.bars", "a" * 64, True, lambda x: x, lambda x: x)
    reader = McpBrokerRead(lambda n, a: (first, second), {"bars": binding},
                           clock, lambda: 2701.)
    with pytest.raises(ContractError, match="BAR_GAP"):
        reader.bars("EURUSD", "M15", 2)
    reader = McpBrokerRead(lambda n, a: (first, second), {"bars": binding},
                           clock, lambda: 2701.,
                           known_session_gap=lambda pair, start, end:
                           pair == "EURUSD" and start == 900. and end == 1800.)
    assert reader.bars("EURUSD", "M15", 2) == (first, second)


def test_registered_schema_encoder_failure_never_invokes_transport() -> None:
    def reject(args: dict[str, object]) -> dict[str, object]:
        raise ContractError("INVALID_SCHEMA", "fixture input schema rejection")
    def forbidden(name: str, args: dict[str, object]) -> object:
        pytest.fail("schema failure invoked transport")
    binding = ReadBinding("fixture.read", "a" * 64, True, reject, lambda x: x)
    reader = McpBrokerRead(forbidden, {"account": binding}, profile(), lambda: 901.)
    with pytest.raises(ContractError, match="INVALID_SCHEMA"):
        reader.account()
