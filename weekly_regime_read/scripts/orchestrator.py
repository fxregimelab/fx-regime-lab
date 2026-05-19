#!/usr/bin/env python3
"""
FX Regime Lab — Weekly Pipeline Orchestrator

Runs the deterministic data pipeline:
  1. data_fetcher  → writer_data_YYYYMMDD.json
  2. track_record  → track_record_YYYYMMDD.json
  3. charts        → charts/*.png

After this runs, the AI reads the output and writes the post.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WRR = ROOT / "weekly_regime_read"
DATA_FETCHER = WRR / "scripts" / "data_fetcher.py"
TRACK_RECORD = WRR / "scripts" / "track_record.py"
CHART_SCRIPT = ROOT / ".kimi/skills/fx-regime-lab-writer/scripts/generate_charts_v5.py"
OUTPUT_DIR = WRR / "output"
CHARTS_DIR = OUTPUT_DIR / "charts"


def run_command(cmd: list[str], label: str) -> bool:
    print(f"\n[{label}]...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in (result.stdout + result.stderr).splitlines():
        if line.strip():
            print(f"    {line}")
    if result.returncode != 0:
        print(f"  ERROR: {label} failed")
        return False
    return True


def run_pipeline() -> bool:
    # Step 1: data fetcher
    if not run_command(
        [sys.executable, str(DATA_FETCHER), "--output-dir", str(OUTPUT_DIR)],
        "Data Fetcher",
    ):
        return False

    # Step 2: track record
    if not run_command(
        [sys.executable, str(TRACK_RECORD)],
        "Track Record",
    ):
        return False

    # Step 3: charts
    if not run_command(
        [sys.executable, str(CHART_SCRIPT), "--output", str(CHARTS_DIR)],
        "Charts",
    ):
        return False

    print("\n=== Pipeline complete ===")
    print(f"  Data:      {OUTPUT_DIR}/writer_data_*.json")
    print(f"  Track:     {OUTPUT_DIR}/track_record_*.json")
    print(f"  Charts:    {CHARTS_DIR}/")
    return True


if __name__ == "__main__":
    ok = run_pipeline()
    sys.exit(0 if ok else 1)
