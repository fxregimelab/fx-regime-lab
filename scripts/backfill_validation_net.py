#!/usr/bin/env python3
"""RETIRED shim — refuses to run.

The former ``backfill_validation_net.py`` backfilled ``validation_log`` net
columns over a direct psycopg2 connection. It was retired (VR1, 2026-10-18)
because it:

* embedded a hardcoded production database credential (now removed — rotate
  that password if the file was ever shared);
* scored ``predicted == "UP"/"DOWN"``, but the canonical call vocabulary is
  BULLISH / BEARISH / NEUTRAL (``src/validation/calculator.py``), so it would
  have marked every directional row incorrect;
* used a divergent cost table (USDINR 1.0 bps vs the canonical 10.0 bps);
* bypassed the sanctioned writer API and the append-only ledger protocol
  (all DB writes must go through ``pipeline/src/db/writer.py``).

Canonical replacement paths:

* Per-row scoring math: ``pipeline/src/validation/calculator.py``
  (``compute_horizon_metrics``).
* Read-only diff audit before any correction:
  ``pipeline/scripts/audit_validation_rescore.py``.
* Sanctioned corrections (supersede + append corrected rows):
  ``pipeline/src/db/writer.py`` — ``bulk_rewrite_validation_rows``,
  ``supersede_validation_row``, ``update_validation_log_row``.

This shim performs no database access and always exits non-zero.
"""

from __future__ import annotations

import sys

_MESSAGE = (
    "backfill_validation_net.py is RETIRED and refuses to run.\n"
    "It had a wrong prediction mapping (UP/DOWN vs BULLISH/BEARISH/NEUTRAL), "
    "a divergent cost table, and a leaked credential.\n"
    "Use the canonical paths instead:\n"
    "  - recompute math:  pipeline/src/validation/calculator.py:compute_horizon_metrics\n"
    "  - read-only audit: pipeline/scripts/audit_validation_rescore.py\n"
    "  - corrections:     pipeline/src/db/writer.py "
    "(bulk_rewrite_validation_rows / supersede_validation_row / update_validation_log_row)\n"
)


def main() -> int:
    print(_MESSAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
