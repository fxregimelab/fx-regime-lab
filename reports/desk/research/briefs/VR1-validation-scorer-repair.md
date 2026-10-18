# Brief — VR1: validation scorer repair (code only, NO DB writes)

**Status:** queued (dispatch when an editing slot frees)
**Kind:** implementer
**Files:** `pipeline/scripts/_bulk_backfill_validation_rest.py`,
new `pipeline/scripts/audit_validation_rescore.py`,
new `pipeline/tests/test_bulk_backfill_validation_rest.py`,
repo-root `scripts/backfill_validation_net.py` (security/mapping repair only).

## Context (verified read-only 2026-10-18)

- `_load_prices()` in `_bulk_backfill_validation_rest.py` paginates `historical_prices`
  WITHOUT `.eq("pair", pair)` — every pair dict receives ALL pairs' rows (last id wins per date).
  This contaminated live `validation_log` rows: identical impossible values across pairs
  (2026-05-20 EURUSD/USDINR `−5057.66` bps; 05-21 all three `−5033.42`; 05-24/25 all three
  `+44127.94/+44018.52`; 2003-12-01 EURUSD `−36218.27`). Several are non-superseded → feed
  live stats.
- `_get_spot()` forward-fills (uses FUTURE dates ≤10 days) — lookahead in scoring.
- Mixed scorer generations left flag mismatches: 194 recon rows BULLISH with positive gross but
  `correct_t5` not true; 129 rows BEARISH with negative gross but not true; 4 live rows likewise.
- Sanctioned correction paths: `writer.bulk_rewrite_validation_rows` (supersede + insert),
  `writer.supersede_validation_row`, `writer.update_validation_log_row`. Trigger
  `protect_immutable_validation` blocks T+5 column changes on scored rows.
- Repo-root `scripts/backfill_validation_net.py` line 11 hardcodes a production DB password and
  uses `predicted=="UP"/"DOWN"` (calls are BULLISH/BEARISH) — wrong mapping + leaked secret.

## Required work

1. **Fix `_load_prices()`**: filter `.eq("pair", pair)`; keep pagination. Result: per-pair
   dicts contain only that pair's rows.
2. **Fix `_get_spot()`**: previous-available only (backward fill). Remove forward fill entirely
   (no lookahead). Return None when nothing ≤ target date.
3. **Tests** (`tests/test_bulk_backfill_validation_rest.py`, fake Supabase client / monkeypatch):
   pair filtering honored; spot resolution never uses dates > target; `_build_rows` computes
   `compute_horizon_metrics` with correct s0/s5/s20; rows for a date whose T+5 is in the future
   relative to `as_of` are omitted as before.
4. **New `scripts/audit_validation_rescore.py`** (read-only):
   - Loads non-superseded `validation_log` rows; loads `historical_prices` per pair (properly
     filtered); recomputes T5/T20 with `compute_horizon_metrics` (current canonical scorer).
   - Diffs stored vs recomputed: gross bps, correct flags, net bps, cost bps, brier.
   - Categorizes: `cross_pair_corrupt` (recomputed-vs-stored gross mismatch AND |stored| implausibly
     large, e.g. |gross|>2000 bps T5 or >3000 T20), `flag_mismatch`, `net_mismatch`, `brier_mismatch`,
     `cost_mismatch`, `no_prices` (dates beyond price coverage).
   - Prints per-category counts + worst 20 rows; writes a JSON+Markdown report to
     `reports/desk/research/` when `--out` given. **Never writes to the DB.**
   - Pure comparison/classification function unit-tested in the same test file (synthetic rows).
5. **Root `scripts/backfill_validation_net.py`**: remove the hardcoded password (require env,
   fail closed with a clear message); fix the mapping to use `src/validation/calculator.py`
   semantics (BULLISH/BEARISH/NEUTRAL) or, if obsolete, convert to a shim that refuses to run and
   points to the canonical rescore path. No DB writes from this task.

## Constraints

- NO DB writes of any kind. Read-only DB access allowed for inspection.
- Do not edit `backfill/simulation_engine.py`, `db/repositories/regime_call.py`,
  `paper/spec_bundle.py`, or their tests (other agents edit those).
- Concurrency: other agents may run full suites mid-edit; if a full-suite failure appears only in
  files you did not touch, re-run once before reporting.
- No git commits/push/checkout/stash.

## Verify (from `pipeline\`)

`.venv\Scripts\python.exe -m pytest tests/test_bulk_backfill_validation_rest.py -q`;
full `-m pytest -q`; `-m ruff check .`; `-m mypy .`.

## Report

Per-item resolution, test names, exact commands + results, residual risks
(e.g. live-window price coverage gap — `historical_prices` is stale since 2026-06-29 until the
coordinator tops it up), manual callers list (GitNexus broken → risk UNKNOWN).
