"""Shared pipeline types and pair configuration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, Required, TypedDict, cast

logger = logging.getLogger(__name__)

_universe_cache: dict[str, Any] | None = None


def normalize_fx_pair_key(pair: str | None) -> str | None:
    """Normalize universe FX keys (e.g. ``EUR/USD`` → ``EURUSD``)."""

    if pair is None:
        return None
    cleaned = str(pair).upper().replace("/", "").strip()
    return cleaned or None


@dataclass(frozen=True)
class PairWeightConfig:
    """Composite blend weights for a pair (must sum to 1.0 for full participation)."""

    rate: float
    cot: float
    vol: float
    oi: float
    special: float


def _universe_rows_to_dict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in rows:
        pair = str(row.get("pair") or "")
        if not pair:
            continue
        cls = str(row.get("class") or "FX")
        # spot_ticker: Yahoo-style symbol for yfinance fallback (e.g. EURUSD=X).
        # Alpha Vantage FX_DAILY uses ISO legs derived from the pair key via
        # ``alphavantage_fx_legs_from_pair`` (e.g. EURUSD → from EUR, to USD).
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


def alphavantage_fx_legs_from_pair(pair: str) -> tuple[str, str]:
    """Map universe FX pair key to Alpha Vantage ``FX_DAILY`` legs (from, to).

    Expects a 6-character BASEQUOTE key (e.g. ``EURUSD``, ``USDJPY``), not a
    Yahoo suffix ticker like ``EURUSD=X``.
    """

    p = pair.upper().replace("/", "").strip()
    if len(p) != 6:
        raise ValueError(f"Alpha Vantage FX legs need a 6-char pair key, got {pair!r}")
    return p[:3], p[3:6]


def spot_tickers_from_universe() -> dict[str, str]:
    """Yahoo spot symbols keyed by pair (from loaded universe; yfinance fallback)."""

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
    volume: float = 0.0


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
    volume_rvol: float | None = None
    structural_instability: bool = False
    breakeven_inflation_10y: float | None = None
    rate_diff_10y_real: float | None = None
    rate_z_tactical: float | None = None
    rate_z_structural: float | None = None
    realized_vol_rank: float | None = None
    skew_alignment: int | None = None

    @property
    def breakeven_inflation(self) -> float | None:
        """FRED T10YIE (10Y breakeven inflation, %); alias of ``breakeven_inflation_10y``."""

        return self.breakeven_inflation_10y


class Layer1GateOutput(TypedDict):
    """Deterministic Layer 1 state vector (Marcus gate + hysteresis-adjusted label)."""

    regime: Required[str]
    invalidated: Required[bool]
    z_rate: Required[float | None]
    m_rate: Required[float | None]
    delta_pi: Required[float | None]
    d_spot: Required[float | None]
    stale_fields: Required[list[str]]
    raw_regime: Required[str]


Layer2DirectionalBias = Literal["LONG", "SHORT", "NEUTRAL"]


class Layer2DirectionalOutput(TypedDict):
    """Layer 2 conviction + directional bias (COT percentile, crowding, Marcus B clash veto)."""

    positioning_percentile: Required[float | None]
    crowd_flag: Required[bool]
    crowd_penalty: Required[float]
    crowd_veto: Required[bool]
    conviction_multiplier: Required[float]
    conviction: Required[int]
    directional_bias: Required[Layer2DirectionalBias]
    rate_positioning_clash: Required[bool]


Layer3EntryTiming = Literal["ENTER", "WAIT"]
Layer3PositionSize = Literal["FULL", "HALF"]


class Layer3ExecutionOutput(TypedDict):
    """Layer 3 execution HUD: timing, sizing, stop, and skew/vol diagnostics."""

    entry_timing: Required[Layer3EntryTiming]
    position_size: Required[Layer3PositionSize]
    stop_level: Required[float | None]
    realized_vol_rank: Required[float | None]
    skew_alignment: Required[int]
    skew_reversal_flag: Required[bool]
    risk_reversal_z: Required[float | None]
    adr: Required[float | None]
    mie_proxy: Required[float | None]
    stop_buffer: Required[float | None]


@dataclass(frozen=True)
class Layer1ClassifierContext:
    """Inputs for ``run_layer1_gate`` (Chamber 1). Series are oldest → newest."""

    pair: str
    composite: float
    vol_expanding: bool
    structural_instability: bool
    prior_regime_label: str | None
    carry_risk_adjusted_chronological: tuple[float, ...]
    spot_closes_chronological: tuple[float, ...]
    breakeven_inflation_chronological: tuple[float, ...] | None
    rate_diff_2y: float | None
    realized_vol_20d: float | None


@dataclass
class RegimeCall:
    pair: str
    date: date
    regime: str
    confidence: float
    signal_composite: float
    rate_signal: str
    primary_driver: str | None = None
    entry_timing: Layer3EntryTiming | None = None
    position_size: Layer3PositionSize | None = None
    stop_level: float | None = None
    data_quality_score: float | None = None
    stress_level: str | None = None
    # Layer 2 outputs (persisted for validation transparency)
    predicted_direction: str | None = None  # BULLISH / BEARISH / NEUTRAL (Layer2 bias)
    directional_bias: str | None = None  # LONG / SHORT / NEUTRAL
    conviction: int | None = None
    # Signal family snapshots (for audit / explainability)
    cot_signal: str | None = None
    vol_signal: str | None = None
    oi_signal: str | None = None


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
