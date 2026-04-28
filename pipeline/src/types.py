"""Shared pipeline types and pair configuration."""

from dataclasses import dataclass
from datetime import date

PAIRS: list[str] = ["EURUSD", "USDJPY", "USDINR"]
YF_TICKERS: dict[str, str] = {
    "EURUSD": "EURUSD=X",
    "USDJPY": "USDJPY=X",
    "USDINR": "USDINR=X",
}


@dataclass
class RawYields:
    date: date
    us_2y: float
    de_2y: float | None
    jp_2y: float | None
    in_2y: float | None
    us_10y: float | None = None
    de_10y: float | None = None
    jp_10y: float | None = None
    in_10y: float | None = None


@dataclass
class SpotBar:
    date: date
    pair: str
    open: float
    high: float
    low: float
    close: float


@dataclass
class CotRow:
    date: date
    pair: str
    net_long: int
    open_interest: int


@dataclass
class SignalRow:
    pair: str
    date: date
    rate_diff_2y: float | None
    rate_diff_10y: float | None
    cot_percentile: float | None
    realized_vol_20d: float | None
    realized_vol_5d: float | None
    implied_vol_30d: float | None
    spot: float | None
    day_change: float | None
    day_change_pct: float | None
    cross_asset_vix: float | None
    cross_asset_dxy: float | None
    cross_asset_oil: float | None


@dataclass
class RegimeCall:
    pair: str
    date: date
    regime: str
    confidence: float
    signal_composite: float
    rate_signal: str
    primary_driver: str | None = None
