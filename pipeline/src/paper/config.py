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

# Hard horizon cap T+5 (owner directive 2026-10-17). Intraday preference — most trades
# targeting ≤8h closes — is enforced by the management policy, not by this tuple.
# See docs/DESK_TRADING_PLAYBOOK.md.
HORIZONS: tuple[int, ...] = (1, 2, 3, 4, 5)
DEFAULT_HORIZON = 5  # outer bound for swing holds (matches validation T+5)


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


@dataclass(frozen=True)
class TradingLimits:
    """Guardrails for the autonomous demo phase (playbook §4 — mirror, never drift).

    The owner removed the per-trade approval gate for the demo phase (2026-10-17);
    these limits plus the kill-switches and full receipts are the control surface.
    Grade-based sizing: A = full, B = half; the 1% owner cap is never a default.
    """

    risk_pct_by_grade: dict[str, float] = field(
        default_factory=lambda: {"A": 0.0075, "B": 0.0050}
    )
    max_concurrent_positions: int = 3
    max_positions_per_pair: int = 1
    max_open_risk_pct: float = 0.0225   # 2.25% of equity across all open trades
    max_new_trades_per_day: int = 3
    daily_stop_pct: float = 0.030       # -3% equity → stop for the day + report
    weekly_stop_pct: float = 0.060      # -6% equity → freeze + review
    cooldown_after_stop_hours: int = 4  # same pair + direction after a stop-out
    partial_at_r: float = 1.0           # take 50% off at 1R
    partial_fraction: float = 0.5
    breakeven_buffer_pips: float = 1.5
    trail_atr_mult: float = 1.2         # chandelier trail on H1 ATR
    trail_buffer_atr: float = 0.15      # anti-liquidity-hunt buffer beyond structure
    early_cut_adverse_r: float = 0.5    # adverse excursion within early_cut_hours
    early_cut_hours: int = 2
    time_stop_hours: int = 4            # stalled-thesis cut if < time_stop_min_r
    time_stop_min_r: float = 0.2


RISK = RiskConfig()
COSTS = CostConfig()
LIMITS = TradingLimits()
