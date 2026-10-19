"""Report helpers for the dense walk-forward harness (research only)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from src.paper.backtest.dense import DenseResult, TradeRecord


def _settled(trades: list[TradeRecord]) -> list[TradeRecord]:
    return [t for t in trades if t.net_r == t.net_r]


def weekly_rows(trades: list[TradeRecord]) -> list[dict[str, Any]]:
    buckets: dict[str, list[TradeRecord]] = defaultdict(list)
    for trade in trades:
        iso = trade.entry_at.isocalendar()
        buckets[f"{iso.year}-W{iso.week:02d}"].append(trade)
    rows: list[dict[str, Any]] = []
    for week in sorted(buckets):
        items = buckets[week]
        wins = [t for t in items if t.net_r > 0.0]
        losses = [t for t in items if t.net_r <= 0.0]
        rows.append(
            {
                "week": week,
                "trades": len(items),
                "net_r": round(sum(t.net_r for t in items), 4),
                "avg_win_r": round(
                    sum(t.net_r for t in wins) / len(wins), 4
                ) if wins else 0.0,
                "avg_loss_r": round(
                    sum(t.net_r for t in losses) / len(losses), 4
                ) if losses else 0.0,
            }
        )
    return rows


def summary(result: DenseResult) -> dict[str, Any]:
    trades = _settled(result.trades)
    wins = [t for t in trades if t.net_r > 0.0]
    losses = [t for t in trades if t.net_r <= 0.0]
    weeks = weekly_rows(trades)
    active_weeks = [w for w in weeks if int(w["trades"]) > 0]
    gross_win = sum(t.net_r for t in wins)
    gross_loss = -sum(t.net_r for t in losses)
    positive_folds = [f.net_r for f in result.folds if f.net_r > 0.0]
    fold_profit_total = sum(positive_folds)
    spread_values = [t.entry_spread_points for t in trades if t.entry_spread_points > 0.0]
    return {
        "pair": result.pair,
        "sample_start": result.start.isoformat(),
        "oos_start": result.folds[0].test_start.isoformat() if result.folds else None,
        "sample_end": result.end.isoformat(),
        "trades": len(trades),
        "trades_per_week": round(result.trades_per_week, 3),
        "active_weeks": len(active_weeks),
        "win_rate": round(result.win_rate, 4),
        "expectancy_r": round(result.expectancy_r, 4),
        "total_net_r": round(sum(t.net_r for t in trades), 4),
        "total_gross_r": round(sum(t.gross_r for t in trades), 4),
        "total_costs_r": round(sum(t.cost_r for t in trades), 4),
        "avg_win_r": round(gross_win / len(wins), 4) if wins else 0.0,
        "avg_loss_r": round(-gross_loss / len(losses), 4) if losses else 0.0,
        "profit_factor": round(gross_win / gross_loss, 4) if gross_loss > 0 else None,
        "unconditional_expectancy_r": round(result.unconditional_r, 4),
        "edge_vs_unconditional_r": round(
            result.expectancy_r - result.unconditional_r, 4
        ),
        "valid_bars": result.valid_bars,
        "long_trades": sum(1 for t in trades if t.side == "long"),
        "short_trades": sum(1 for t in trades if t.side == "short"),
        "avg_bars_held": round(
            sum(t.bars_held for t in trades) / len(trades), 2
        ) if trades else 0.0,
        "entry_spread_points_mean": round(float(np.mean(spread_values)), 2)
        if spread_values else None,
        "entry_spread_points_median": round(float(np.median(spread_values)), 2)
        if spread_values else None,
        "fold_profit_concentration": round(
            max(positive_folds) / fold_profit_total, 4
        ) if fold_profit_total > 0.0 else None,
        "average_week_net_r": round(
            sum(w["net_r"] for w in active_weeks) / len(active_weeks), 4
        ) if active_weeks else 0.0,
        "best_week_r": max((w["net_r"] for w in weeks), default=0.0),
        "worst_week_r": min((w["net_r"] for w in weeks), default=0.0),
        "fold_results": [
            {
                "fold": f.fold,
                "test_start": f.test_start.isoformat(),
                "test_end": f.test_end.isoformat(),
                "trades": f.trades,
                "net_r": round(f.net_r, 4),
                "mean_actual_r": round(f.mean_actual_r, 4),
                "unconditional_r": round(f.unconditional_r, 4),
                "threshold": round(f.threshold, 4),
                "train_rows": f.train_rows,
                "test_rows": f.test_rows,
            }
            for f in result.folds
        ],
        "mean_coefficients": _mean_coefficients(result),
        "weekly": weeks,
    }


def _mean_coefficients(result: DenseResult) -> list[dict[str, Any]]:
    """Average standardised ridge coefficient per feature across folds.

    Sign is relative to the proposed direction (positive supports the trade).
    This is diagnostic only; it is not a causal claim.
    """
    if not result.folds:
        return []
    names = list(result.folds[0].coefficients)
    averaged = []
    for name in names:
        values = [f.coefficients[name] for f in result.folds]
        averaged.append(
            {"feature": name, "mean": round(sum(values) / len(values), 5)}
        )
    return sorted(averaged, key=lambda item: abs(float(item["mean"])), reverse=True)


def render_markdown(rows: list[dict[str, Any]], *, title: str, config: dict[str, Any]) -> str:
    lines = [
        f"# {title}",
        "",
        "**Historical simulation - not live results.** Walk-forward: every trade below was",
        "chosen by a model trained only on earlier bars. Entry at the next bar's open, stop",
        "before target on ambiguous bars, gaps fill at the open, canonical costs included.",
        "",
        "## Configuration (fixed a priori, not tuned per fold)",
        "",
    ]
    for key, value in config.items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("| Pair | Trades | Trades/wk | Win rate | Expectancy R | Net R | Costs R |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row['pair']} | {row['trades']} | {row['trades_per_week']} | "
            f"{row['win_rate']:.1%} | {row['expectancy_r']:+.3f} | "
            f"{row['total_net_r']:+.2f} | {row['total_costs_r']:.2f} |"
        )
    lines.append("")
    lines.append("## Selected vs unconditional")
    lines.append("")
    lines.append("| Pair | Selected expectancy R | Unconditional R | Edge |")
    lines.append("|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row['pair']} | {row['expectancy_r']:+.3f} | "
            f"{row['unconditional_expectancy_r']:+.3f} | {row['edge_vs_unconditional_r']:+.3f} |"
        )
    lines.append("")
    for row in rows:
        lines.append(f"## {row['pair']} fold detail")
        lines.append("")
        lines.append("| Fold | Test window | Trades | Net R | Mean R | Unconditional R |")
        lines.append("|---|---|---|---|---|---|")
        for fold in row["fold_results"]:
            lines.append(
                f"| {fold['fold']} | {fold['test_start'][:10]} to {fold['test_end'][:10]} | "
                f"{fold['trades']} | {fold['net_r']:+.2f} | {fold['mean_actual_r']:+.3f} | "
                f"{fold['unconditional_r']:+.3f} |"
            )
        lines.append("")
    return "\n".join(lines)
