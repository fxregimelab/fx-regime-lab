"""Joint multi-pair portfolio replay for the private desk (research only).

The single-pair replay in :mod:`src.paper.backtest.engine` answers "what did
this one pair do". This module answers the portfolio question: **EURUSD and
USDJPY share ONE set of caps**, so an entry on one pair can consume the
slots, the loss capacity and the correlated USD load of the other pair.

The rules are the binding decisions of PD-00C (coordinator, 2026-10-19):

- **Event time.** The equity is derived from SETTLED exits only. A trade's
  outcome is booked when its exit happens, never when it is admitted, so no
  future outcome can fund an earlier opportunity. An open position holds its
  slot and its stop-risk reservation; a censored position holds both until
  the end of the sample and contributes NOTHING to the equity.
- **Ordering (A4).** At an equal timestamp the exits settle before the
  entries. Simultaneous entries are ordered by
  ``(entry_at, decision_at, pair, setup_id)``; the second entry therefore
  sees the first entry's reservation. Every tie-break is recorded and
  reproducible.
- **USD sign (A6).** The correlated one-way USD load is capped by TICKET
  COUNT, not by notional: the notional variant belongs to the sizing layer.
  ``EURUSD`` long is SHORT USD, ``USDJPY`` long is LONG USD.
- **Open risk (A3).** ``O`` is the flat 1R-per-open-position PROXY and ``C``
  is the planned trade's ``cost_r`` converted to an equity fraction. Both are
  labelled proxies: this is a research replay, not a funded account model.
- **Entry latch only (A2).** A loss-capacity breach blocks NEW entries. It
  never liquidates an open position: that needs a bar-driven engine and is a
  separate packet.
- **Management (A10).** The management policy is inherited unchanged from the
  engine. The one-close early cut and the unconditional Friday flatten are a
  labelled open item for PD-03; this module certifies replay honesty only,
  never the management policy.

Nothing here contacts a broker, a model or a database. The fingerprint is a
hash of the chronological event stream: the same timeline always reproduces
the same fingerprint, and any change in the ordering or in a booked outcome
changes it.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from src.paper.backtest.engine import (
    A_USD_SIGN_CAP,
    BacktestConfig,
    DetectionResult,
    PairCandidate,
    PortfolioGate,
    ReplayEvent,
    ReplayState,
    Trade,
    detect_candidates,
    order_candidates,
    replay_candidates,
)
from src.paper.config import LIMITS
from src.paper.features import OHLCBar

__all__ = [
    "JointConfig",
    "JointResult",
    "PairBars",
    "TieBreak",
    "replay_joint",
    "run_joint_backtest",
    "usd_sign",
]


def usd_sign(pair: str, side: str) -> int:
    """The sign of the position's USD exposure.

    ``+1`` is a long USD position, ``-1`` a short USD position and ``0`` a
    pair with no USD leg. ``EURUSD`` long is short USD (``-1``); ``USDJPY``
    long is long USD (``+1``). A short trade flips the sign.
    """
    if side not in ("long", "short"):
        raise ValueError(f"unknown trade side: {side!r}")
    base = pair[:3].upper()
    quote = pair[3:].upper()
    if base == "USD":
        sign = 1
    elif quote == "USD":
        sign = -1
    else:
        sign = 0
    return sign if side == "long" else -sign


@dataclass(frozen=True)
class PairBars:
    """The four bar series one pair contributes to the joint replay."""

    pair: str
    d1: list[OHLCBar]
    h4: list[OHLCBar]
    h1: list[OHLCBar]
    m15: list[OHLCBar]


@dataclass(frozen=True)
class JointConfig:
    """The cross-pair limits. The per-pair limits stay in BacktestConfig.

    ``max_same_usd_sign_tickets`` is a TICKET COUNT (A6): the notional
    variant belongs to the sizing layer and is not modelled here.
    """

    max_same_usd_sign_tickets: int = LIMITS.max_same_usd_sign_tickets


@dataclass(frozen=True)
class TieBreak:
    """One recorded ordering decision for candidates sharing a timestamp.

    ``ordered`` lists ``(pair, setup_id, side)`` in the ORDER THE CANDIDATES
    WERE SORTED for admission -- including candidates that were then rejected
    and never booked. It is the candidate ordering, not an admission log; the
    events carry which candidates were actually admitted.
    """

    at: datetime
    ordered: tuple[tuple[str, str, str], ...]
    rule: str = "entry_at, decision_at, pair, setup_id, side"


@dataclass(frozen=True)
class JointResult:
    """The joint replay outcome: trades, events, rejections and a fingerprint.

    The funnel counts are kept apart on purpose (A9): ``emitted_count`` is
    the detector output, ``admitted_count`` the booked parents and
    ``settled_count`` the parents with a resolved outcome.
    """

    trades: tuple[Trade, ...]
    events: tuple[ReplayEvent, ...]
    rejections: Counter[str]
    tie_breaks: tuple[TieBreak, ...]
    equity: float
    starting_equity: float
    fingerprint: str
    per_pair: Mapping[str, tuple[Trade, ...]] = field(default_factory=dict)
    detections: Mapping[str, DetectionResult] = field(default_factory=dict)

    @property
    def trade_count(self) -> int:
        return len(self.trades)

    @property
    def emitted_count(self) -> int:
        """Candidates the detectors emitted, before admission."""
        return sum(len(detection.candidates) for detection in self.detections.values())

    @property
    def admitted_count(self) -> int:
        """Candidates that passed admission and were booked."""
        return len(self.trades)

    @property
    def settled_count(self) -> int:
        """Booked parents with a resolved outcome."""
        return sum(1 for trade in self.trades if trade.settled)

    @property
    def censored_count(self) -> int:
        """Booked parents whose outcome is unknown (censored)."""
        return sum(1 for trade in self.trades if not trade.settled)

    @property
    def net_r(self) -> float:
        """SETTLED-ONLY net R."""
        return sum(trade.net_r for trade in self.trades if trade.settled)

    @property
    def net_r_all(self) -> float:
        """Net R over every booked parent, censored tail included."""
        return sum(trade.net_r for trade in self.trades)

    @property
    def gross_r(self) -> float:
        """SETTLED-ONLY gross R (before the canonical cost table)."""
        return sum(trade.r_multiple for trade in self.trades if trade.settled)

    @property
    def gross_r_all(self) -> float:
        """Gross R over every booked parent, censored tail included."""
        return sum(trade.r_multiple for trade in self.trades)

    @property
    def costs_r(self) -> float:
        """SETTLED-ONLY canonical cost in R."""
        return sum(trade.cost_r for trade in self.trades if trade.settled)

    @property
    def costs_r_all(self) -> float:
        """Canonical cost over every booked parent, censored tail included."""
        return sum(trade.cost_r for trade in self.trades)

    @property
    def expectancy_r(self) -> float:
        """SETTLED-ONLY net R per settled parent."""
        settled = self.settled_count
        return self.net_r / settled if settled else 0.0

    @property
    def expectancy_r_all(self) -> float:
        """Net R per booked parent, censored tail included."""
        return self.net_r_all / len(self.trades) if self.trades else 0.0

    @property
    def unresolved_r(self) -> float:
        """The net R that is NOT settled: the censored tail only."""
        return sum(trade.net_r for trade in self.trades if not trade.settled)

    @property
    def equity_curve(self) -> tuple[tuple[datetime, float], ...]:
        """The equity after every chronological event."""
        return tuple((event.at, event.equity) for event in self.events)


def _usd_sign_gate(joint: JointConfig) -> PortfolioGate:
    """The correlated USD-load gate: a TICKET COUNT over the open positions."""

    def gate(state: ReplayState, pc: PairCandidate, _planned_cost_r: float) -> str | None:
        sign = usd_sign(pc.pair, pc.candidate.side)
        if sign == 0:
            return None
        same = sum(1 for p in state.open_positions if usd_sign(p.pair, p.side) == sign)
        if same >= joint.max_same_usd_sign_tickets:
            return A_USD_SIGN_CAP
        return None

    return gate


def _tie_breaks(ordered: Sequence[PairCandidate]) -> tuple[TieBreak, ...]:
    """Record every timestamp that carries more than one candidate."""
    groups: dict[datetime, list[PairCandidate]] = {}
    for pc in ordered:
        groups.setdefault(pc.candidate.entry_at, []).append(pc)
    out: list[TieBreak] = []
    for at, group in groups.items():
        if len(group) > 1:
            out.append(
                TieBreak(
                    at=at,
                    ordered=tuple(
                        (pc.pair, pc.candidate.setup_id, pc.candidate.side) for pc in group
                    ),
                )
            )
    return tuple(out)


def _fingerprint(events: Sequence[ReplayEvent]) -> str:
    """A stable hash of the chronological event stream."""
    digest = hashlib.sha256()
    for event in events:
        digest.update(
            "|".join(
                (
                    event.at.isoformat(),
                    event.kind,
                    event.pair,
                    event.setup_id,
                    event.side,
                    event.reason,
                    f"{event.net_r:.12f}",
                    f"{event.equity:.12f}",
                )
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def replay_joint(
    candidates: Sequence[PairCandidate],
    m15_bars: Mapping[str, list[OHLCBar]],
    h1_bars: Mapping[str, list[OHLCBar]],
    *,
    cfg: BacktestConfig | None = None,
    joint: JointConfig | None = None,
) -> JointResult:
    """Replay already-detected candidates against ONE shared portfolio.

    The candidates of every pair are merged into a single chronological
    stream, so the slots, the per-pair cap, the USD-sign ticket cap, the
    open-risk reservation and the daily/weekly loss capacity are shared.
    """
    cfg = cfg or BacktestConfig()
    joint = joint or JointConfig()
    ordered = order_candidates(candidates)
    outcome = replay_candidates(
        ordered,
        m15_bars,
        h1_bars,
        cfg=cfg,
        gate=_usd_sign_gate(joint),
    )
    per_pair: dict[str, list[Trade]] = {}
    for trade in outcome.trades:
        per_pair.setdefault(trade.pair, []).append(trade)
    return JointResult(
        trades=outcome.trades,
        events=outcome.events,
        rejections=outcome.rejections,
        tie_breaks=_tie_breaks(ordered),
        equity=outcome.equity,
        starting_equity=cfg.starting_equity,
        fingerprint=_fingerprint(outcome.events),
        per_pair={pair: tuple(trades) for pair, trades in per_pair.items()},
    )


def run_joint_backtest(
    pairs: Sequence[PairBars],
    *,
    cfg: BacktestConfig | None = None,
    joint: JointConfig | None = None,
) -> JointResult:
    """Detect on every pair, then replay them against one shared portfolio.

    The detection phase is the engine's :func:`detect_candidates`; only the
    admission and the settlement are joint.
    """
    cfg = cfg or BacktestConfig()
    joint = joint or JointConfig()
    detections: dict[str, DetectionResult] = {}
    for series in pairs:
        detections[series.pair] = detect_candidates(
            series.pair,
            d1=series.d1,
            h4=series.h4,
            h1=series.h1,
            m15=series.m15,
            cfg=cfg,
        )
    candidates = [
        PairCandidate(pair=pair, candidate=candidate)
        for pair, detection in detections.items()
        for candidate in detection.candidates
    ]
    result = replay_joint(
        candidates,
        {series.pair: series.m15 for series in pairs},
        {series.pair: series.h1 for series in pairs},
        cfg=cfg,
        joint=joint,
    )
    rejections = Counter(result.rejections)
    for detection in detections.values():
        rejections.update(detection.rejections)
    return JointResult(
        trades=result.trades,
        events=result.events,
        rejections=rejections,
        tie_breaks=result.tie_breaks,
        equity=result.equity,
        starting_equity=result.starting_equity,
        fingerprint=result.fingerprint,
        per_pair=result.per_pair,
        detections=detections,
    )
