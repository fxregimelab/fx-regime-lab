# vol_pipeline.py
# Phase 1: CME CVOL implied vol — extend with CME EOD REST when CME_API_KEY is set.

from __future__ import annotations

import os
import sys


"""
CME CVOL implied volatility Pipeline.

Execution context:
- Called by run.py as STEP 4 (vol)
- Depends on: inr_pipeline.py
- Outputs: Supabase signals table (vol signals) + data/vol_latest.csv if applicable
- Next step: oi_pipeline.py
- Blocking: YES — pipeline halts on failure

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""


def main() -> None:
    key = os.environ.get("CME_API_KEY")
    if not key:
        print("  vol_pipeline: CME_API_KEY not set — skipping CVOL fetch (Phase 1)")
        return
    print("  vol_pipeline: CME key present — CVOL EOD integration pending (Phase 1)")


if __name__ == "__main__":
    main()
    sys.exit(0)
