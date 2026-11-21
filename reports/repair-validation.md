# Validation repair handoff

Date: 2026-09-27

Branch: `repair/evidence-contracts`

Scope: V01, V02, V03 and V05 calculator, live validation, and two replay paths

## Result

The bounded local repair is implemented. Live validation, the per-call replay, and the batch replay now use one pure calculator.

- A call is scored only from its published `predicted_direction`. Missing or unknown direction is skipped; `rate_signal` is not a fallback.
- Raw market log return stays unchanged. Directional research payoff is `side * raw_return - explicit_pair_cost`, where side is +1 for bullish and -1 for bearish. `correct_net` means that payoff is positive.
- Directional moves inside the +/-5 bps deadband are incorrect. Their Brier outcome is the same boolean event used by accuracy.
- A neutral prediction is an abstention: correctness, Brier score, net payoff and net-positive status are null.
- Directional confidence must be present, finite and between 0 and 1. Prices must be finite and positive.
- Later-horizon writes carry every earlier horizon field, including net payoff and cost. A completed T+5 does not stop a mature T+20 calculation.
- Existing validation is reused only when `call_id` matches exactly. A different or missing association fails closed with no write.
- Replay prices must match the requested date exactly. Nearby past or future bars are no longer substituted.
- Batch replay no longer invents `live` or `v2` provenance and no longer writes with direct SQL; writes go through `src.db.writer`.

GitNexus reported HIGH risk for `run_validation` and HIGH/CRITICAL risk for its shared helpers because scheduler, replay, diagnostics and integration paths depend on them. Existing helper names remain as compatibility wrappers. The two replay entry points were LOW risk. The required post-change `gitnexus_detect_changes(scope="unstaged")` ran; the repository-wide shared worktree result was HIGH because it also included concurrent writer, aggregate, scheduler-adjacent and documentation changes. For this packet it identified the expected live-validation and replay processes.

## Files owned and changed

- `pipeline/src/validation/calculator.py` (new)
- `pipeline/src/validation/engine.py`
- `pipeline/src/backfill/validation_backfill.py`
- `pipeline/src/backfill/batch_validation_backfill.py`
- `pipeline/tests/test_validation_engine.py`
- `pipeline/tests/test_batch_validation_backfill.py` (new)
- `pipeline/tests/integration/test_validation_backfill.py`
- `pipeline/tests/integration/test_p0_validation_immutability.py`

## Verification

From `D:\Projects\fxregimelab\pipeline`:

```text
python -m pytest tests/test_validation_engine.py tests/test_batch_validation_backfill.py tests/integration/test_validation_backfill.py tests/integration/test_p0_validation_immutability.py -q
47 passed in 5.14s

python -m ruff check src/validation/engine.py src/validation/calculator.py src/backfill/validation_backfill.py src/backfill/batch_validation_backfill.py tests/test_validation_engine.py tests/test_batch_validation_backfill.py tests/integration/test_validation_backfill.py tests/integration/test_p0_validation_immutability.py
All checks passed!

python -m mypy src/validation/calculator.py src/validation/engine.py src/backfill/validation_backfill.py src/backfill/batch_validation_backfill.py
Success: no issues found in 4 source files

git diff --check
No output
```

The tests include opposing rate/final direction, mirrored bullish/bearish payoff, flat/deadband and cost-boundary cases, neutral abstention, invalid/missing probability, invalid price, exact-date replay, datetime normalization, T+5 then T+20 preservation, repeated runs, and ambiguous call identity.

## Limits and remaining work

- No database write, real pipeline run, historical reconciliation, release or deployment was performed.
- The local tests mock the writer. The checked-in migration history does not show the horizon-specific `log_return_net_bps_t5` and `log_return_net_bps_t20` columns already referenced by runtime code. Schema compatibility and a real local database rehearsal remain required before release.
- Current writer behavior can still prevent a new T+20 from being appended to an existing T+5 row. The writer/transaction repair is owned by the ledger packet; these tests verify the payload passed to that boundary.
- Historical records remain unchanged. Correcting them requires the versioned, append-only reconciliation in X01.
- Exact-date selection closes the nearby-bar substitution in these replay paths. Publication time, market calendars, delayed bars and tradability remain open under V08.
- Cost values are explicit research assumptions. They are not claimed as observed fills or empirical transaction-cost estimates.
- The staged validation class has separate arithmetic and was outside this packet's file ownership. Its parity must be handled in the staged-pipeline repair.
- The focused checks do not prove production schema, Supabase permissions, scheduler behavior, deployed output, or historical accuracy.
