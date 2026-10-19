"""Univariate edge scan: does any feature separate winners from losers?

Research diagnostic only. For a fixed trade geometry it builds the directional
feature matrix, pools long and short rows, and reports, per feature:

- Spearman information coefficient (pooled and per side)
- mean net R in the top and bottom decile
- the top-decile mean per calendar year (stability)

If no feature produces a stable spread wider than the ~0.05R cost drag, no model
built on these features can be expected to trade profitably.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeAlias

import numpy as np
import numpy.typing as npt
from scipy.stats import spearmanr

from src.paper.backtest.data import DEFAULT_DATA_DIR, PAIRS, load_series
from src.paper.backtest.dense import (
    DIRECTIONAL_FEATURES,
    FEATURE_NAMES,
    DenseConfig,
    FeatureFrame,
    build_features,
    build_labels,
    directional_matrix,
)
from src.paper.features import OHLCBar

Array: TypeAlias = npt.NDArray[np.float64]
REPORT_DIR = Path(__file__).resolve().parents[2] / "reports" / "desk" / "research"


def _signed_features(base: Array) -> tuple[Array, Array]:
    long_view = directional_matrix(base)
    mask = np.array([name in DIRECTIONAL_FEATURES for name in FEATURE_NAMES])
    short_view: Array = np.where(mask, -long_view, long_view)
    return long_view, short_view


def scan_pair(pair: str, bars: list[OHLCBar], cfg: DenseConfig) -> dict[str, Any]:
    frame: FeatureFrame = build_features(bars, pair, cfg=cfg)
    long_r, short_r, _, _ = build_labels(bars, frame, pair, cfg=cfg)
    valid = frame.valid & np.isfinite(long_r) & np.isfinite(short_r)
    index = np.flatnonzero(valid)

    long_features, short_features = _signed_features(frame.base)
    features = np.vstack([long_features[valid], short_features[valid]])
    target = np.concatenate([long_r[valid], short_r[valid]])
    sides = np.concatenate([np.ones(index.size), -np.ones(index.size)])
    years = np.concatenate([
        np.array([frame.times[i].year for i in index]),
        np.array([frame.times[i].year for i in index]),
    ])
    return _scan_matrix(pair, features, target, sides, years)


def _scan_matrix(
    pair: str,
    features: Array,
    target: Array,
    sides: Array,
    years: Array,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for k, name in enumerate(FEATURE_NAMES):
        column = features[:, k]
        finite = np.isfinite(column)
        if finite.sum() < 100 or np.std(column[finite]) == 0.0:
            continue
        x = column[finite]
        y = target[finite]
        side = sides[finite]
        year = years[finite]

        ic = float(spearmanr(x, y).statistic)
        long_mask = side > 0
        short_mask = side < 0
        ic_long = (
            float(spearmanr(x[long_mask], y[long_mask]).statistic)
            if long_mask.sum() > 100 else float("nan")
        )
        ic_short = (
            float(spearmanr(x[short_mask], y[short_mask]).statistic)
            if short_mask.sum() > 100 else float("nan")
        )

        q10, q90 = np.quantile(x, [0.10, 0.90])
        top = y[x >= q90]
        bottom = y[x <= q10]

        per_year: dict[str, float] = {}
        for value in sorted(set(year.tolist())):
            mask = year == value
            if mask.sum() < 200:
                continue
            top_year = y[mask & (x >= q90)]
            if top_year.size:
                per_year[str(int(value))] = round(float(np.mean(top_year)), 4)

        rows.append(
            {
                "feature": name,
                "ic": round(ic, 5),
                "ic_long": round(ic_long, 5) if ic_long == ic_long else None,
                "ic_short": round(ic_short, 5) if ic_short == ic_short else None,
                "bottom_decile_r": round(float(np.mean(bottom)), 5),
                "top_decile_r": round(float(np.mean(top)), 5),
                "spread_r": round(float(np.mean(top) - np.mean(bottom)), 5),
                "top_decile_by_year": per_year,
                "n": int(finite.sum()),
            }
        )
    rows.sort(key=lambda row: abs(float(row["ic"])), reverse=True)
    return {"pair": pair, "features": rows, "n_rows": int(target.shape[0])}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="h1")
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--stop", type=float, default=2.5)
    parser.add_argument("--target", type=float, default=1.5)
    parser.add_argument("--hold", type=int, default=48)
    parser.add_argument("--tag", default="edge_scan")
    args = parser.parse_args()

    cfg = DenseConfig(
        stop_atr_mult=args.stop, target_r=args.target, max_hold_bars=args.hold
    )
    start = datetime.fromisoformat(args.start).replace(tzinfo=UTC)
    series: dict[str, list[OHLCBar]] = {
        pair: [
            b
            for b in load_series(pair, args.timeframe, data_dir=DEFAULT_DATA_DIR).bars
            if b.timestamp >= start
        ]
        for pair in PAIRS
    }

    results = [scan_pair(pair, series[pair], cfg) for pair in PAIRS]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"{args.tag}.json").write_text(
        json.dumps(
            {
                "timeframe": args.timeframe,
                "start": args.start,
                "stop_atr_mult": args.stop,
                "target_r": args.target,
                "max_hold_bars": args.hold,
                "pairs": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    for result in results:
        print(f"\n{result['pair']} ({result['n_rows']} directional rows)")
        header = (
            f"{'feature':16s} {'IC':>7s} {'IC-L':>7s} {'IC-S':>7s} "
            f"{'bottom10':>9s} {'top10':>9s} {'spread':>7s}  top10 by year"
        )
        print(header)
        for row in result["features"][:12]:
            years = " ".join(
                f"{y}:{v:+.3f}" for y, v in row["top_decile_by_year"].items()
            )
            print(
                f"{row['feature']:16s} {float(row['ic']):>7.4f} "
                f"{_fmt(row['ic_long']):>7s} {_fmt(row['ic_short']):>7s} "
                f"{float(row['bottom_decile_r']):>9.4f} "
                f"{float(row['top_decile_r']):>9.4f} "
                f"{float(row['spread_r']):>7.4f}  {years}"
            )
    return 0


def _fmt(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):+.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
