"""Historical bar loading for offline backtests (research only, never execution).

Reads the CSVs written by the read-only MetaTrader5 dump or the yfinance
fallback, normalises them into spec-02 ``OHLCBar`` values, and enforces the
same completed-bar contract the live detectors rely on: a bar is only usable
at decisions ``t >= close_time``.

Nothing here places, modifies or closes orders. The module has no broker
import and no network access.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.paper.contracts import ContractError
from src.paper.features import OHLCBar, validate_bars

DEFAULT_DATA_DIR = Path(r"C:\Users\sakha\AppData\Local\Temp\opencode\desk_backtest")
PAIRS: tuple[str, ...] = ("EURUSD", "USDJPY")
TIMEFRAMES: tuple[str, ...] = ("d1", "h4", "h1", "m15")

_BAR_SECONDS = {"m15": 900, "h1": 3600, "h4": 14400, "d1": 86400}


@dataclass(frozen=True)
class BarSeries:
    """One pair/timeframe series with provenance for the report."""

    pair: str
    timeframe: str
    bars: tuple[OHLCBar, ...]
    source: str

    @property
    def first(self) -> datetime:
        return self.bars[0].timestamp

    @property
    def last(self) -> datetime:
        return self.bars[-1].timestamp

    def __len__(self) -> int:
        return len(self.bars)


def _parse_time(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ContractError("INVALID_SCHEMA", f"naive timestamp in backtest CSV: {value!r}")
    return parsed


def _mt5_paths(data_dir: Path, pair: str, timeframe: str) -> list[Path]:
    return [
        data_dir / f"{pair}_{timeframe}_mt5.csv",
        data_dir / f"{pair}_{timeframe}.csv",
    ]


def load_series(
    pair: str, timeframe: str, *, data_dir: Path = DEFAULT_DATA_DIR
) -> BarSeries:
    """Load one series, preferring the MT5 dump (close_time is explicit)."""
    if pair not in PAIRS:
        raise ContractError("INVALID_SCHEMA", f"unsupported pair {pair!r}")
    if timeframe not in TIMEFRAMES:
        raise ContractError("INVALID_SCHEMA", f"unsupported timeframe {timeframe!r}")
    path = next((p for p in _mt5_paths(data_dir, pair, timeframe) if p.exists()), None)
    if path is None:
        raise ContractError(
            "INSUFFICIENT_DATA", f"no backtest CSV for {pair} {timeframe} in {data_dir}"
        )

    bars: list[OHLCBar] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ContractError("INVALID_SCHEMA", f"{path.name}: empty CSV")
        has_close_time = "close_time" in reader.fieldnames
        for row in reader:
            close_time = row["close_time"] if has_close_time else row["timestamp"]
            bars.append(
                OHLCBar(
                    timestamp=_parse_time(close_time),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("tick_volume") or row.get("volume") or 0.0),
                )
            )
    bars.sort(key=lambda b: b.timestamp)
    _drop_incomplete_tail(bars, timeframe)
    validate_bars(bars)
    return BarSeries(pair=pair, timeframe=timeframe, bars=tuple(bars), source=path.name)


def _drop_incomplete_tail(bars: list[OHLCBar], timeframe: str) -> None:
    """Remove the last bar when it cannot have closed yet (MT5 includes it)."""
    if not bars:
        return
    now = datetime.now(tz=bars[-1].timestamp.tzinfo)
    if bars[-1].timestamp > now:
        bars.pop()


def load_pair(pair: str, *, data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, BarSeries]:
    """All four timeframes for one pair, trimmed to their common overlap."""
    return {tf: load_series(pair, tf, data_dir=data_dir) for tf in TIMEFRAMES}


def load_bundle(*, data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, dict[str, BarSeries]]:
    return {pair: load_pair(pair, data_dir=data_dir) for pair in PAIRS}


def slice_between(
    series: BarSeries, start: datetime, end: datetime
) -> tuple[OHLCBar, ...]:
    return tuple(b for b in series.bars if start <= b.timestamp <= end)


def expected_step(timeframe: str) -> timedelta:
    return timedelta(seconds=_BAR_SECONDS[timeframe])


def coverage_summary(bundle: dict[str, dict[str, BarSeries]]) -> list[dict[str, Any]]:
    """Rows for the report: bars, span and source per pair/timeframe."""
    rows: list[dict[str, Any]] = []
    for pair, frames in bundle.items():
        for timeframe, series in frames.items():
            rows.append(
                {
                    "pair": pair,
                    "timeframe": timeframe,
                    "bars": len(series),
                    "first": series.first.isoformat(),
                    "last": series.last.isoformat(),
                    "days": round((series.last - series.first).total_seconds() / 86400.0, 1),
                    "source": series.source,
                }
            )
    return rows
