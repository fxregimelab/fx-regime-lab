# scripts/pipeline_merge.py
# Phase 1: thin wrapper that invokes pipeline.merge_main() as a standalone
# subprocess so run.py's script-level dedup does not skip the merge step
# (fx already executed pipeline.py; a different script name keeps merge alive).

from __future__ import annotations

import os
import sys

# Ensure repo root is importable when invoked from run.py via subprocess
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from pipeline import merge_main


def main() -> None:
    try:
        ok = merge_main()
        if ok is False:
            sys.exit(1)
    except Exception as e:
        print(f"  pipeline_merge: unexpected error — {e}")
        try:
            from core.signal_write import log_pipeline_error
            log_pipeline_error("pipeline_merge", str(e), notes="wrapper")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
    sys.exit(0)
