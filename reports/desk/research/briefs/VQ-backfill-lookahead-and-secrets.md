# Brief — VQ: validation backfill lookahead fix + security sweep

**Status:** queued (spawn with inline copy of this brief)
**Kind:** implementer
**Files:** `pipeline/src/backfill/batch_validation_backfill.py` + focused test additions
(`pipeline/tests/integration/test_validation_backfill.py` adapt if needed); repo-root
`scripts/apply_phase1_migrations.py`, `scripts/recompute_validation_stats.py`,
`scripts/backfill_validation_net.sql`.

## Task 1 — backward-only spot resolution

`_get_spot` in `batch_validation_backfill.py` (~L102-116) still forward-fills (uses FUTURE
prices within a window) — the same defect family VR1 fixed in
`pipeline/scripts/_bulk_backfill_validation_rest.py` (commit `bf12c0d`): exact match →
last observation ≤ target within a staleness bound → None; NEVER a future date. Port that
semantic here. First grep the callers/tests to confirm contracts
(`backfill_validation_for_call` is exercised by `pipeline/tests/integration/test_validation_backfill.py`);
keep the public API unchanged. Add focused tests proving: no future date ever used; exact
match preferred; None when nothing within bound.

## Task 2 — security sweep (repo-root scripts only; never print secrets)

- `scripts/apply_phase1_migrations.py:11` and `scripts/recompute_validation_stats.py:12`
  contain hardcoded credential fallbacks (`os.getenv("SUPABASE_DB_PASSWORD", "<literal>")`).
  Remove the literals; fail closed with a clear message when the env var is missing.
- `scripts/backfill_validation_net.sql`: still uses the wrong `predicted=actual` mapping and
  a divergent USDINR cost table; retire it (replace content with a comment pointing to the
  canonical repair path, or rename) — document the choice.
- Do NOT touch `scripts/backfill_validation_net.py` (already a fail-closed shim, `bf12c0d`).

## Constraints

No DB writes; read-only inspection allowed. Do not edit other agents' files
(`simulation_engine.py`, `orchestrator.py`, `signals/rate.py` + their tests are owned by
others); if full-suite failures appear only in files you did not touch, re-run once.
No commits/push/checkout/stash.

## Verify (from `pipeline\`)

Focused `-m pytest tests/integration/test_validation_backfill.py -q` + new tests; full
`-m pytest -q` (baseline 749); `-m ruff check .`; `-m mypy .`.

## Report

Per-item resolution, test names, exact commands + results, residual risks, manual callers
list (GitNexus unavailable → risk UNKNOWN).
