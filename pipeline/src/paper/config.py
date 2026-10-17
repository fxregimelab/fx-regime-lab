"""Paper desk configuration (private personal tooling — never rendered publicly).

Trading subset: EURUSD + USDJPY only (owner decision 2026-10-17). The research
pipeline keeps its 3-pair lock; USDINR is never executed by the desk.

Governance: the desk operates under ``docs/DESK_TRADING_PLAYBOOK.md`` +
``docs/DESK_STRATEGY_FRAMEWORK.md``. Ledger receipts are stamped with
``FRAMEWORK_VERSION`` / ``PLAYBOOK_VERSION`` so every decision cites the spec
it was made under.

Risk model v2 (owner directive 2026-10-17, aggressive demo phase): risk ceilings
by open slot (5% / 4% / 3% / 3%), scaled DOWN by checklist grade, hard cap 15%
open risk at any point in time, daily max loss -10%. Weekly target +50% is a
tracked objective (reported actual-vs-target; never a guarantee). An asymmetric
operator score (losses punished heavier than wins reward; framework §8) gates
the autonomy envelope. All values are demo-scoped; any real-money phase
re-derives them from the graduation gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Governance versions --------------------------------------------------------

FRAMEWORK_VERSION = "1.1"
PLAYBOOK_VERSION = "0.3"

# --- Targets (owner-set; tracked objectives, never guarantees) ------------------

WEEKLY_TARGET_PCT = 0.50  # +50%/week tracked by the weekly scorecard (actual vs target)

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
    """Sizing reference for the paper account."""

    paper_equity: float = 10_000.0      # reporting base (currency-agnostic)
    max_leverage: float = 50.0          # notional cap (× equity), demo-aggressive;
                                        # sizing clips here, then re-checks effective risk
    default_stop_atr_mult: float = 1.2  # fallback stop when layer3 stop_level is None (ATR_H1)


@dataclass(frozen=True)
class CostConfig:
    """Round-trip cost excluding the separate slippage allowance (unmeasured defaults)."""

    round_trip_bps: dict[str, float] = field(
        default_factory=lambda: {"EURUSD": 1.0, "USDJPY": 1.2}
    )
    slippage_bps: float = 0.5


@dataclass(frozen=True)
class TradingLimits:
    """Guardrails for the autonomous demo phase (playbook §4 — mirror, never drift).

    Risk ceilings by open slot (first open 5%, second 4%, then 3% + 3% → max 15%
    open risk at any point in time). The checklist grade scales risk DOWN from the
    slot ceiling only (A+ 1.0, A 0.8, B+ 0.6, B 0.45); C never trades. Kill-switches
    are entry lockouts, not guaranteed realized-loss caps. Independent admission
    also reserves residual stop risk against remaining daily/weekly loss capacity.
    """

    slot_risk_ceilings: tuple[float, ...] = (0.05, 0.04, 0.03, 0.03)
    grade_multipliers: dict[str, float] = field(
        default_factory=lambda: {"A+": 1.0, "A": 0.8, "B+": 0.6, "B": 0.45}
    )
    min_effective_risk_pct: float = 0.01   # skip when grade-scaled risk falls below 1%
    max_concurrent_positions: int = 4
    max_positions_per_pair: int = 2
    max_same_usd_sign_tickets: int = 2    # correlated one-way USD load cap
    max_open_risk_pct: float = 0.15       # 15% of equity across all open trades (hard cap)
    max_new_trades_per_day: int = 5
    daily_stop_pct: float = 0.10          # -10% equity → no new trades for the day + report
    weekly_stop_pct: float = 0.25         # -25% equity → freeze + full review
    cooldown_after_stop_hours: int = 4    # same pair + direction after a stop-out
    partial_at_r: float = 1.0             # take 50% off at 1R
    partial_fraction: float = 0.5
    breakeven_buffer_pips: float = 1.5
    trail_atr_mult: float = 1.2           # chandelier trail on H1 ATR
    trail_buffer_atr: float = 0.15        # anti-liquidity-hunt buffer beyond structure
    early_cut_adverse_r: float = 0.5      # adverse excursion within early_cut_hours
    early_cut_hours: int = 2
    time_stop_hours: int = 4              # stalled-thesis cut if < time_stop_min_r
    time_stop_min_r: float = 0.2


@dataclass(frozen=True)
class AgentScoreConfig:
    """Operator score — asymmetric penalty/reward for the executing AI (framework §8).

    Each verified trade decision must record the operator id (model/agent). Settled outcomes
    and process violations move that operator's score. The score gates the
    autonomy envelope and can only TIGHTEN limits, never loosen them. Pure replay
    is in operator_score.py; automated settlement/ledger integration is pending.
    """

    start_score: float = 100.0
    win_points_per_r: float = 4.0          # reward per +1R settled
    win_points_cap_per_trade: float = 12.0
    loss_points_per_r: float = 6.0         # losses punished heavier than wins reward
    loss_points_floor_per_trade: float = -18.0
    violation_penalty: float = 20.0        # unreceipted checklist / widened stop / missed cut
    kill_switch_day_penalty: float = 15.0
    full_envelope_min: float = 85.0        # >= 85: full autonomy envelope
    reduced_envelope_min: float = 60.0     # 60-84: A/A+ only, slot ceilings x0.75
    reduced_mode_grades: tuple[str, ...] = ("A+", "A")
    reduced_mode_slot_mult: float = 0.75


RISK = RiskConfig()
COSTS = CostConfig()
LIMITS = TradingLimits()
AGENT_SCORE = AgentScoreConfig()
