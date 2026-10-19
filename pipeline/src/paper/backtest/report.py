"""Reporting for the offline backtest: weekly P&L, per-trade stats, funnel.

Pure aggregation over :class:`~src.paper.backtest.engine.BacktestResult`. It
renders Markdown and JSON so the numbers can be reviewed and diffed, and it
labels every table as *historical simulation* so nobody mistakes it for live
performance.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.paper.backtest.engine import BacktestConfig, BacktestResult, Trade

_STATE_LABEL = "Historical simulation - not live results"


def _iso_week(when: datetime) -> str:
    iso = when.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def weekly_table(result: BacktestResult, *, risk_per_trade: float) -> list[dict[str, Any]]:
    """One row per ISO week that contains at least one trade."""
    buckets: dict[str, list[Trade]] = defaultdict(list)
    for trade in result.trades:
        buckets[_iso_week(trade.entry_at)].append(trade)
    rows: list[dict[str, Any]] = []
    for week in sorted(buckets):
        trades = buckets[week]
        net_r = sum(t.net_r for t in trades)
        rows.append(
            {
                "week": week,
                "trades": len(trades),
                "wins": sum(1 for t in trades if t.net_r > 0),
                "net_r": round(net_r, 3),
                "net_pct": round(net_r * risk_per_trade * 100.0, 2),
                "gross_r": round(sum(t.r_multiple for t in trades), 3),
                "costs_r": round(sum(t.cost_r for t in trades), 3),
            }
        )
    return rows


def weekly_summary(result: BacktestResult, *, risk_per_trade: float) -> dict[str, Any]:
    """Average gain/loss per active week and per-trade, in R and in percent."""
    weeks = weekly_table(result, risk_per_trade=risk_per_trade)
    if not weeks:
        return {
            "active_weeks": 0,
            "trades_per_week": 0.0,
            "avg_week_net_r": 0.0,
            "avg_week_net_pct": 0.0,
            "best_week_r": 0.0,
            "worst_week_r": 0.0,
            "positive_weeks": 0,
            "negative_weeks": 0,
            "flat_weeks": 0,
        }
    net_rs = [w["net_r"] for w in weeks]
    positive = [r for r in net_rs if r > 0]
    negative = [r for r in net_rs if r < 0]
    total_days = (result.end - result.start).days or 1
    total_weeks = max(1.0, total_days / 7.0)
    return {
        "active_weeks": len(weeks),
        "total_weeks_in_sample": round(total_weeks, 1),
        "trades_per_week": round(len(result.trades) / total_weeks, 2),
        "trades_per_active_week": round(len(result.trades) / len(weeks), 2),
        "avg_week_net_r": round(sum(net_rs) / len(net_rs), 3),
        "avg_week_net_pct": round(sum(net_rs) / len(net_rs) * risk_per_trade * 100.0, 3),
        "avg_winning_week_r": round(sum(positive) / len(positive), 3) if positive else 0.0,
        "avg_losing_week_r": round(sum(negative) / len(negative), 3) if negative else 0.0,
        "best_week_r": round(max(net_rs), 3),
        "worst_week_r": round(min(net_rs), 3),
        "positive_weeks": len(positive),
        "negative_weeks": len(negative),
        "flat_weeks": len(net_rs) - len(positive) - len(negative),
    }


def trade_stats(result: BacktestResult) -> dict[str, Any]:
    trades = result.trades
    if not trades:
        return {"trades": 0}
    r_multiples = sorted(t.net_r for t in trades)
    median = (
        r_multiples[len(r_multiples) // 2]
        if len(r_multiples) % 2
        else (r_multiples[len(r_multiples) // 2 - 1] + r_multiples[len(r_multiples) // 2]) / 2.0
    )
    return {
        "trades": len(trades),
        "win_rate": round(result.win_rate, 3),
        "expectancy_r": round(result.expectancy_r, 3),
        "avg_win_r": round(result.avg_win_r, 3),
        "avg_loss_r": round(result.avg_loss_r, 3),
        "median_r": round(median, 3),
        "best_r": round(max(t.net_r for t in trades), 3),
        "worst_r": round(min(t.net_r for t in trades), 3),
        "profit_factor": (
            round(result.profit_factor, 2) if result.profit_factor != float("inf") else "inf"
        ),
        "total_net_r": round(result.net_r, 3),
        "total_gross_r": round(result.gross_r, 3),
        "total_costs_r": round(result.costs_r, 3),
        "avg_bars_held": round(sum(t.bars_held for t in trades) / len(trades), 1),
        "avg_mae_r": round(sum(t.mae_r for t in trades) / len(trades), 3),
        "avg_mfe_r": round(sum(t.mfe_r for t in trades) / len(trades), 3),
        "partial_taken": sum(1 for t in trades if t.partial_taken),
        "by_setup": dict(Counter(t.setup_id for t in trades)),
        "by_side": dict(Counter(t.side for t in trades)),
        "by_exit": dict(Counter(t.exit_reason for t in trades)),
    }


def funnel(result: BacktestResult) -> dict[str, Any]:
    """Reconcile evaluated opportunities -> candidates -> admitted -> trades."""
    detector_rejections = {
        k: v for k, v in result.rejections.items() if ":" in k
    }
    admission_rejections = {
        k: v for k, v in result.rejections.items() if ":" not in k
    }
    per_setup: dict[str, Counter[str]] = defaultdict(Counter)
    for key, count in detector_rejections.items():
        setup_id, _, reason = key.partition(":")
        per_setup[setup_id][reason] += count
    return {
        "h1_opportunities_evaluated": result.opportunities,
        "candidates_passed_all_detector_gates": result.total_candidates,
        "trades_taken": len(result.trades),
        "candidates_by_setup": dict(result.setup_counts),
        "detector_rejections_by_reason": dict(
            sorted(detector_rejections.items(), key=lambda kv: -kv[1])
        ),
        "detector_rejections_by_setup": {
            setup: dict(counter.most_common()) for setup, counter in per_setup.items()
        },
        "admission_rejections": dict(admission_rejections),
    }


def per_setup_stats(result: BacktestResult) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Trade]] = defaultdict(list)
    for trade in result.trades:
        grouped[trade.setup_id].append(trade)
    out: dict[str, dict[str, Any]] = {}
    for setup_id, trades in sorted(grouped.items()):
        net = sum(t.net_r for t in trades)
        wins = [t for t in trades if t.net_r > 0]
        losses = [t for t in trades if t.net_r <= 0]
        out[setup_id] = {
            "trades": len(trades),
            "net_r": round(net, 3),
            "win_rate": round(len(wins) / len(trades), 3),
            "expectancy_r": round(net / len(trades), 3),
            "avg_win_r": round(sum(t.net_r for t in wins) / len(wins), 3) if wins else 0.0,
            "avg_loss_r": round(sum(t.net_r for t in losses) / len(losses), 3) if losses else 0.0,
        }
    return out


def build_report(results: list[BacktestResult]) -> dict[str, Any]:
    """Everything the owner asked for, per pair and combined."""
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
    for result in results:
        all_rejections.update(result.rejections)
        all_setups.update(result.setup_counts)
    combined = BacktestResult(
        pair="ALL",
        start=min((r.start for r in results), default=datetime.min),
        end=max((r.end for r in results), default=datetime.min),
        trades=combined_trades,
        rejections=all_rejections,
        setup_counts=all_setups,
        opportunities=sum(r.opportunities for r in results),
        config=results[0].config if results else BacktestConfig(),
    )
    return {
        "label": _STATE_LABEL,
        "risk_per_trade": risk,
        "assumptions": [
            "Entry fills at the next M15 open after the decision bar closes.",
            "A bar spanning both stop and target books the STOP (pessimistic).",
            "Costs use the canonical round-trip + slippage table in src/paper/config.py.",
            "Management: 50% at +1R, stop to BE, chandelier trail on completed H1 bars.",
            "D1 context is a price/EMA20-slope proxy, not the production regime model.",
            "SU2-v1 is structurally untradeable under the 1.2xATR stop floor.",
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


_SIGNED = {
    "expectancy_r", "avg_win_r", "avg_loss_r", "median_r", "best_r", "worst_r",
    "total_net_r", "total_gross_r", "total_costs_r", "avg_mae_r", "avg_mfe_r",
    "avg_week_net_r", "avg_week_net_pct", "avg_winning_week_r", "avg_losing_week_r",
    "best_week_r", "worst_week_r",
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
            "trades", "win_rate", "expectancy_r", "avg_win_r", "avg_loss_r",
            "median_r", "profit_factor", "total_net_r", "total_gross_r",
            "total_costs_r", "avg_bars_held",
        ):
            if key in stats:
                lines.append(f"| {key} | {_fmt(stats[key], key)} |")
        lines.append("")
        lines.append("### Weekly")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        for key in (
            "trades_per_week", "trades_per_active_week", "active_weeks",
            "avg_week_net_r", "avg_week_net_pct", "avg_winning_week_r",
            "avg_losing_week_r", "best_week_r", "worst_week_r",
            "positive_weeks", "negative_weeks",
        ):
            lines.append(f"| {key} | {_fmt(weekly.get(key, 0), key)} |")
        lines.append("")
        lines.append("### Funnel")
        lines.append("")
        fn = block["funnel"]
        lines.append(f"- H1 opportunities evaluated: **{fn['h1_opportunities_evaluated']}**")
        passing = fn["candidates_passed_all_detector_gates"]
        lines.append(f"- Candidates passing all detector gates: **{passing}**")
        lines.append(f"- Trades taken after admission: **{fn['trades_taken']}**")
        lines.append("")
        lines.append("Top detector rejections:")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|---|---|")
        for key, count in list(fn["detector_rejections_by_reason"].items())[:12]:
            lines.append(f"| {key} | {count} |")
        lines.append("")
        if block["weekly_rows"]:
            lines.append("### Active weeks")
            lines.append("")
            lines.append("| Week | Trades | Wins | Net R | Net % |")
            lines.append("|---|---|---|---|---|")
            for row in block["weekly_rows"]:
                lines.append(
                    f"| {row['week']} | {row['trades']} | {row['wins']} | "
                    f"{row['net_r']:+.2f} | {row['net_pct']:+.2f}% |"
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
    lines.append("### Per setup")
    lines.append("")
    lines.append("| Setup | Trades | Net R | Win rate | Expectancy |")
    lines.append("|---|---|---|---|---|")
    for setup_id, row in combined["per_setup"].items():
        lines.append(
            f"| {setup_id} | {row['trades']} | {row['net_r']:+.2f} | "
            f"{row['win_rate']:.2%} | {row['expectancy_r']:+.3f} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: dict[str, Any], out_dir: Path, stem: str = "backtest"
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{stem}.md"
    json_path = out_dir / f"{stem}.json"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return md_path, json_path
