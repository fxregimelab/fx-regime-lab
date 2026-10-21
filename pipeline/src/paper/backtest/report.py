"""Reporting for the offline backtest: weekly P&L, per-trade stats, funnel.

Pure aggregation over :class:`~src.paper.backtest.engine.BacktestResult`. It
renders Markdown and JSON so the numbers can be reviewed and diffed, and it
labels every table as *historical simulation* so nobody mistakes it for live
performance.

SEMANTICS (PD-00C2, decisions A1 and A9)
----------------------------------------
Every R aggregate in this module is SETTLED-ONLY. A trade whose outcome is
unknown -- the input ended before its calendar-day horizon -- is never a win,
never a settled loss and never part of a performance number. The censored
tail is not hidden: it is reported separately, as MARKS, beside the settled
figures (``unresolved_r``, ``trades_censored``, ``net_r_with_marks``,
``trades_per_week_all``).

The report carries a machine-readable ``semantics`` block
(:func:`semantics_block`), so a reader never has to guess which basis a
number uses, which horizon it respects or which fill rule produced it.

The funnel keeps the stages apart (A9): ``candidates_emitted`` is the
DETECTOR output, never the admitted count, and the funnel reconciles:

    candidates_emitted - trades_admitted == sum(admission_rejections)
    trades_admitted == trades_settled + trades_censored

This module changes no engine or portfolio behaviour: it only describes what
the replay produced.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from src.paper.backtest.engine import (
    A_COOLDOWN,
    A_DAILY_STOP,
    A_DUPLICATE,
    A_ENTRY_FILL_MISMATCH,
    A_INVALID_RISK,
    A_MAX_SLOTS,
    A_NEW_TRADES_DAY,
    A_NO_ENTRY_BAR,
    A_OPEN_RISK,
    A_PAIR_SLOTS,
    A_USD_SIGN_CAP,
    A_WEEKLY_STOP,
    HORIZON_BASIS,
    BacktestConfig,
    BacktestResult,
    Trade,
)
from src.paper.backtest.portfolio import JointResult, PairBars

_STATE_LABEL = "Historical simulation - not live results"

# The R unit of the engine: one R is the ORIGINAL stop distance of the parent.
_R_UNIT = "price_R"

# The entry fill rule the detectors plan and the engine books.
_ENTRY_FILL_RULE = "next_m15_open"

# The stem reserved for the HISTORICAL report. It is never regenerated (A8).
RESERVED_STEM = "backtest"

# Every admission reason the engine can record. The funnel always lists them
# all, so a reason that never fired stays visible as a zero instead of
# disappearing from the report.
_ADMISSION_REASONS: tuple[str, ...] = (
    A_PAIR_SLOTS,
    A_MAX_SLOTS,
    A_OPEN_RISK,
    A_DAILY_STOP,
    A_WEEKLY_STOP,
    A_NEW_TRADES_DAY,
    A_COOLDOWN,
    A_DUPLICATE,
    A_ENTRY_FILL_MISMATCH,
    A_USD_SIGN_CAP,
    A_NO_ENTRY_BAR,
    A_INVALID_RISK,
)


def _iso_week(when: datetime) -> str:
    iso = when.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


# --- Semantics -------------------------------------------------------------------


def semantics_block() -> dict[str, Any]:
    """The machine-readable meaning of every number in this report.

    The block names the basis, what the censored tail is excluded from, where
    the marks are reported, the horizon basis, the entry fill rule, the two
    known limitations (R1 and R2) and the two things this report does NOT
    certify: the management policy and the historical report's freshness.
    """
    return {
        "basis": "settled_only",
        "r_unit": _R_UNIT,
        "settled_definition": (
            "A trade is SETTLED when its outcome is resolved. A censored trade "
            "(the input ended before its horizon) is NOT settled: it is never a "
            "win, never a settled loss and never part of a performance number."
        ),
        "censored_tail_excluded_from": [
            "net_r",
            "gross_r",
            "costs_r",
            "expectancy_r",
            "win_rate",
            "avg_win_r",
            "avg_loss_r",
            "profit_factor",
            "median_r",
            "best_r",
            "worst_r",
            "weekly net_r / gross_r / costs_r / wins",
            "per_setup net_r / win_rate / expectancy_r / avg_win_r / avg_loss_r",
            "trades_per_week",
            "trades_per_active_week",
        ],
        "marks_reported_separately": [
            "unresolved_r",
            "net_r_all",
            "gross_r_all",
            "costs_r_all",
            "expectancy_r_all",
            "trades_censored",
            "trades_total",
            "weekly.net_r_with_marks",
            "weekly.unresolved",
            "weekly.trades_per_week_all",
            "weekly.unresolved_total",
            "weekly_rows[].unresolved",
            "weekly_rows[].net_r_with_marks",
            "weekly_rows[].trades_total",
            "weekly.weeks_with_trades",
            "per_setup.unresolved_r",
            "per_setup.net_r_all",
            "per_setup.win_rate_all",
            "per_setup.expectancy_r_all",
            "per_setup.trades_total",
        ],
        "census_counts_include_censored": [
            "trades_total",
            "by_setup",
            "by_side",
            "by_exit",
            "candidates_emitted",
            "trades_admitted",
        ],
        "horizon_basis": HORIZON_BASIS,
        "horizon_note": (
            "The research horizon is a CALENDAR-DAY bound. It is NOT "
            "broker-session T+5: the trading-session count is a separate, "
            "unbound semantic and is never relabelled as this one."
        ),
        "entry_fill": _ENTRY_FILL_RULE,
        "entry_fill_note": (
            "Entry fills at the open of the next M15 bar after the decision bar "
            "closes. A candidate whose planned fill is not a real M15 open is "
            "rejected (A_ENTRY_FILL_MISMATCH), never booked."
        ),
        "limitations": {
            "R1": (
                "The detector gates (stop floor, cost share, entry band) are "
                "evaluated at the planned fill price, which is the NEXT bar's "
                "open and therefore not known at decision time. This is a mild "
                "lookahead in the accept/reject decision, not in the fill."
            ),
            "R2": (
                "There is NO fill model. The harness assumes a market fill at "
                "the next open; it models no slippage beyond the canonical cost "
                "table, no partial fills and no no-fill. The canonical cost "
                "table is a COST model, not a fill model."
            ),
        },
        "management_policy_certified": False,
        "management_policy_note": (
            "The management policy is NOT certified by this report. The "
            "one-close early adverse cut and the unconditional Friday flatten "
            "still diverge from AD execution spec (03) section 7. PD-00C "
            "certifies replay honesty only, never the management policy."
        ),
        "historical_report_stale_by_design": True,
        "historical_report_note": (
            "The historical reports/desk/research/backtest.json is NOT "
            "regenerated by this packet. It was written before the PD-00B "
            "engine repair and the PD-00C event-time replay, so its numbers "
            "are stale by design and must not be compared with this report."
        ),
        "rebased_legacy_keys": {
            "note": (
                "These bare keys MEANED something else in the historical file. "
                "A consumer comparing field-by-field must not read them as the "
                "same quantity."
            ),
            "trade_stats.trades": "was booked; is now SETTLED (trades_total is booked)",
            "per_setup.<setup_id>.trades": "was booked; is now SETTLED",
            "weekly_rows[].trades": "was booked; is now SETTLED",
            "weekly.trades_per_week": "was booked per week; is now SETTLED per week",
            "weekly.trades_per_active_week": (
                "was booked per active week; is now SETTLED per active week"
            ),
            "funnel.candidates_passed_all_detector_gates": (
                "was admitted; is now the EMITTED candidate count (A9)"
            ),
            "funnel.trades_taken": "unchanged: admitted parents",
        },
        "sibling_output_scope": (
            "This settled-only basis applies to THIS report only. The sibling "
            "outputs in the same folder -- dense*.json, rules.json, "
            "frequency_curve*.json, edge_scan_h1.json and funnel.json -- come "
            "from different harnesses that keep their OWN all-trades semantics. "
            "Do not compare their net_r with this report's."
        ),
    }


# --- Weekly ----------------------------------------------------------------------


def weekly_table(result: BacktestResult, *, risk_per_trade: float) -> list[dict[str, Any]]:
    """One row per ISO week that contains at least one trade.

    The row is SETTLED-ONLY: ``trades``, ``wins``, ``net_r``, ``gross_r`` and
    ``costs_r`` count the settled trades only. The censored tail stays
    visible in ``unresolved`` (how many) and in ``net_r_with_marks`` (the
    settled result plus the unresolved marks); ``trades_total`` keeps the
    booked census.
    """
    buckets: dict[str, list[Trade]] = defaultdict(list)
    for trade in result.trades:
        buckets[_iso_week(trade.entry_at)].append(trade)
    rows: list[dict[str, Any]] = []
    for week in sorted(buckets):
        trades = buckets[week]
        settled = [t for t in trades if t.settled]
        censored = [t for t in trades if not t.settled]
        net_r = sum(t.net_r for t in settled)
        marks_r = sum(t.net_r for t in censored)
        rows.append(
            {
                "week": week,
                "trades": len(settled),
                "trades_total": len(trades),
                "unresolved": len(censored),
                "wins": sum(1 for t in settled if t.net_r > 0),
                "net_r": round(net_r, 3),
                "net_r_with_marks": round(net_r + marks_r, 3),
                "net_pct": round(net_r * risk_per_trade * 100.0, 2),
                "gross_r": round(sum(t.r_multiple for t in settled), 3),
                "costs_r": round(sum(t.cost_r for t in settled), 3),
            }
        )
    return rows


def weekly_summary(result: BacktestResult, *, risk_per_trade: float) -> dict[str, Any]:
    """Average gain/loss per active week and per trade, in R and in percent.

    SETTLED-ONLY: ``trades_per_week`` and every week statistic count the
    settled trades only, and a week counts as active when it holds at least
    one SETTLED trade. The booked census is reported beside them as
    ``trades_per_week_all`` and ``unresolved_total``.
    """
    weeks = weekly_table(result, risk_per_trade=risk_per_trade)
    total_days = (result.end - result.start).days or 1
    total_weeks = max(1.0, total_days / 7.0)
    booked = result.trade_count
    settled = result.settled_count
    censored = result.censored_count
    active = [row for row in weeks if row["trades"] > 0]
    net_rs = [float(row["net_r"]) for row in active]
    positive = [r for r in net_rs if r > 0]
    negative = [r for r in net_rs if r < 0]
    return {
        "active_weeks": len(active),
        "weeks_with_trades": len(weeks),
        "weeks_with_unresolved": sum(1 for row in weeks if row["unresolved"] > 0),
        "total_weeks_in_sample": round(total_weeks, 1),
        "trades_per_week": round(settled / total_weeks, 2),
        "trades_per_week_all": round(booked / total_weeks, 2),
        "trades_per_active_week": round(settled / len(active), 2) if active else 0.0,
        "trades_per_active_week_all": round(booked / len(active), 2) if active else 0.0,
        "unresolved_total": censored,
        "avg_week_net_r": round(sum(net_rs) / len(net_rs), 3) if net_rs else 0.0,
        "avg_week_net_pct": (
            round(sum(net_rs) / len(net_rs) * risk_per_trade * 100.0, 3) if net_rs else 0.0
        ),
        "avg_winning_week_r": round(sum(positive) / len(positive), 3) if positive else 0.0,
        "avg_losing_week_r": round(sum(negative) / len(negative), 3) if negative else 0.0,
        "best_week_r": round(max(net_rs), 3) if net_rs else 0.0,
        "worst_week_r": round(min(net_rs), 3) if net_rs else 0.0,
        "positive_weeks": len(positive),
        "negative_weeks": len(negative),
        "flat_weeks": len(net_rs) - len(positive) - len(negative),
    }


# --- Trade statistics ------------------------------------------------------------


def trade_stats(result: BacktestResult) -> dict[str, Any]:
    """The performance of the SETTLED trades, with the censored tail beside it.

    Every R aggregate (net, gross, costs, expectancy, win rate, average win,
    average loss, profit factor, median, best, worst) is settled-only. The
    censored tail is reported separately: ``trades_total``,
    ``trades_censored``, ``unresolved_r`` and the ``*_all`` variants. The
    census counters (``by_setup``, ``by_side``, ``by_exit``) count the
    BOOKED trades, so the censored exits stay visible in ``by_exit``.
    """
    settled = result.settled_trades
    booked = result.trades
    net_rs = sorted(t.net_r for t in settled)
    median = (
        net_rs[len(net_rs) // 2]
        if len(net_rs) % 2
        else (net_rs[len(net_rs) // 2 - 1] + net_rs[len(net_rs) // 2]) / 2.0
    ) if net_rs else 0.0
    profit_factor = result.profit_factor
    return {
        "trades_total": len(booked),
        "trades_settled": len(settled),
        "trades_censored": result.censored_count,
        # legacy alias of trades_settled (the R aggregates are settled-only)
        "trades": len(settled),
        "win_rate": round(result.win_rate, 3),
        "expectancy_r": round(result.expectancy_r, 3),
        "avg_win_r": round(result.avg_win_r, 3),
        "avg_loss_r": round(result.avg_loss_r, 3),
        "median_r": round(median, 3),
        "best_r": round(max(net_rs), 3) if net_rs else 0.0,
        "worst_r": round(min(net_rs), 3) if net_rs else 0.0,
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "inf",
        "total_net_r": round(result.net_r, 3),
        "total_gross_r": round(result.gross_r, 3),
        "total_costs_r": round(result.costs_r, 3),
        "net_r_all": round(result.net_r_all, 3),
        "gross_r_all": round(result.gross_r_all, 3),
        "costs_r_all": round(result.costs_r_all, 3),
        "expectancy_r_all": round(result.expectancy_r_all, 3),
        "unresolved_r": round(result.unresolved_r, 3),
        "avg_bars_held": (
            round(sum(t.bars_held for t in settled) / len(settled), 1) if settled else 0.0
        ),
        "avg_mae_r": (
            round(sum(t.mae_r for t in settled) / len(settled), 3) if settled else 0.0
        ),
        "avg_mfe_r": (
            round(sum(t.mfe_r for t in settled) / len(settled), 3) if settled else 0.0
        ),
        "partial_taken": sum(1 for t in settled if t.partial_taken),
        "by_setup": dict(Counter(t.setup_id for t in booked)),
        "by_setup_settled": dict(Counter(t.setup_id for t in settled)),
        "by_side": dict(Counter(t.side for t in booked)),
        "by_side_settled": dict(Counter(t.side for t in settled)),
        "by_exit": dict(Counter(t.exit_reason for t in booked)),
        "by_exit_settled": dict(Counter(t.exit_reason for t in settled)),
    }


def per_setup_stats(result: BacktestResult) -> dict[str, dict[str, Any]]:
    """Per-setup performance, SETTLED-ONLY, with the censored tail beside it.

    A setup whose trades are all censored has NO settled sample: every rate is
    reported as 0.0 (never a division by zero) and the counts say why.
    """
    grouped: dict[str, list[Trade]] = defaultdict(list)
    for trade in result.trades:
        grouped[trade.setup_id].append(trade)
    out: dict[str, dict[str, Any]] = {}
    for setup_id, trades in sorted(grouped.items()):
        settled = [t for t in trades if t.settled]
        censored = [t for t in trades if not t.settled]
        wins = [t for t in settled if t.net_r > 0]
        losses = [t for t in settled if t.net_r <= 0]
        net = sum(t.net_r for t in settled)
        gross_win = sum(t.net_r for t in wins)
        gross_loss = -sum(t.net_r for t in losses)
        if gross_loss > 0.0:
            profit_factor: float | str = round(gross_win / gross_loss, 2)
        elif gross_win > 0.0:
            profit_factor = "inf"
        else:
            profit_factor = 0.0
        out[setup_id] = {
            "trades_total": len(trades),
            "trades_settled": len(settled),
            "trades_censored": len(censored),
            # legacy alias of trades_settled
            "trades": len(settled),
            "net_r": round(net, 3),
            "gross_r": round(sum(t.r_multiple for t in settled), 3),
            "costs_r": round(sum(t.cost_r for t in settled), 3),
            "net_r_all": round(sum(t.net_r for t in trades), 3),
            "unresolved_r": round(sum(t.net_r for t in censored), 3),
            "win_rate": round(len(wins) / len(settled), 3) if settled else 0.0,
            "expectancy_r": round(net / len(settled), 3) if settled else 0.0,
            "avg_win_r": round(sum(t.net_r for t in wins) / len(wins), 3) if wins else 0.0,
            "avg_loss_r": round(sum(t.net_r for t in losses) / len(losses), 3) if losses else 0.0,
            "profit_factor": profit_factor,
            "win_rate_all": (
                round(len([t for t in trades if t.net_r > 0]) / len(trades), 3) if trades else 0.0
            ),
            "expectancy_r_all": (
                round(sum(t.net_r for t in trades) / len(trades), 3) if trades else 0.0
            ),
        }
    return out


# --- Funnel ----------------------------------------------------------------------


def _split_rejections(rejections: Counter[str]) -> tuple[dict[str, int], dict[str, int]]:
    """Split the rejection counters into admission and detector rejections.

    A known admission reason is always an admission rejection. A key with a
    ``setup:reason`` shape is a detector rejection. Any other bare key is an
    admission-phase reason this report does not know yet: it is counted as an
    admission rejection so the funnel still reconciles.
    """
    admission: dict[str, int] = {}
    detector: dict[str, int] = {}
    for key, count in rejections.items():
        if key in _ADMISSION_REASONS:
            admission[key] = count
        elif ":" in key:
            detector[key] = count
        else:
            admission[key] = count
    return admission, detector


def funnel(result: BacktestResult) -> dict[str, Any]:
    """The A9 funnel: emitted -> admitted -> settled / censored.

    ``candidates_emitted`` is the DETECTOR output. It is a different number
    from ``trades_admitted`` (the booked parents), and the funnel reconciles:
    ``candidates_emitted - trades_admitted == sum(admission_rejections)`` and
    ``trades_admitted == trades_settled + trades_censored``.
    """
    admission, detector = _split_rejections(result.rejections)
    per_setup: dict[str, Counter[str]] = defaultdict(Counter)
    for key, count in detector.items():
        setup_id, _, reason = key.partition(":")
        per_setup[setup_id][reason] += count
    emitted = result.candidates_emitted
    admitted = result.admitted_count
    settled = result.settled_count
    censored = result.censored_count
    admission_total = sum(admission.values())
    known = {reason: admission.get(reason, 0) for reason in _ADMISSION_REASONS}
    extra = {key: count for key, count in admission.items() if key not in _ADMISSION_REASONS}
    return {
        "h1_opportunities_evaluated": result.opportunities,
        "candidates_emitted": emitted,
        "trades_admitted": admitted,
        "trades_settled": settled,
        "trades_censored": censored,
        # legacy aliases, now carrying the CORRECT values (A9)
        "candidates_passed_all_detector_gates": emitted,
        "trades_taken": admitted,
        "admission_rejection_total": admission_total,
        "emitted_not_admitted": emitted - admitted,
        "reconciles": (
            emitted - admitted == admission_total and admitted == settled + censored
        ),
        "candidates_by_setup": dict(result.setup_counts),
        "candidates_emitted_by_setup": dict(result.emitted_setup_counts),
        "detector_rejections_by_reason": dict(
            sorted(detector.items(), key=lambda kv: -kv[1])
        ),
        "detector_rejections_by_setup": {
            setup: dict(counter.most_common()) for setup, counter in per_setup.items()
        },
        "admission_rejections": {**known, **extra},
    }


# --- Joint replay ----------------------------------------------------------------


def joint_to_results(
    joint_result: JointResult,
    pairs: Sequence[PairBars],
    *,
    cfg: BacktestConfig,
) -> list[BacktestResult]:
    """Split a joint replay into the per-pair results the report aggregates.

    The joint replay books ONE shared portfolio, so its rejections are global.
    Every rejection is attributed to the pair of the candidate it refused, so
    the per-pair funnels and the combined funnel both reconcile:

        candidates_emitted == trades_admitted + admission_rejections
        trades_admitted == trades_settled + trades_censored
    """
    bars_by_pair = {series.pair: series for series in pairs}
    rejects_by_pair: dict[str, Counter[str]] = defaultdict(Counter)
    for event in joint_result.events:
        if event.kind == "reject":
            rejects_by_pair[event.pair][event.reason] += 1

    results: list[BacktestResult] = []
    for pair, detection in joint_result.detections.items():
        series = bars_by_pair.get(pair)
        m15 = list(series.m15) if series else []
        h1 = list(series.h1) if series else []
        trades = list(joint_result.per_pair.get(pair, ()))
        rejections: Counter[str] = Counter(detection.rejections)
        rejections.update(rejects_by_pair.get(pair, Counter()))
        results.append(
            BacktestResult(
                pair=pair,
                start=(
                    m15[0].timestamp if m15 else (h1[0].timestamp if h1 else datetime.min)
                ),
                end=h1[-1].timestamp if h1 else datetime.min,
                trades=trades,
                rejections=rejections,
                setup_counts=Counter(t.setup_id for t in trades),
                opportunities=detection.opportunities,
                config=cfg,
                candidates_emitted=len(detection.candidates),
                emitted_setup_counts=Counter(detection.emitted_by_setup),
            )
        )
    return results


# --- Report ----------------------------------------------------------------------


def build_report(
    results: list[BacktestResult], *, joint: JointResult | None = None
) -> dict[str, Any]:
    """Everything the owner asked for, per pair and combined.

    Every R aggregate is SETTLED-ONLY (see :func:`semantics_block`); the
    censored tail is reported beside it, never folded into it.
    """
    cfg = results[0].config if results else None
    risk = cfg.risk_per_trade if cfg else 0.01
    pairs: dict[str, Any] = {}
    for result in results:
        pairs[result.pair] = {
            "span": {
                "start": result.start.date().isoformat(),
                "end": result.end.date().isoformat(),
                "days": (result.end - result.start).days,
            },
            "trade_stats": trade_stats(result),
            "weekly": weekly_summary(result, risk_per_trade=risk),
            "weekly_rows": weekly_table(result, risk_per_trade=risk),
            "per_setup": per_setup_stats(result),
            "funnel": funnel(result),
        }
    combined_trades = [t for r in results for t in r.trades]
    all_rejections: Counter[str] = Counter()
    all_setups: Counter[str] = Counter()
    all_emitted_setups: Counter[str] = Counter()
    emitted_total = 0
    for result in results:
        all_rejections.update(result.rejections)
        all_setups.update(result.setup_counts)
        all_emitted_setups.update(result.emitted_setup_counts)
        emitted_total += result.candidates_emitted
    combined = BacktestResult(
        pair="ALL",
        start=min((r.start for r in results), default=datetime.min),
        end=max((r.end for r in results), default=datetime.min),
        trades=combined_trades,
        rejections=all_rejections,
        setup_counts=all_setups,
        opportunities=sum(r.opportunities for r in results),
        config=results[0].config if results else BacktestConfig(),
        candidates_emitted=emitted_total,
        emitted_setup_counts=all_emitted_setups,
    )
    report: dict[str, Any] = {
        "label": _STATE_LABEL,
        "risk_per_trade": risk,
        "mode": "joint" if joint is not None else "per_pair",
        "semantics": semantics_block(),
        "assumptions": [
            "Basis: SETTLED-ONLY. Every R aggregate below counts settled trades only.",
            "The censored tail (the input ended before the horizon) is excluded from "
            "the performance numbers and reported separately as marks.",
            "Entry fills at the next M15 open after the decision bar closes.",
            "The hold horizon is a CALENDAR-DAY research bound, not broker-session T+5.",
            "A bar spanning both stop and target books the STOP (pessimistic).",
            "Costs use the canonical round-trip + slippage table in src/paper/config.py.",
            "Management: 50% at +1R, stop to BE, chandelier trail on completed H1 bars.",
            "D1 context is a price/EMA20-slope proxy, not the production regime model.",
            "SU2-v1 is structurally untradeable under the 1.2xATR stop floor.",
            "R1: the detector gates are evaluated at the future fill open "
            "(a mild lookahead in the accept/reject decision).",
            "R2: there is no fill model; the canonical cost table is a cost model, "
            "not a fill model.",
            "The management policy is NOT certified by this report.",
            "The historical backtest.json is stale by design and is not regenerated.",
        ],
        "pairs": pairs,
        "combined": {
            "trade_stats": trade_stats(combined),
            "weekly": weekly_summary(combined, risk_per_trade=risk),
            "weekly_rows": weekly_table(combined, risk_per_trade=risk),
            "per_setup": per_setup_stats(combined),
            "funnel": funnel(combined),
        },
    }
    if joint is not None:
        report["joint"] = {
            "fingerprint": joint.fingerprint,
            "equity": joint.equity,
            "starting_equity": joint.starting_equity,
            "emitted_count": joint.emitted_count,
            "admitted_count": joint.admitted_count,
            "settled_count": joint.settled_count,
            "censored_count": joint.censored_count,
            "net_r": round(joint.net_r, 3),
            "net_r_all": round(joint.net_r_all, 3),
            "unresolved_r": round(joint.unresolved_r, 3),
            "tie_breaks": [
                {
                    "at": tie.at.isoformat(),
                    "ordered": [list(item) for item in tie.ordered],
                    "rule": tie.rule,
                }
                for tie in joint.tie_breaks
            ],
        }
    return report


_SIGNED = {
    "expectancy_r", "avg_win_r", "avg_loss_r", "median_r", "best_r", "worst_r",
    "total_net_r", "total_gross_r", "total_costs_r", "avg_mae_r", "avg_mfe_r",
    "avg_week_net_r", "avg_week_net_pct", "avg_winning_week_r", "avg_losing_week_r",
    "best_week_r", "worst_week_r", "net_r", "net_r_all", "gross_r", "gross_r_all",
    "costs_r", "costs_r_all", "unresolved_r", "expectancy_r_all", "net_r_with_marks",
}


def _fmt(value: Any, key: str = "") -> str:
    if isinstance(value, float):
        return f"{value:+.3f}" if key in _SIGNED else f"{value:.3f}"
    return str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Desk strategy backtest")
    lines.append("")
    lines.append(f"**{report['label']}.** Generated from completed bars only.")
    lines.append("")

    semantics = report.get("semantics", {})
    if semantics:
        lines.append("## Semantics")
        lines.append("")
        lines.append(f"- Basis: **{semantics.get('basis', 'unknown')}**")
        lines.append(f"- R unit: **{semantics.get('r_unit', 'unknown')}**")
        lines.append(f"- Horizon basis: **{semantics.get('horizon_basis', 'unknown')}**")
        lines.append(f"- Entry fill: **{semantics.get('entry_fill', 'unknown')}**")
        excluded = semantics.get("censored_tail_excluded_from") or []
        if excluded:
            lines.append("- Censored tail excluded from: " + ", ".join(str(x) for x in excluded))
        marks = semantics.get("marks_reported_separately") or []
        if marks:
            lines.append("- Marks reported separately: " + ", ".join(str(x) for x in marks))
        limitations = semantics.get("limitations") or {}
        for name in sorted(limitations):
            lines.append(f"- {name}: {limitations[name]}")
        lines.append(
            "- Management policy certified: "
            f"**{'yes' if semantics.get('management_policy_certified') else 'no'}**"
        )
        lines.append(
            "- Historical report stale by design: "
            f"**{'yes' if semantics.get('historical_report_stale_by_design') else 'no'}**"
        )
        lines.append("")

    lines.append("## Assumptions")
    lines.append("")
    for item in report["assumptions"]:
        lines.append(f"- {item}")
    lines.append("")

    for pair, block in report["pairs"].items():
        stats = block["trade_stats"]
        weekly = block["weekly"]
        lines.append(f"## {pair}")
        lines.append("")
        lines.append(
            f"Sample: {block['span']['start']} to {block['span']['end']} "
            f"({block['span']['days']} days)."
        )
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        for key in (
            "trades_total", "trades_settled", "trades_censored", "win_rate",
            "expectancy_r", "avg_win_r", "avg_loss_r", "median_r", "profit_factor",
            "total_net_r", "total_gross_r", "total_costs_r", "unresolved_r",
            "net_r_all", "expectancy_r_all", "avg_bars_held",
        ):
            if key in stats:
                lines.append(f"| {key} | {_fmt(stats[key], key)} |")
        lines.append("")
        lines.append("### Weekly")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        for key in (
            "trades_per_week", "trades_per_week_all", "trades_per_active_week",
            "unresolved_total", "active_weeks", "avg_week_net_r", "avg_week_net_pct",
            "avg_winning_week_r", "avg_losing_week_r", "best_week_r",
            "worst_week_r", "positive_weeks", "negative_weeks",
        ):
            lines.append(f"| {key} | {_fmt(weekly.get(key, 0), key)} |")
        lines.append("")
        lines.append("### Funnel")
        lines.append("")
        fn = block["funnel"]
        lines.append(f"- H1 opportunities evaluated: **{fn['h1_opportunities_evaluated']}**")
        lines.append(f"- Candidates emitted by the detectors: **{fn['candidates_emitted']}**")
        lines.append(f"- Trades admitted (booked): **{fn['trades_admitted']}**")
        lines.append(f"- Trades settled: **{fn['trades_settled']}**")
        lines.append(f"- Trades censored (unresolved): **{fn['trades_censored']}**")
        lines.append(f"- Admission rejections: **{fn['admission_rejection_total']}**")
        lines.append(f"- Funnel reconciles: **{'yes' if fn['reconciles'] else 'no'}**")
        lines.append("")
        lines.append("Top detector rejections:")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|---|---|")
        for key, count in list(fn["detector_rejections_by_reason"].items())[:12]:
            lines.append(f"| {key} | {count} |")
        lines.append("")
        lines.append("Admission rejections (every known reason, zero when unused):")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|---|---|")
        for key, count in fn["admission_rejections"].items():
            lines.append(f"| {key} | {count} |")
        lines.append("")
        if block["weekly_rows"]:
            lines.append("### Active weeks")
            lines.append("")
            lines.append(
                "| Week | Settled | Unresolved | Wins | Net R | Net R with marks | Net % |"
            )
            lines.append("|---|---|---|---|---|---|---|")
            for row in block["weekly_rows"]:
                lines.append(
                    f"| {row['week']} | {row['trades']} | {row['unresolved']} | "
                    f"{row['wins']} | {row['net_r']:+.2f} | "
                    f"{row['net_r_with_marks']:+.2f} | {row['net_pct']:+.2f}% |"
                )
            lines.append("")

    combined = report["combined"]
    lines.append("## Both pairs combined")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    for key, value in combined["trade_stats"].items():
        if isinstance(value, (int, float)):
            lines.append(f"| {key} | {_fmt(value, key)} |")
    lines.append("")
    lines.append("### Exit reasons (booked trades, censored tail included)")
    lines.append("")
    lines.append("| Exit | Count |")
    lines.append("|---|---|")
    for key, count in combined["trade_stats"].get("by_exit", {}).items():
        lines.append(f"| {key} | {count} |")
    lines.append("")
    lines.append("### Per setup")
    lines.append("")
    lines.append("| Setup | Settled | Censored | Net R | Win rate | Expectancy |")
    lines.append("|---|---|---|---|---|---|")
    for setup_id, row in combined["per_setup"].items():
        lines.append(
            f"| {setup_id} | {row['trades_settled']} | {row['trades_censored']} | "
            f"{row['net_r']:+.2f} | {row['win_rate']:.2%} | {row['expectancy_r']:+.3f} |"
        )
    lines.append("")
    joint_block = report.get("joint")
    if joint_block:
        lines.append("### Joint portfolio")
        lines.append("")
        lines.append(f"- Fingerprint: `{joint_block['fingerprint']}`")
        lines.append(
            f"- Emitted {joint_block['emitted_count']}, admitted "
            f"{joint_block['admitted_count']}, settled {joint_block['settled_count']}, "
            f"censored {joint_block['censored_count']}"
        )
        lines.append(
            f"- Settled net R: {joint_block['net_r']:+.3f} "
            f"(marks {joint_block['unresolved_r']:+.3f})"
        )
        lines.append("")
    return "\n".join(lines)


def write_report(
    report: dict[str, Any], out_dir: Path, stem: str = "backtest_joint"
) -> tuple[Path, Path]:
    """Write the Markdown and JSON report under ``stem``.

    The stem defaults to a NEW stem: ``backtest`` is the reserved stem of the
    historical report (``reports/desk/research/backtest.json``), which is
    deliberately NOT regenerated (A8).

    The reservation is enforced HERE, not only in the command-line script, so
    that a direct library caller cannot overwrite the historical artifact by
    passing ``stem="backtest"``.
    """
    if stem == RESERVED_STEM:
        raise ValueError(
            f"the stem {stem!r} is reserved for the historical report; "
            "it is never regenerated (A8)"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{stem}.md"
    json_path = out_dir / f"{stem}.json"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return md_path, json_path
