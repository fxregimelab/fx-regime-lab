"""Report helpers for the dense walk-forward harness (research only)."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

import numpy as np
from scipy import stats

from src.paper.backtest.dense import DenseResult, TradeRecord


def _settled(trades: list[TradeRecord]) -> list[TradeRecord]:
    return [t for t in trades if t.net_r == t.net_r]


def _finite(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def _weekly_t_stat(
    result: DenseResult, trades: list[TradeRecord]
) -> tuple[int, float, float, float] | None:
    """One-sample t-test on weekly net R, with weeks without trades set to zero.

    The out-of-sample span comes from the first test window to the series end, so
    quiet weeks count as zero rather than disappearing. This is still not a block
    bootstrap; overlapping positions make the test optimistic.
    """
    if not result.folds:
        return None
    cursor = result.folds[0].test_start.date()
    end = result.end.date()
    keys: list[str] = []
    seen: set[str] = set()
    while cursor <= end:
        iso = cursor.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        if key not in seen:
            seen.add(key)
            keys.append(key)
        cursor += timedelta(days=7)
    by_week: dict[str, float] = defaultdict(float)
    for trade in trades:
        iso = trade.entry_at.isocalendar()
        by_week[f"{iso.year}-W{iso.week:02d}"] += trade.net_r
    values = np.array([by_week.get(key, 0.0) for key in keys], dtype=np.float64)
    if values.size < 3 or float(np.std(values, ddof=1)) == 0.0:
        return None
    stat, p_value = stats.ttest_1samp(values, 0.0)
    return len(keys), float(values.mean()), float(stat), float(p_value)


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
    net_total = sum(t.net_r for t in trades)
    spread_values = [t.entry_spread_points for t in trades if t.entry_spread_points > 0.0]
    net_values = np.array([t.net_r for t in trades], dtype=np.float64)
    if net_values.size >= 2 and float(np.std(net_values, ddof=1)) > 0.0:
        t_stat, p_value = stats.ttest_1samp(net_values, 0.0)
        t_stat_iid: float | None = float(t_stat)
        p_value_iid: float | None = float(p_value)
    else:
        t_stat_iid, p_value_iid = None, None

    paired = np.array(
        [t.net_r - t.matched_r for t in trades if np.isfinite(t.matched_r)],
        dtype=np.float64,
    )
    if paired.size >= 2 and float(np.std(paired, ddof=1)) > 0.0:
        t_stat_matched, p_value_matched = stats.ttest_1samp(paired, 0.0)
        t_stat_matched_f: float | None = float(t_stat_matched)
        p_value_matched_f: float | None = float(p_value_matched)
    else:
        t_stat_matched_f, p_value_matched_f = None, None

    last_fold = result.folds[-1] if result.folds else None
    last_fold_days = (
        (last_fold.test_end - last_fold.test_start).total_seconds() / 86400.0
        if last_fold is not None
        else 0.0
    )
    prior = [t for t in trades if last_fold is not None and t.fold != last_fold.fold]
    prior_net = sum(t.net_r for t in prior)
    weekly_stats = _weekly_t_stat(result, trades)
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
        "total_net_r": round(net_total, 4),
        "total_gross_r": round(sum(t.gross_r for t in trades), 4),
        "total_costs_r": round(sum(t.cost_r for t in trades), 4),
        "avg_win_r": round(gross_win / len(wins), 4) if wins else 0.0,
        "avg_loss_r": round(-gross_loss / len(losses), 4) if losses else 0.0,
        "profit_factor": round(gross_win / gross_loss, 4) if gross_loss > 0 else None,
        "unconditional_expectancy_r": _finite(result.unconditional_r),
        "matched_unconditional_r": _finite(result.matched_unconditional_r),
        "edge_vs_unconditional_r": _finite(
            result.expectancy_r - result.unconditional_r
        ),
        "edge_vs_matched_r": _finite(
            result.expectancy_r - result.matched_unconditional_r
        ),
        "t_stat_iid": round(t_stat_iid, 3) if t_stat_iid is not None else None,
        "p_value_iid": round(p_value_iid, 4) if p_value_iid is not None else None,
        "t_stat_matched": round(t_stat_matched_f, 3)
        if t_stat_matched_f is not None else None,
        "p_value_matched": round(p_value_matched_f, 4)
        if p_value_matched_f is not None else None,
        "weekly_weeks": weekly_stats[0] if weekly_stats else 0,
        "weekly_mean_r": round(weekly_stats[1], 4) if weekly_stats else None,
        "t_stat_weekly": round(weekly_stats[2], 3) if weekly_stats else None,
        "p_value_weekly": round(weekly_stats[3], 4) if weekly_stats else None,
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
        # Share of positive fold profit in the single best fold, and the same
        # share against total net. Both matter: a small net can make one fold
        # look dominant even when profits are spread out.
        "max_fold_share_of_positive": round(
            max(positive_folds) / fold_profit_total, 4
        ) if fold_profit_total > 0.0 else None,
        "max_fold_share_of_net": round(max(positive_folds) / net_total, 4)
        if net_total > 0.0 else None,
        "last_fold_days": round(last_fold_days, 1),
        "trades_excluding_last_fold": len(prior),
        "net_r_excluding_last_fold": round(prior_net, 4),
        "expectancy_excluding_last_fold": round(prior_net / len(prior), 4)
        if prior else None,
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


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.3f}"


def render_markdown(rows: list[dict[str, Any]], *, title: str, config: dict[str, Any]) -> str:
    lines = [
        f"# {title}",
        "",
        "**Historical simulation - not live results.** Walk-forward: every trade below was",
        "chosen by a model trained only on earlier bars. Entry at the next bar's open, stop",
        "before target on ambiguous bars, stop gaps fill at the open, target gaps cap at",
        "the target, canonical costs included.",
        "",
        "## Configuration (fixed for this run; not re-tuned per fold)",
        "",
        "Sweep winners are chosen after seeing the whole grid and are therefore",
        "post-hoc maxima, not a-priori configurations.",
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
    lines.append("## Selected vs benchmarks")
    lines.append("")
    lines.append(
        "All-bar unconditional averages every bar; matched averages both sides at "
        "the bars the model actually selected, removing bar-composition effects."
    )
    lines.append("")
    lines.append(
        "| Pair | Selected R | All-bar R | Matched R | Edge vs matched | t (iid) | p (iid) |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row['pair']} | {row['expectancy_r']:+.3f} | "
            f"{_fmt(row['unconditional_expectancy_r'])} | "
            f"{_fmt(row['matched_unconditional_r'])} | "
            f"{_fmt(row['edge_vs_matched_r'])} | "
            f"{_fmt(row['t_stat_iid'])} | {_fmt(row['p_value_iid'])} |"
        )
    lines.append("")
    lines.append(
        "Paired test (selected minus matched, same decision bars): "
        + ", ".join(
            f"{row['pair']} t={_fmt(row['t_stat_matched'])}, p={_fmt(row['p_value_matched'])}"
            for row in rows
        )
    )
    lines.append("")
    lines.append(
        "The t-test treats trades as independent; overlapping labels and the "
        "one-position constraint make it optimistic. Use it as a rough screen."
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
