"""Paper desk configuration (private personal tooling — never rendered publicly).

Trading subset: EURUSD + USDJPY only (owner decision 2026-10-17). The research
pipeline keeps its 3-pair lock; USDINR is never executed by the desk.

All values are conservative defaults for the paper phase and can be overridden
per run. Costs start conservative and are replaced by measured MT5 spreads once
the spread sampler has run (see `pipeline/scripts/desk_mt5_spike.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Universe ------------------------------------------------------------------

TRADING_PAIRS: tuple[str, ...] = ("EURUSD", "USDJPY")

# --- Live-data guards -----------------------------------------------------------

LIVE_MODEL_VERSION = "2.0-live"
LIVE_DATA_SOURCE = "live"  # the desk only ever *trades* on live-tagged calls

# --- Horizons (trading days) ----------------------------------------------------

HORIZONS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)
DEFAULT_HORIZON = 5  # house strategy horizon (matches validation T+5)


@dataclass(frozen=True)
class RiskConfig:
    """Risk-based sizing for the paper account."""

    paper_equity: float = 10_000.0      # reporting base (currency-agnostic)
    risk_pct: float = 0.0075            # 0.75% of equity at risk per trade
    max_leverage: float = 3.0           # notional cap vs equity
    default_stop_atr_mult: float = 2.0  # fallback stop when layer3 stop_level is None


@dataclass(frozen=True)
class CostConfig:
    """Conservative round-trip costs in bps (incl. slippage allowance)."""

    round_trip_bps: dict[str, float] = field(
        default_factory=lambda: {"EURUSD": 1.0, "USDJPY": 1.2}
    )
    slippage_bps: float = 0.5


RISK = RiskConfig()
COSTS = CostConfig()
