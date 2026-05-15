"""Walk-forward backtest for pair-specific models.

Compares v2 (old) vs v3 (new) composite models on historical data.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

from src.db import writer

# Pair-specific v3 composites
from src.pairs.eurusd.composite import EURUSDComposite
from src.pairs.usdinr.composite import USDINRComposite
from src.pairs.usdjpy.composite import USDJPYComposite
from src.regime.composite import compute_composite

logger = logging.getLogger(__name__)

# Deterministic seed for any stochastic elements (currently none, but reserved)
_RANDOM_SEED = 42
np.random.seed(_RANDOM_SEED)

_TRANSACTION_COST_BPS = 1.0  # Round-trip cost in basis points
_INITIAL_CAPITAL = 100_000.0


@dataclass
class DailyResult:
    date: str
    pair: str
    spot: float | None
    v2_composite: float | None
    v3_composite: float | None
    v2_predicted: str
    v3_predicted: str
    realized_t1: str | None
    realized_t5: str | None
    realized_t20: str | None
    v2_correct_t1: bool | None
    v2_correct_t5: bool | None
    v2_correct_t20: bool | None
    v3_correct_t1: bool | None
    v3_correct_t5: bool | None
    v3_correct_t20: bool | None
    v2_brier_t1: float | None
    v2_brier_t5: float | None
    v2_brier_t20: float | None
    v3_brier_t1: float | None
    v3_brier_t5: float | None
    v3_brier_t20: float | None
    v2_pnl_t1: float
    v3_pnl_t1: float


@dataclass
class ModelStats:
    model: str
    pair: str
    start_date: str
    end_date: str
    total_days: int
    signal_days: int
    accuracy_t1: float | None
    accuracy_t5: float | None
    accuracy_t20: float | None
    mean_brier_t1: float | None
    mean_brier_t5: float | None
    mean_brier_t20: float | None
    total_pnl: float
    sharpe_ratio: float | None
    max_drawdown_pct: float | None
    num_trades: int


def _log_return_bps(s0: float, s1: float) -> float:
    if s0 <= 0 or s1 <= 0:
        return 0.0
    return 10_000.0 * math.log(s1 / s0)


def _realized_direction(bps: float, deadband: float = 5.0) -> str:
    if bps > deadband:
        return "UP"
    if bps < -deadband:
        return "DOWN"
    return "NEUTRAL"


def _predicted_direction(composite: float | None, threshold: float = 0.2) -> str:
    if composite is None:
        return "NEUTRAL"
    if composite > threshold:
        return "BULLISH"
    if composite < -threshold:
        return "BEARISH"
    return "NEUTRAL"


def _is_correct(predicted: str, realized: str) -> bool:
    p = predicted.strip().upper()
    r = realized.strip().upper()
    if p == "BULLISH":
        return r == "UP"
    if p == "BEARISH":
        return r == "DOWN"
    if p == "NEUTRAL":
        return r == "NEUTRAL"
    return False


def _brier_score(confidence: float, correct: bool) -> float:
    p = float(np.clip(confidence, 0.0, 1.0))
    y = 1.0 if correct else 0.0
    return (p - y) ** 2


def _reconstruct_v2_composite(
    row: dict[str, Any],
    pair: str,
) -> float | None:
    """Reconstruct v2 composite from a historical signal row."""
    rate_diff = row.get("rate_diff_2y")
    cot_pct = row.get("cot_percentile")
    rv20 = row.get("realized_vol_20d")
    rv5 = row.get("realized_vol_5d")
    oi = row.get("oi_delta")

    rate_norm = None
    if rate_diff is not None and rv20 is not None and rv20 > 0:
        rate_norm = rate_diff / rv20

    cot_norm = None
    if cot_pct is not None:
        cot_norm = (cot_pct - 50.0) / 50.0

    vol_norm = None
    if rv5 is not None and rv20 is not None and rv20 > 0:
        vol_norm = ((rv5 / rv20) - 1.0) * 2.0

    oi_norm = None
    if oi is not None:
        oi_norm = float(oi)

    special = None
    # Pair-specific special signal proxies from historical data
    if pair == "EURUSD":
        pass  # No reliable historical special signal in signals table
    elif pair == "USDJPY":
        pass
    elif pair == "USDINR":
        pass

    return compute_composite(
        rate_norm,
        cot_norm,
        vol_norm,
        oi_norm,
        pair=pair,
        special_signal=special,
    )


def _reconstruct_v3_composite(
    row: dict[str, Any],
    pair: str,
) -> float | None:
    """Reconstruct v3 composite from a historical signal row."""
    rate_diff = row.get("rate_diff_2y")
    cot_pct = row.get("cot_percentile")
    vix = row.get("cross_asset_vix")
    rv20 = row.get("realized_vol_20d")

    rate_norm = None
    if rate_diff is not None:
        scaler = {"EURUSD": 2.0, "USDJPY": 4.0, "USDINR": 5.0}.get(pair, 3.0)
        rate_norm = max(-1.0, min(1.0, rate_diff / scaler))

    cot_norm = None
    if cot_pct is not None:
        cot_norm = (cot_pct - 50.0) / 50.0

    vol_norm = None
    if vix is not None:
        if vix > 30:
            vol_norm = -1.0
        elif vix > 25:
            vol_norm = -0.5
        elif vix < 15:
            vol_norm = 0.5
        else:
            vol_norm = 0.0
    elif rv20 is not None:
        # Approximate vol norm from realized vol
        vol_norm = max(-1.0, min(1.0, (rv20 - 0.08) / 0.08 * -1.0))

    vol_regime = (
        "HIGH_VOL"
        if (vix is not None and vix > 25) or (rv20 is not None and rv20 > 0.12)
        else "NEUTRAL"
    )

    if pair == "EURUSD":
        comp = EURUSDComposite(vol_regime=vol_regime)
        return comp.score(rate_norm, cot_norm, vol_norm, None)
    if pair == "USDJPY":
        comp = USDJPYComposite(vol_regime=vol_regime)
        return comp.score(rate_norm, cot_norm, vol_norm, None)
    if pair == "USDINR":
        comp = USDINRComposite(vol_regime=vol_regime)
        return comp.score(rate_norm, cot_norm, vol_norm, None)
    return None


def _simulate_pnl(
    composites: Sequence[float | None],
    spots: Sequence[float | None],
    holding_days: int = 1,
) -> tuple[list[float], int]:
    """Simple P&L simulation: enter proportional to composite, hold N days."""
    pnls: list[float] = []
    trades = 0
    n = len(composites)
    for i in range(n - holding_days):
        comp = composites[i]
        s0 = spots[i]
        s1 = spots[i + holding_days]
        if comp is None or s0 is None or s1 is None or s0 <= 0:
            pnls.append(0.0)
            continue
        # Position size = |composite| capped at 1.0, scaled to notional
        size = min(abs(comp), 1.0) * _INITIAL_CAPITAL
        direction = 1.0 if comp > 0 else -1.0 if comp < 0 else 0.0
        if direction == 0.0:
            pnls.append(0.0)
            continue
        gross_return = (s1 / s0 - 1.0) * direction
        # Round-trip transaction cost in decimal
        tc = _TRANSACTION_COST_BPS / 10_000.0
        net_return = gross_return - tc
        pnl = size * net_return
        pnls.append(pnl)
        trades += 1
    # Pad remaining days with 0
    for _ in range(holding_days):
        pnls.append(0.0)
    return pnls, trades


def _compute_sharpe(pnls: Sequence[float]) -> float | None:
    arr = np.array([x for x in pnls if x != 0.0], dtype=float)
    if len(arr) < 2:
        return None
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    if std <= 0:
        return None
    # Daily Sharpe, annualized assuming 252 trading days
    daily_sharpe = mean / std
    return daily_sharpe * math.sqrt(252.0)


def _compute_max_drawdown(pnls: Sequence[float]) -> float | None:
    cumulative = np.cumsum([x for x in pnls], dtype=float)
    if len(cumulative) == 0:
        return None
    peak = cumulative[0]
    max_dd = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
    if peak == 0:
        return None
    return (max_dd / abs(peak)) * 100.0


def _run_backtest_for_pair(
    pair: str,
    start_date: date,
    end_date: date,
    verbose: bool = False,
) -> tuple[list[DailyResult], ModelStats, ModelStats]:
    """Run backtest for a single pair, returning daily results + stats for v2 and v3."""
    logger.info(
        "Backtest start for %s: %s to %s", pair, start_date.isoformat(), end_date.isoformat()
    )

    # Load historical signals (newest-first)
    raw_rows = writer.get_historical_signals(pair, limit=5000)
    if not raw_rows:
        raise RuntimeError(f"No historical signals found for {pair}")

    # Filter to date range and sort ascending
    rows: list[dict[str, Any]] = []
    for r in raw_rows:
        d = date.fromisoformat(str(r["date"])[:10])
        if start_date <= d <= end_date:
            rows.append(r)
    rows.sort(key=lambda x: x["date"])

    if len(rows) < 30:
        raise RuntimeError(f"Insufficient data for {pair} in range: {len(rows)} rows")

    daily_results: list[DailyResult] = []
    v2_composites: list[float | None] = []
    v3_composites: list[float | None] = []
    spots: list[float | None] = []

    for idx, row in enumerate(rows):
        d = str(row["date"])[:10]
        spot = row.get("spot")
        spots.append(spot)

        v2 = _reconstruct_v2_composite(row, pair)
        v3 = _reconstruct_v3_composite(row, pair)
        v2_composites.append(v2)
        v3_composites.append(v3)

        v2_pred = _predicted_direction(v2)
        v3_pred = _predicted_direction(v3)

        # Forward returns
        def _fwd_spot(offset: int) -> float | None:
            if idx + offset < len(rows):
                return rows[idx + offset].get("spot")
            return None

        def _realized(offset: int) -> str | None:
            s0 = spot
            s1 = _fwd_spot(offset)
            if s0 is None or s1 is None or s0 <= 0:
                return None
            bps = _log_return_bps(s0, s1)
            return _realized_direction(bps)

        rt1 = _realized(1)
        rt5 = _realized(5)
        rt20 = _realized(20)

        v2_c1 = _is_correct(v2_pred, rt1) if rt1 is not None else None
        v2_c5 = _is_correct(v2_pred, rt5) if rt5 is not None else None
        v2_c20 = _is_correct(v2_pred, rt20) if rt20 is not None else None

        v3_c1 = _is_correct(v3_pred, rt1) if rt1 is not None else None
        v3_c5 = _is_correct(v3_pred, rt5) if rt5 is not None else None
        v3_c20 = _is_correct(v3_pred, rt20) if rt20 is not None else None

        v2_conf = min(abs(v2 or 0.0), 1.0)
        v3_conf = min(abs(v3 or 0.0), 1.0)

        v2_b1 = _brier_score(v2_conf, v2_c1) if v2_c1 is not None else None
        v2_b5 = _brier_score(v2_conf, v2_c5) if v2_c5 is not None else None
        v2_b20 = _brier_score(v2_conf, v2_c20) if v2_c20 is not None else None

        v3_b1 = _brier_score(v3_conf, v3_c1) if v3_c1 is not None else None
        v3_b5 = _brier_score(v3_conf, v3_c5) if v3_c5 is not None else None
        v3_b20 = _brier_score(v3_conf, v3_c20) if v3_c20 is not None else None

        # T+1 P&L placeholders (computed in aggregate later)
        daily = DailyResult(
            date=d,
            pair=pair,
            spot=spot,
            v2_composite=v2,
            v3_composite=v3,
            v2_predicted=v2_pred,
            v3_predicted=v3_pred,
            realized_t1=rt1,
            realized_t5=rt5,
            realized_t20=rt20,
            v2_correct_t1=v2_c1,
            v2_correct_t5=v2_c5,
            v2_correct_t20=v2_c20,
            v3_correct_t1=v3_c1,
            v3_correct_t5=v3_c5,
            v3_correct_t20=v3_c20,
            v2_brier_t1=v2_b1,
            v2_brier_t5=v2_b5,
            v2_brier_t20=v2_b20,
            v3_brier_t1=v3_b1,
            v3_brier_t5=v3_b5,
            v3_brier_t20=v3_b20,
            v2_pnl_t1=0.0,
            v3_pnl_t1=0.0,
        )
        daily_results.append(daily)

    # Simulate P&L
    v2_pnls, v2_trades = _simulate_pnl(v2_composites, spots, holding_days=1)
    v3_pnls, v3_trades = _simulate_pnl(v3_composites, spots, holding_days=1)

    for i, daily in enumerate(daily_results):
        daily.v2_pnl_t1 = v2_pnls[i]
        daily.v3_pnl_t1 = v3_pnls[i]

    # Compute stats
    def _build_stats(model: str, composites: Sequence[float | None], trades: int) -> ModelStats:
        correct_t1 = [d for d in daily_results if getattr(d, f"{model}_correct_t1") is not None]
        correct_t5 = [d for d in daily_results if getattr(d, f"{model}_correct_t5") is not None]
        correct_t20 = [d for d in daily_results if getattr(d, f"{model}_correct_t20") is not None]

        acc_t1 = (
            sum(1 for d in correct_t1 if getattr(d, f"{model}_correct_t1"))
            / len(correct_t1)
            * 100.0
            if correct_t1
            else None
        )
        acc_t5 = (
            sum(1 for d in correct_t5 if getattr(d, f"{model}_correct_t5"))
            / len(correct_t5)
            * 100.0
            if correct_t5
            else None
        )
        acc_t20 = (
            sum(1 for d in correct_t20 if getattr(d, f"{model}_correct_t20"))
            / len(correct_t20)
            * 100.0
            if correct_t20
            else None
        )

        briers_t1 = [
            getattr(d, f"{model}_brier_t1")
            for d in daily_results
            if getattr(d, f"{model}_brier_t1") is not None
        ]
        briers_t5 = [
            getattr(d, f"{model}_brier_t5")
            for d in daily_results
            if getattr(d, f"{model}_brier_t5") is not None
        ]
        briers_t20 = [
            getattr(d, f"{model}_brier_t20")
            for d in daily_results
            if getattr(d, f"{model}_brier_t20") is not None
        ]

        mean_b1 = sum(briers_t1) / len(briers_t1) if briers_t1 else None
        mean_b5 = sum(briers_t5) / len(briers_t5) if briers_t5 else None
        mean_b20 = sum(briers_t20) / len(briers_t20) if briers_t20 else None

        pnls = v2_pnls if model == "v2" else v3_pnls
        total_pnl = sum(pnls)
        sharpe = _compute_sharpe(pnls)
        mdd = _compute_max_drawdown(pnls)

        signal_days = sum(1 for c in composites if c is not None)

        return ModelStats(
            model=model,
            pair=pair,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_days=len(daily_results),
            signal_days=signal_days,
            accuracy_t1=acc_t1,
            accuracy_t5=acc_t5,
            accuracy_t20=acc_t20,
            mean_brier_t1=mean_b1,
            mean_brier_t5=mean_b5,
            mean_brier_t20=mean_b20,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe,
            max_drawdown_pct=mdd,
            num_trades=trades,
        )

    stats_v2 = _build_stats("v2", v2_composites, v2_trades)
    stats_v3 = _build_stats("v3", v3_composites, v3_trades)

    if verbose:
        logger.info(
            "%s v2 stats: acc_t1=%s acc_t5=%s P&L=%.2f Sharpe=%s MDD=%s",
            pair,
            stats_v2.accuracy_t1,
            stats_v2.accuracy_t5,
            stats_v2.total_pnl,
            stats_v2.sharpe_ratio,
            stats_v2.max_drawdown_pct,
        )
        logger.info(
            "%s v3 stats: acc_t1=%s acc_t5=%s P&L=%.2f Sharpe=%s MDD=%s",
            pair,
            stats_v3.accuracy_t1,
            stats_v3.accuracy_t5,
            stats_v3.total_pnl,
            stats_v3.sharpe_ratio,
            stats_v3.max_drawdown_pct,
        )

    return daily_results, stats_v2, stats_v3


def run_backtest(
    pair: str | None,
    start_date: date,
    end_date: date,
    verbose: bool = False,
    output_dir: str | None = None,
) -> None:
    """Run backtest comparison and save results."""
    pairs = [pair] if pair else ["EURUSD", "USDJPY", "USDINR"]

    all_daily: list[DailyResult] = []
    all_stats: list[ModelStats] = []

    for p in pairs:
        try:
            daily, stats_v2, stats_v3 = _run_backtest_for_pair(
                p, start_date, end_date, verbose=verbose
            )
            all_daily.extend(daily)
            all_stats.append(stats_v2)
            all_stats.append(stats_v3)
        except Exception as exc:
            logger.error("Backtest failed for %s: %s", p, exc)

    if not all_daily:
        logger.error("No backtest results generated.")
        return

    # Output directory
    out = (
        Path(output_dir)
        if output_dir
        else Path(__file__).resolve().parent.parent.parent / "backtest_results"
    )
    out.mkdir(parents=True, exist_ok=True)
    tag = f"{start_date.isoformat()}_{end_date.isoformat()}"

    # CSV
    csv_path = out / f"backtest_daily_{tag}.csv"
    _write_daily_csv(all_daily, csv_path)
    logger.info("Daily CSV saved: %s", csv_path)

    # JSON stats
    json_path = out / f"backtest_stats_{tag}.json"
    stats_data = [asdict(s) for s in all_stats]
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(stats_data, fh, indent=2, default=str)
    logger.info("Stats JSON saved: %s", json_path)

    # Summary report
    report_path = out / f"backtest_report_{tag}.txt"
    _write_report(all_stats, report_path)
    logger.info("Report saved: %s", report_path)


def _write_daily_csv(daily_results: Sequence[DailyResult], path: Path) -> None:
    import csv

    fieldnames = [
        "date",
        "pair",
        "spot",
        "v2_composite",
        "v3_composite",
        "v2_predicted",
        "v3_predicted",
        "realized_t1",
        "realized_t5",
        "realized_t20",
        "v2_correct_t1",
        "v2_correct_t5",
        "v2_correct_t20",
        "v3_correct_t1",
        "v3_correct_t5",
        "v3_correct_t20",
        "v2_brier_t1",
        "v2_brier_t5",
        "v2_brier_t20",
        "v3_brier_t1",
        "v3_brier_t5",
        "v3_brier_t20",
        "v2_pnl_t1",
        "v3_pnl_t1",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for d in daily_results:
            w.writerow(asdict(d))


def _write_report(stats: Sequence[ModelStats], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("=" * 60 + "\n")
        fh.write("PAIR-SPECIFIC BACKTEST COMPARISON REPORT\n")
        fh.write("=" * 60 + "\n\n")
        for s in stats:
            fh.write(f"Model: {s.model.upper()}  Pair: {s.pair}\n")
            fh.write(f"  Period: {s.start_date} to {s.end_date}\n")
            fh.write(f"  Days: {s.total_days} (signal days: {s.signal_days})\n")
            fh.write(
                f"  T+1 Accuracy:  {s.accuracy_t1:.2f}%\n"
                if s.accuracy_t1
                else "  T+1 Accuracy:  N/A\n"
            )
            fh.write(
                f"  T+5 Accuracy:  {s.accuracy_t5:.2f}%\n"
                if s.accuracy_t5
                else "  T+5 Accuracy:  N/A\n"
            )
            fh.write(
                f"  T+20 Accuracy: {s.accuracy_t20:.2f}%\n"
                if s.accuracy_t20
                else "  T+20 Accuracy: N/A\n"
            )
            fh.write(
                f"  Mean Brier T+1:  {s.mean_brier_t1:.4f}\n"
                if s.mean_brier_t1
                else "  Mean Brier T+1:  N/A\n"
            )
            fh.write(
                f"  Mean Brier T+5:  {s.mean_brier_t5:.4f}\n"
                if s.mean_brier_t5
                else "  Mean Brier T+5:  N/A\n"
            )
            fh.write(
                f"  Mean Brier T+20: {s.mean_brier_t20:.4f}\n"
                if s.mean_brier_t20
                else "  Mean Brier T+20: N/A\n"
            )
            fh.write(f"  Total P&L:     ${s.total_pnl:,.2f}\n")
            fh.write(
                f"  Sharpe Ratio:  {s.sharpe_ratio:.3f}\n"
                if s.sharpe_ratio
                else "  Sharpe Ratio:  N/A\n"
            )
            fh.write(
                f"  Max Drawdown:  {s.max_drawdown_pct:.2f}%\n"
                if s.max_drawdown_pct
                else "  Max Drawdown:  N/A\n"
            )
            fh.write(f"  Num Trades:    {s.num_trades}\n")
            fh.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pair-specific backtest engine")
    parser.add_argument("--pair", choices=("EURUSD", "USDJPY", "USDINR"), help="Pair to backtest")
    parser.add_argument("--all", action="store_true", help="Backtest all pairs")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--output-dir", help="Output directory for results")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    pair = None if args.all else args.pair
    if not pair and not args.all:
        parser.error("Specify --pair or --all")

    run_backtest(
        pair=pair,
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        verbose=args.verbose,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
