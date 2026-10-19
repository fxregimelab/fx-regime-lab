"""Run the dense walk-forward research harness over all available M15 history.

Research only: reads CSVs, writes a report, never touches the broker.

Usage (from pipeline/):
    .\\.venv\\Scripts\\python.exe scripts\\backtest_dense.py
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.paper.backtest.data import DEFAULT_DATA_DIR, PAIRS, load_series
from src.paper.backtest.dense import DenseConfig, run_walk_forward
from src.paper.backtest.dense_report import render_markdown, summary

REPORT_DIR = Path(__file__).resolve().parents[2] / "reports" / "desk" / "research"


def main() -> int:
    cfg = DenseConfig()
    rows = []
    for pair in PAIRS:
        series = load_series(pair, "m15", data_dir=DEFAULT_DATA_DIR)
        print(f"{pair}: {len(series)} M15 bars {series.first} -> {series.last}")
        result = run_walk_forward(pair, list(series.bars), cfg=cfg)
        row = summary(result)
        rows.append(row)
        print(
            f"  trades={row['trades']} ({row['trades_per_week']}/wk) "
            f"win={row['win_rate']:.1%} exp={row['expectancy_r']:+.3f}R "
            f"net={row['total_net_r']:+.2f}R "
            f"unconditional={row['unconditional_expectancy_r']:+.3f}R"
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_by": "scripts/backtest_dense.py",
        "config": asdict(cfg),
        "pairs": rows,
    }
    (REPORT_DIR / "dense.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (REPORT_DIR / "dense.md").write_text(
        render_markdown(
            rows,
            title="Dense walk-forward research",
            config=asdict(cfg),
        ),
        encoding="utf-8",
    )
    print(f"wrote {REPORT_DIR / 'dense.json'} and dense.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
