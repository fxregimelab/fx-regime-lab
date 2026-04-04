# vol_pipeline.py
# Phase 1: CME CVOL implied vol — extend with CME EOD REST when CME_API_KEY is set.

from __future__ import annotations

import os
import sys


def main() -> None:
    key = os.environ.get("CME_API_KEY")
    if not key:
        print("  vol_pipeline: CME_API_KEY not set — skipping CVOL fetch (Phase 1)")
        return
    print("  vol_pipeline: CME key present — CVOL EOD integration pending (Phase 1)")


if __name__ == "__main__":
    main()
    sys.exit(0)
