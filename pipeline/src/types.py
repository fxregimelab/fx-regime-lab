"""Shared pipeline types and pair configuration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)

_universe_cache: dict[str, Any] | None = None


def _universe_rows_to_dict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in rows:
        pair = str(row.get("pair") or "")
        if not pair:
            continue
        cls = str(row.get("class") or "FX")
        out[pair] = {
            "class": cls,
            "tickers": {
                "spot_ticker": row.get("spot_ticker"),
                "yield_base": row.get("yield_base"),
                "yield_quote": row.get("yield_quote"),
                "cot_ticker": row.get("cot_ticker"),
            },
        }
    return out


def _load_universe_from_json() -> dict[str, Any]:
    path = Path(__file__).resolve().parent.parent / "universe.json"
    if not path.is_file():
        raise FileNotFoundError(f"universe.json not found at {path}")
    with path.open(encoding="utf-8") as fh:
        raw: Any = json.load(fh)
        if not isinstance(raw, dict):
            raise ValueError("universe.json must be a JSON object")
        return cast(dict[str, Any], raw)


def load_universe(*, force_refresh: bool = False) -> dict[str, Any]:
    """Load instrument registry from Supabase ``universe`` table; cache for the process run.

    Falls back to ``pipeline/universe.json`` only if the table is unreachable or empty
    (local/tests).
    """

    global _universe_cache
    if _universe_cache is not None and not force_refresh:
        return _universe_cache

    rows: list[dict[str, Any]] = []
    try:
        from src.db import writer

        rows = writer.fetch_universe_registry()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Universe table read failed (%s); falling back to universe.json", exc)

    if rows:
        _universe_cache = _universe_rows_to_dict(rows)
    else:
        logger.warning("Universe table empty; using pipeline/universe.json")
        _universe_cache = _load_universe_from_json()

    _sync_pairs()
    return _universe_cache


def pairs_from_universe(*, asset_class: str = "FX") -> list[str]:
    """Ordered list of instrument keys from the universe (filtered by ``class``)."""

    u = load_universe()
    return [
        k
        for k, meta in u.items()
        if isinstance(meta, dict) and meta.get("class") == asset_class
    ]


PAIRS: list[str] = []


def _sync_pairs() -> None:
    global PAIRS
    PAIRS[:] = pairs_from_universe(asset_class="FX")


def spot_tickers_from_universe() -> dict[str, str]:
    """Yahoo spot symbols keyed by pair (from loaded universe)."""

    out: dict[str, str] = {}
    for sym, meta in load_universe().items():
        if not isinstance(meta, dict) or meta.get("class") != "FX":
            continue
        tickers = meta.get("tickers")
        raw: dict[str, Any] = tickers if isinstance(tickers, dict) else {}
        st_raw = raw.get("spot_ticker")
        spot = st_raw if isinstance(st_raw, str) else raw.get("spot")
        if isinstance(spot, str):
            out[sym] = spot
    return out


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
    cross_asset_us10y: float | None
    cross_asset_gold: float | None
    cross_asset_copper: float | None
    cross_asset_stoxx: float | None
    oi_delta: int | None
    structural_instability: bool = False
    breakeven_inflation_10y: float | None = None
    rate_diff_10y_real: float | None = None
    rate_z_tactical: float | None = None
    rate_z_structural: float | None = None

    @property
    def breakeven_inflation(self) -> float | None:
        """FRED T10YIE (10Y breakeven inflation, %); alias of ``breakeven_inflation_10y``."""

        return self.breakeven_inflation_10y


@dataclass
class RegimeCall:
    pair: str
    date: date
    regime: str
    confidence: float
    signal_composite: float
    rate_signal: str
    primary_driver: str | None = None


@dataclass
class StrategyLedgerRow:
    """Alpha ledger row: regime + primary driver directional edge tracking (forward-walked MTM)."""

    date: date
    pair: str
    regime: str
    primary_driver: str
    direction: str
    entry_close: float | None = None
    confidence: float | None = None
    t1_close: float | None = None
    t3_close: float | None = None
    t5_close: float | None = None
    t1_hit: int | None = None
    t3_hit: int | None = None
    t5_hit: int | None = None
    brier_score_t5: float | None = None


@dataclass
class DeskOpenCardRow:
    date: date
    pair: str
    structural_regime: str
    dominance_array: list[dict[str, Any]]
    pain_index: float | None
    markov_probabilities: dict[str, Any]
    ai_brief: str
    telemetry_audit: dict[str, Any]
    invalidation_triggered: bool = False
    telemetry_status: str = "ONLINE"
    global_rank: int | None = None
    apex_score: float | None = None
    regime_age: int | None = None
