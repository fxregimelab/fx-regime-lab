"""Round 4 Phase 3 — Research artifact generation.

Produces institutional-grade markdown reports from ``validation_stats``
for SSRN pre-prints, Substack posts, and internal research memos.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, cast

from src.db import writer

logger = logging.getLogger(__name__)


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.1f}%"


def _fmt_float(v: float | None, decimals: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}"


def generate_track_record_report(
    as_of_date: date | None = None,
    output_path: str | None = None,
) -> str:
    """Generate a markdown track-record report from ``validation_stats``.

    Parameters
    ----------
    as_of_date:
        Report date (defaults to latest available in validation_stats).
    output_path:
        If provided, write markdown to this file path.

    Returns
    -------
    Markdown string.
    """
    supabase = writer._client()
    query = (
        supabase.table("validation_stats")
        .select("*")
        .order("as_of_date", desc=True)
        .limit(50)
    )
    res = query.execute()
    rows: list[dict[str, Any]] = cast(list[dict[str, Any]], res.data or [])

    if not rows:
        logger.warning("No validation_stats rows found for report generation")
        return "# Track Record Report\n\n*No data available.*"

    if as_of_date is None:
        as_of_date = date.fromisoformat(str(rows[0]["as_of_date"]))

    iso = as_of_date.isoformat()
    day_rows = [r for r in rows if str(r.get("as_of_date")) == iso]
    if not day_rows:
        day_rows = rows[:1]

    overall = next((r for r in day_rows if r.get("pair") == "ALL"), None)

    lines: list[str] = []
    lines.append("# FX Regime Lab — Track Record Report")
    lines.append(f"\n**Report Date:** {iso}  ")
    lines.append("**Strategy:** G10 FX Regime Classification (EUR/USD, USD/JPY, USD/INR)")
    lines.append("**Horizons:** T+5 and T+20 trading days")
    lines.append("**Methodology:** Log-return validation with 5 bps Marcus dead-band")
    lines.append("")

    if overall:
        lines.append("## Aggregate Performance (All Pairs)")
        lines.append("")
        lines.append(
            "| Horizon | Calls | Directional | Wins | Win Rate | Mean Brier |"
            " Brier Skill | Sharpe | Max DD (bps) |"
        )
        lines.append(
            "|---------|-------|-------------|------|----------|------------|"
            "-------------|--------|--------------|"
        )
        for prefix, label in (("t5", "T+5"), ("t20", "T+20")):
            total = overall.get(f"{prefix}_total_calls") or 0
            directional = overall.get(f"{prefix}_directional_calls") or 0
            wins = overall.get(f"{prefix}_wins") or 0
            win_rate = _fmt_pct(overall.get(f"{prefix}_win_rate"))
            mean_brier = _fmt_float(overall.get(f"{prefix}_mean_brier"), 4)
            skill = _fmt_float(overall.get(f"{prefix}_brier_skill"), 4)
            sharpe = _fmt_float(overall.get(f"{prefix}_sharpe_like"), 3)
            mdd = _fmt_float(overall.get(f"{prefix}_max_drawdown_bps"), 2)
            lines.append(
                f"| {label} | {total} | {directional} | {wins} |"
                f" {win_rate} | {mean_brier} | {skill} | {sharpe} | {mdd} |"
            )
        lines.append("")

    lines.append("## Per-Pair Performance")
    lines.append("")
    pair_rows = [r for r in day_rows if r.get("pair") not in (None, "ALL")]
    for row in pair_rows:
        pair = row.get("pair")
        lines.append(f"### {pair}")
        lines.append("")
        lines.append("| Horizon | Calls | Win Rate | Mean Brier | Sharpe |")
        lines.append("|---------|-------|----------|------------|--------|")
        for prefix, label in (("t5", "T+5"), ("t20", "T+20")):
            total = row.get(f"{prefix}_total_calls") or 0
            win_rate = _fmt_pct(row.get(f"{prefix}_win_rate"))
            mean_brier = _fmt_float(row.get(f"{prefix}_mean_brier"), 4)
            sharpe = _fmt_float(row.get(f"{prefix}_sharpe_like"), 3)
            lines.append(f"| {label} | {total} | {win_rate} | {mean_brier} | {sharpe} |")
        lines.append("")

        # Calibration buckets
        calib_json = row.get("t5_calibration_json")
        if calib_json:
            try:
                calib = json.loads(calib_json) if isinstance(calib_json, str) else calib_json
                buckets = calib.get("buckets", [])
                if buckets:
                    lines.append("**T+5 Calibration Buckets:**")
                    lines.append("")
                    lines.append("| Bucket | Avg Confidence | Observed Accuracy | N |")
                    lines.append("|--------|----------------|-------------------|---|")
                    for b in buckets:
                        lines.append(
                            f"| {b.get('bucket_index')} |"
                        f" {_fmt_pct(b.get('avg_confidence'))} |"
                        f" {_fmt_pct(b.get('observed_accuracy'))} |"
                        f" {b.get('n')} |"
                        )
                    lines.append("")
            except Exception as exc:  # noqa: BLE001
                logger.debug("Calibration parse failed for %s: %s", pair, exc)

    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "- **Brier Score** measures probabilistic calibration. "
        "A perfectly calibrated forecaster scores 0.0; random guessing scores 0.25."
    )
    lines.append(
        "- **Brier Skill** is relative to the random baseline: "
        "(0.25 − mean Brier) / 0.25. Positive values indicate skill above chance."
    )
    lines.append(
        "- **Sharpe-like ratio** uses log-return bps: mean / std dev. "
        "It is NOT annualized; interpret as signal-to-noise over the horizon."
    )
    lines.append(
        "- **Max Drawdown (bps)** is the largest peak-to-trough drop "
        "in cumulative log-return bps across the validation window."
    )
    lines.append("")
    lines.append("---")
    lines.append(
        "*Generated by FX Regime Lab validation pipeline. "
        "Data is append-only; no backdating. See fxregimelab.com for live updates.*"
    )

    markdown = "\n".join(lines)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(markdown)
        logger.info("Track record report written to %s", output_path)

    return markdown


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    report = generate_track_record_report()
    if report:
        print(report)  # noqa: T201
