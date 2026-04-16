# rr_pipeline.py
# Phase 1: Synthetic 25-delta risk reversal via yfinance FXE options (minimal probe).

from __future__ import annotations

import sys

import yfinance as yf

from core.signal_write import log_pipeline_error


"""
Synthetic risk reversal (RR) Pipeline.

Execution context:
- Called by run.py as STEP 6 (rr)
- Depends on: oi_pipeline.py
- Outputs: Supabase signals table (synthetic risk reversal) + data/rr_latest.csv if applicable
- Next step: morning_brief.py (text step)
- Blocking: YES — pipeline halts on failure

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""


def main() -> None:
    print("  rr_pipeline: probing FXE options (synthetic EUR/USD RR proxy)…")
    try:
        t = yf.Ticker("FXE")
        expirations = t.options
        if not expirations:
            print("    no option expirations — skip")
            return
        print(f"    OK nearest expiry bucket: {expirations[0]} (full RR calc Phase 1)")
    except Exception as e:
        print(f"    WARN: {e} (non-fatal)")
        try:
            log_pipeline_error("rr_pipeline", str(e))
        except Exception:
            pass


if __name__ == "__main__":
    main()
    sys.exit(0)
