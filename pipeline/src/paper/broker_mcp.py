"""Injected MCP read transport; no installed schema is assumed or bundled.

Local .mcp.json has HTTP terminal/editor bridges, not tool schemas. AD-T07
therefore requires explicit reviewed bindings to archived tools/list schemas.
Binding encoders validate actual input schemas; decoders validate actual output
schemas and normalize to broker records. Fixture bindings are NOT live proof.
No network client, terminal login, credentials or direct-Python fallback lives here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from src.paper.broker import (
    SYMBOLS,
    TIMEFRAMES,
    Account,
    BrokerItems,
    CompletedBar,
    Instrument,
    Tick,
    validate_record,
)
from src.paper.clock import ClockProfile, digest, finite
from src.paper.contracts import ContractError

R = TypeVar("R", Account, Instrument, Tick, BrokerItems)


@dataclass(frozen=True)
class ReadBinding:
    tool_name: str
    schema_sha256: str
    read_only: bool
    encode: Callable[[dict[str, object]], dict[str, object]]
    decode: Callable[[object], object]

    def __post_init__(self) -> None:
        if (not self.tool_name.strip() or not digest(self.schema_sha256)
                or self.read_only is not True or not callable(self.encode)
                or not callable(self.decode)):
            raise ContractError("INVALID_SCHEMA", "reviewed read-only schema binding required")


class McpBrokerRead:
    def __init__(self, invoke: Callable[[str, dict[str, object]], object],
                 bindings: Mapping[str, ReadBinding], clock: ClockProfile,
                 now: Callable[[], float],
                 known_session_gap: Callable[[str, float, float], bool] | None = None) -> None:
        allowed = {"tick", "instrument", "account", "positions", "orders", "deals", "bars"}
        if set(bindings) - allowed:
            raise ContractError("INVALID_SCHEMA", "non-read semantic operation")
        self._invoke = invoke
        self._bindings = dict(bindings)
        self._clock = clock
        self._now = now
        # Only an independently verified broker session calendar may explain gaps.
        self._known_session_gap = known_session_gap

    def _read(self, operation: str, arguments: dict[str, object]) -> object:
        binding = self._bindings.get(operation)
        if binding is None:
            raise ContractError("SOURCE_INCOMPLETE", "no discovered schema registered")
        self._clock.to_utc_epoch(self._now(), self._now())
        # Intentionally no retries, fallback or exception text containing raw broker data.
        return binding.decode(self._invoke(binding.tool_name, binding.encode(arguments)))

    def _record(self, operation: str, arguments: dict[str, object], kind: type[R]) -> R:
        result = self._read(operation, arguments)
        if not isinstance(result, kind) or type(result) is not kind:
            raise ContractError("INVALID_SCHEMA", "decoded broker record has wrong type")
        validate_record(result)
        if isinstance(result, Tick):
            result.validate_at(self._now(), self._clock)
        else:
            self._clock.require_fresh(result.observed_at, self._now(), 5., "BROKER_STATE_STALE")
        return result

    def _symbol(self, pair: str) -> str:
        if pair not in SYMBOLS:
            raise ContractError("UNSUPPORTED_PAIR", "pair outside execution subset")
        return SYMBOLS[pair]

    def tick(self, pair: str) -> Tick:
        result = self._record("tick", {"symbol": self._symbol(pair)}, Tick)
        if result.pair != pair:
            raise ContractError("INVALID_SCHEMA", "tick pair mismatch")
        return result

    def instrument(self, pair: str) -> Instrument:
        result = self._record("instrument", {"symbol": self._symbol(pair)}, Instrument)
        if result.pair != pair:
            raise ContractError("INVALID_SCHEMA", "instrument pair mismatch")
        return result

    def account(self) -> Account:
        return self._record("account", {}, Account)

    def positions(self) -> BrokerItems:
        return self._record("positions", {}, BrokerItems)

    def orders(self) -> BrokerItems:
        return self._record("orders", {}, BrokerItems)

    def deals(self, start: float, end: float) -> BrokerItems:
        now = self._now()
        if not finite(start) or not finite(end) or not 0 <= start <= end <= now:
            raise ContractError("INVALID_SCHEMA", "invalid deals interval")
        return self._record("deals", {"start": start, "end": end}, BrokerItems)

    def bars(self, pair: str, timeframe: str, count: int) -> tuple[CompletedBar, ...]:
        if timeframe not in TIMEFRAMES or type(count) is not int or not 1 <= count <= 260:
            raise ContractError("INVALID_SCHEMA", "invalid bounded bar request")
        result = self._read("bars", {"symbol": self._symbol(pair), "timeframe": timeframe,
                                     "start_position": 1, "count": count})
        if type(result) is not tuple or not result or len(result) > count:
            raise ContractError("INVALID_SCHEMA", "nonempty completed-bar tuple required")
        bars: list[CompletedBar] = []
        previous = -1.
        for bar in result:
            if type(bar) is not CompletedBar:
                raise ContractError("INVALID_SCHEMA", "invalid bar type")
            validate_record(bar)
            bar.validate_at(self._now(), self._clock)
            if bar.pair != pair or bar.timeframe != timeframe or bar.open_at <= previous:
                raise ContractError("BAR_INCOMPLETE", "wrong or unordered bars")
            if bars and bars[-1].close_at != bar.open_at:
                if (bars[-1].close_at > bar.open_at or self._known_session_gap is None
                        or self._known_session_gap(pair, bars[-1].close_at, bar.open_at)
                        is not True):
                    raise ContractError("BAR_GAP", "unexplained completed-bar interval")
            bars.append(bar)
            previous = bar.open_at
        return tuple(bars)
