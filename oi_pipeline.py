# oi_pipeline.py
# Phase 1: CME FX futures open interest delta — stub.

from __future__ import annotations

import sys


"""
CME FX open interest Pipeline.

Execution context:
- Called by run.py as STEP 5 (oi)
- Depends on: vol_pipeline.py
- Outputs: Supabase signals table (OI signals) + data/oi_latest.csv if applicable
- Next step: rr_pipeline.py
- Blocking: YES — pipeline halts on failure

DO NOT:
- Import other *_pipeline.py modules
- Use async/await
- Add CLI arguments (argparse, click, sys.argv)
- Hardcode dates, API keys, or file paths
- Use plain supabase insert — always upsert
"""


def main() -> None:
    print("  oi_pipeline: stub — implement CME OI scrape/API (Phase 1)")


if __name__ == "__main__":
    main()
    sys.exit(0)
