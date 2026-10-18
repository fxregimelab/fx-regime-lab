"""Strict semantic broker read records. No credentials, writes or transport fallback."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Protocol

from src.paper.clock import ClockProfile, digest, finite
from src.paper.contracts import ContractError

SYMBOLS = {"EURUSD": "EURUSDm", "USDJPY": "USDJPYm"}
TIMEFRAMES = {"M15": 900, "H1": 3600, "H4": 14400, "D1": 86400}


def require_symbol(pair: str, symbol: str) -> None:
    if pair not in SYMBOLS or SYMBOLS[pair] != symbol:
        raise ContractError("UNSUPPORTED_PAIR", "exact protected broker symbol required")


def require_numbers(record: object, names: tuple[str, ...], positive: bool = False) -> None:
    for name in names:
        value = getattr(record, name)
        if not finite(value) or (positive and value <= 0):
            raise ContractError("INVALID_NUMBER", f"invalid {name}")


@dataclass(frozen=True)
class Account:
    account_fingerprint: str
    terminal_identity: str
    currency: str
    trade_mode: int
    margin_mode: int
    balance: float
    equity: float
    observed_at: float

    def __post_init__(self) -> None:
        # MT5 ACCOUNT_TRADE_MODE_DEMO=0, ACCOUNT_MARGIN_MODE_RETAIL_HEDGING=2.
        if type(self.trade_mode) is not int or self.trade_mode != 0:
            raise ContractError("NON_DEMO_ACCOUNT", "numeric DEMO trade mode required")
        if type(self.margin_mode) is not int or self.margin_mode != 2:
            raise ContractError("NETTING_UNSUPPORTED", "split children require hedging")
        if (not digest(self.account_fingerprint) or not self.terminal_identity.strip()
                or len(self.currency) != 3 or not self.currency.isupper()):
            raise ContractError("INVALID_SCHEMA", "account identity/currency missing")
        require_numbers(self, ("balance", "equity", "observed_at"))


@dataclass(frozen=True)
class Instrument:
    pair: str
    symbol: str
    digits: int
    point: float
    tick_size: float
    tick_value_profit: float
    tick_value_loss: float
    contract_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level: int
    freeze_level: int
    observed_at: float

    def __post_init__(self) -> None:
        require_symbol(self.pair, self.symbol)
        for name in ("digits", "stops_level", "freeze_level"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ContractError("INVALID_SCHEMA", f"missing or invalid {name}")
        require_numbers(self, ("point", "tick_size", "tick_value_profit", "tick_value_loss",
                              "contract_size", "volume_min", "volume_max", "volume_step"), True)
        require_numbers(self, ("observed_at",))
        if self.volume_min > self.volume_max or self.volume_step > self.volume_max:
            raise ContractError("INVALID_NUMBER", "inconsistent volume limits")


@dataclass(frozen=True)
class Tick:
    pair: str
    symbol: str
    bid: float
    ask: float
    time_epoch: float
    acquired_at: float

    def __post_init__(self) -> None:
        require_symbol(self.pair, self.symbol)
        require_numbers(self, ("bid", "ask"), True)
        require_numbers(self, ("time_epoch", "acquired_at"))
        if self.bid > self.ask:
            raise ContractError("INVALID_NUMBER", "crossed quote")

    def validate_at(self, now: float, clock: ClockProfile) -> None:
        clock.require_fresh(self.time_epoch, now, 2., "TICK_STALE")
        clock.require_fresh(self.acquired_at, now, 2., "TICK_STALE")


@dataclass(frozen=True)
class CompletedBar:
    pair: str
    symbol: str
    timeframe: str
    open_at: float
    close_at: float
    available_at: float
    acquired_at: float
    original_epoch: float
    clock_profile_id: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    spread: float

    def __post_init__(self) -> None:
        require_symbol(self.pair, self.symbol)
        require_numbers(self, ("open", "high", "low", "close"), True)
        require_numbers(self, ("open_at", "close_at", "available_at", "acquired_at",
                              "original_epoch", "volume", "spread"))
        if (self.timeframe not in TIMEFRAMES or self.volume < 0 or self.spread < 0
                or not self.low <= min(self.open, self.close) <= max(self.open, self.close)
                <= self.high or self.close_at - self.open_at != TIMEFRAMES[self.timeframe]
                or not self.open_at == self.original_epoch
                or not self.close_at <= self.available_at <= self.acquired_at):
            raise ContractError("BAR_INCOMPLETE", "invalid completed-bar geometry/provenance")

    def validate_at(self, now: float, clock: ClockProfile) -> None:
        if (self.clock_profile_id != clock.profile_id or self.close_at > now
                or self.available_at > now or self.acquired_at > now):
            raise ContractError("BAR_INCOMPLETE", "bar unavailable at decision cutoff")
        clock.to_utc_epoch(self.original_epoch, now)


@dataclass(frozen=True)
class BrokerItem:
    """Normalized position/order/deal with explicit ownership and monetary units."""

    ticket: int
    pair: str
    symbol: str
    side: str
    volume: float
    price: float
    stop_loss: float
    take_profit: float
    profit: float
    commission: float
    swap: float
    currency: str
    magic: int
    comment: str
    time_epoch: float

    def __post_init__(self) -> None:
        require_symbol(self.pair, self.symbol)
        require_numbers(self, ("volume", "price"), True)
        require_numbers(self, ("stop_loss", "take_profit", "profit", "commission",
                              "swap", "time_epoch"))
        if (type(self.ticket) is not int or self.ticket <= 0 or type(self.magic) is not int
                or self.side not in ("long", "short") or self.stop_loss < 0
                or self.take_profit < 0 or len(self.currency) != 3):
            raise ContractError("INVALID_SCHEMA", "invalid broker item")


@dataclass(frozen=True)
class BrokerItems:
    account_fingerprint: str
    observed_at: float
    items: tuple[BrokerItem, ...]

    def __post_init__(self) -> None:
        if (not digest(self.account_fingerprint) or not finite(self.observed_at)
                or type(self.items) is not tuple
                or any(type(item) is not BrokerItem for item in self.items)
                or len({item.ticket for item in self.items}) != len(self.items)):
            raise ContractError("INVALID_SCHEMA", "invalid broker reconciliation snapshot")


def validate_record(record: Account | Instrument | Tick | CompletedBar | BrokerItems) -> None:
    """Reconstruct frozen records to recheck even externally supplied instances."""
    type(record)(**{f.name: getattr(record, f.name) for f in fields(record)})


class BrokerReadPort(Protocol):
    def tick(self, pair: str) -> Tick: ...
    def instrument(self, pair: str) -> Instrument: ...
    def account(self) -> Account: ...
    def positions(self) -> BrokerItems: ...
    def orders(self) -> BrokerItems: ...
    def deals(self, start: float, end: float) -> BrokerItems: ...
    def bars(self, pair: str, timeframe: str, count: int) -> tuple[CompletedBar, ...]: ...
