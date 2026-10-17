"""Deterministic accountability, not model training or evidence of trading edge.

Replay verified, chronologically ordered events for the entire desk. Model swaps
do not reset safety history. Settlement means BOTH child tickets closed: net R
includes commissions/swap/slippage, divided by immutable initial parent risk.
The ledger adapter and owner-remediation workflow are not implemented here.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from src.paper.config import AGENT_SCORE


@dataclass(frozen=True)
class ScoreEvent:
    event_id: str  # parent trade id for settlement; unique incident/day id otherwise
    operator_id: str
    kind: Literal["settlement", "violation", "daily_kill"]
    net_r: float | None = None
    probability: float | None = None  # recorded before outcome, for a fixed binary event
    outcome: bool | None = None


@dataclass(frozen=True)
class ScoreReport:
    score: float
    mode: Literal["full", "reduced", "paused"]
    slot_mult: float
    allowed_grades: tuple[str, ...]
    settled_trades: int
    net_r: float
    brier: float | None
    forecast_count: int
    review_required: bool


def replay_score(events: Sequence[ScoreEvent]) -> ScoreReport:
    """Replay once from genesis; never append the same outcome twice.

    Pause and process-breach restrictions latch for this history. Profitable
    trades cannot erase them. No auto-resume/retraining/parameter optimization.
    Empty history is untested, NOT evidence of skill or execution readiness.
    """
    score = AGENT_SCORE.start_score
    seen: set[str] = set()
    settled = 0
    net_r = 0.0
    losses: list[float] = []
    breached = False
    paused = False
    for event in events:
        if not event.event_id.strip() or not event.operator_id.strip():
            raise ValueError("Event and operator identities are required")
        if event.event_id in seen:
            raise ValueError("Duplicate score event; reconcile before replay")
        seen.add(event.event_id)
        if event.kind == "settlement":
            if event.net_r is None or not math.isfinite(event.net_r):
                raise ValueError("Settlement requires finite net R")
            if (event.probability is None) != (event.outcome is None):
                raise ValueError("Forecast probability and binary outcome must be paired")
            if event.probability is not None:
                if not math.isfinite(event.probability) or not 0 <= event.probability <= 1:
                    raise ValueError("Invalid forecast probability")
                if type(event.outcome) is not bool:
                    raise ValueError("Forecast outcome must be binary")
                losses.append((event.probability - float(event.outcome)) ** 2)
            settled += 1
            net_r += event.net_r
            if event.net_r > 0:
                delta = min(
                    AGENT_SCORE.win_points_cap_per_trade,
                    event.net_r * AGENT_SCORE.win_points_per_r,
                )
            else:
                delta = max(
                    AGENT_SCORE.loss_points_floor_per_trade,
                    event.net_r * AGENT_SCORE.loss_points_per_r,
                )
        elif event.kind in ("violation", "daily_kill"):
            if any(v is not None for v in (event.net_r, event.probability, event.outcome)):
                raise ValueError("Incident cannot carry settlement/forecast fields")
            breached = True
            delta = -(
                AGENT_SCORE.violation_penalty if event.kind == "violation"
                else AGENT_SCORE.kill_switch_day_penalty
            )
        else:
            raise ValueError("Unknown score event kind")
        score = min(100.0, max(0.0, score + delta))
        paused = paused or score < AGENT_SCORE.reduced_envelope_min

    mode: Literal["full", "reduced", "paused"] = "full"
    mult = 1.0
    grades: tuple[str, ...] = ("A+", "A", "B+", "B")
    if paused:
        mode, mult, grades = "paused", 0.0, ()
    elif breached or score < AGENT_SCORE.full_envelope_min:
        mode = "reduced"
        mult = AGENT_SCORE.reduced_mode_slot_mult
        grades = AGENT_SCORE.reduced_mode_grades
    return ScoreReport(
        score=score, mode=mode, slot_mult=mult, allowed_grades=grades,
        settled_trades=settled, net_r=net_r,
        brier=sum(losses) / len(losses) if losses else None,
        forecast_count=len(losses), review_required=breached or paused,
    )
