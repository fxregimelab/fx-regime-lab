"""Bar service for the personal paper desk: broker (MetaTrader 5) daily bars
into the local desk store, with sanity bounds and quarantine.

Trading subset: EURUSD + USDJPY only. This module never places, modifies, or
closes orders - market data only. Credentials come from repo-root ``.env.local``
and are never printed. The MetaTrader5 package is imported lazily so the test
suite runs without a terminal present.

Pieces:
- ``validate_bars`` - pure OHLC sanity + close-to-close jump quarantine.
- ``sync_bars`` - validate + upsert into ``DeskStore``; returns a report.
- ``Mt5BarFeed`` - thin read-only wrapper over the MetaTrader5 package.
"""

from __future__ import annotations

import math
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.paper.store import Bar, DeskStore

_REPO_ROOT = Path(__file__).resolve().parents[3]

PAIRS: tuple[str, ...] = ("EURUSD", "USDJPY")
SUFFIX_CANDIDATES: tuple[str, ...] = ("", "m", ".", "#", "pro", "raw", "ecn", "z")

MAX_DAY_MOVE_FRAC = 0.10  # quarantine bound for close-to-close jumps
DEFAULT_TIMEFRAME = "D1"
MAX_BARS = 20_000  # plenty for D1 since 2018; broker returns what exists


@dataclass(frozen=True)
class Mt5Env:
    login: str
    password: str
    server: str
    terminal_path: str
    portable: bool


def load_mt5_env(env_path: Path | None = None) -> Mt5Env:
    """Build the terminal connection config from shell env + ``.env.local``.

    Shell env wins over the file. Values are never printed.
    """
    values: dict[str, str] = {}
    path = env_path if env_path is not None else _REPO_ROOT / ".env.local"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            values[name.strip()] = value.strip().strip('"').strip("'")

    def pick(name: str) -> str:
        return os.environ.get(name) or values.get(name, "")

    return Mt5Env(
        login=pick("MT5_LOGIN"),
        password=pick("MT5_PASSWORD"),
        server=pick("MT5_SERVER"),
        terminal_path=pick("MT5_TERMINAL"),
        portable=pick("MT5_PORTABLE") == "1",
    )


@dataclass
class BarValidation:
    clean: list[Bar] = field(default_factory=list)
    quarantined: list[tuple[Bar, str]] = field(default_factory=list)


def _bar_reject_reason(bar: Bar) -> str | None:
    prices = {"open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close}
    for name, value in prices.items():
        if not math.isfinite(value) or value <= 0:
            return f"bad_{name}={value!r}"
    if bar.high < max(bar.open, bar.close):
        return "high_below_body"
    if bar.low > min(bar.open, bar.close):
        return "low_above_body"
    if bar.high < bar.low:
        return "high_below_low"
    return None


def validate_bars(
    bars: Iterable[Bar],
    max_day_move_frac: float = MAX_DAY_MOVE_FRAC,
) -> BarValidation:
    """Sanity-check bars; returns clean bars (sorted, deduped) + quarantine list.

    Rules: OHLC consistency, positive finite prices, and no close-to-close jump
    larger than ``max_day_move_frac`` (jumps measured against the last clean
    bar). Duplicate timestamps keep the later bar.
    """
    out = BarValidation()
    by_time: dict[int, Bar] = {}
    for bar in bars:
        reason = _bar_reject_reason(bar)
        if reason is not None:
            out.quarantined.append((bar, reason))
            continue
        by_time[bar.time_srv] = bar

    prev: Bar | None = None
    for time_srv in sorted(by_time):
        bar = by_time[time_srv]
        if prev is not None:
            move = abs(bar.close - prev.close) / prev.close
            if move > max_day_move_frac:
                out.quarantined.append(
                    (bar, f"day_move {move:.2%} > {max_day_move_frac:.0%}")
                )
                continue
        out.clean.append(bar)
        prev = bar
    return out


@dataclass(frozen=True)
class SyncReport:
    pair: str
    symbol: str
    timeframe: str
    fetched: int
    stored: int
    quarantined: tuple[tuple[int, str], ...]  # (time_srv, reason)


def sync_bars(
    store: DeskStore,
    pair: str,
    symbol: str,
    bars: Sequence[Bar],
    timeframe: str = DEFAULT_TIMEFRAME,
) -> SyncReport:
    """Validate fetched bars and upsert the clean ones into the store."""
    result = validate_bars(bars)
    stored = store.upsert_bars(result.clean)
    return SyncReport(
        pair=pair,
        symbol=symbol,
        timeframe=timeframe,
        fetched=len(bars),
        stored=stored,
        quarantined=tuple((bar.time_srv, reason) for bar, reason in result.quarantined),
    )


class Mt5BarFeed:
    """Read-only wrapper over the MetaTrader5 package (lazy import).

    ``initialize`` may start a hidden helper terminal instance; call
    ``shutdown()`` (or use the context manager) when done.
    """

    def __init__(self, env: Mt5Env) -> None:
        self._env = env
        self._mt5: Any = None

    def __enter__(self) -> Mt5BarFeed:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        self.shutdown()

    def connect(self) -> None:
        import MetaTrader5 as mt5  # noqa: N813  # package name is CamelCase

        kwargs: dict[str, Any] = {"timeout": 120_000, "portable": self._env.portable}
        if self._env.terminal_path:
            kwargs["path"] = self._env.terminal_path
        if self._env.login and self._env.password and self._env.server:
            kwargs.update(
                login=int(self._env.login),
                password=self._env.password,
                server=self._env.server,
            )
        if not mt5.initialize(**kwargs):
            raise RuntimeError(f"MetaTrader5 initialize failed: {mt5.last_error()}")
        self._mt5 = mt5

    def shutdown(self) -> None:
        if self._mt5 is not None:
            self._mt5.shutdown()
            self._mt5 = None

    def resolve_symbol(self, pair: str) -> str | None:
        assert self._mt5 is not None
        for suffix in SUFFIX_CANDIDATES:
            candidate = f"{pair}{suffix}"
            if self._mt5.symbol_info(candidate) is not None:
                return candidate
        return None

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str = DEFAULT_TIMEFRAME,
        count: int = MAX_BARS,
    ) -> list[Bar]:
        assert self._mt5 is not None
        tf = getattr(self._mt5, f"TIMEFRAME_{timeframe}")
        self._mt5.symbol_select(symbol, True)
        rates = self._mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            raise RuntimeError(
                f"copy_rates_from_pos({symbol}, {timeframe}) failed: {self._mt5.last_error()}"
            )
        return [
            Bar(
                symbol=symbol,
                timeframe=timeframe,
                time_srv=int(r["time"]),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                tick_volume=int(r["tick_volume"]),
                spread_points=int(r["spread"]),
            )
            for r in rates
        ]
