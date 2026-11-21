# Staged validation price evidence repair

Date: 27 September 2026  
Source revision: `9fa1505` on `codex/frontend`  
Scope: leaf 11.2 staged validation files and staged tests only

## Result

`ValidateStage` now calls `src.validation.evaluator.evaluate_call` for every published call. It supplies the exact immutable publication signal and exact dated historical close through `WriterPort`. The ingestion snapshot remains an orchestrator argument but is not used as validation price evidence.

The production adapter delegates to `src.db.writer.get_publication_signal_for_call` and `src.db.writer.get_exact_historical_price_for_date`. The fake records both read paths, returns publication evidence only for atomic publications, and returns historical evidence only after a test explicitly seeds the exact pair and date. Its current-evaluation reader filters to `publication-snapshot-v2` and ignores superseded rows, matching production cohort selection.

Covered cases include:

- two same-date call versions with different publication spots and different returns;
- T+5 evidence frozen while a later revision adds T+20;
- a completed retry that performs no entry or endpoint reads;
- a legacy call with no publication evidence remaining unavailable;
- an old backlog call evaluated from durable evidence with an empty recent ingestion snapshot;
- exact-date endpoint absence, v1/v2 coexistence, neutral scoring, immature calls, pair mismatch, and full-history reads.

## Verification

The exact leaf gate passed:

```text
88 passed in 24.94s
REPAIR_PYTEST_VERIFIED
```

Command:

```text
cd pipeline
node ../scripts/repair/verify-pytest.mjs tests/test_staged_validation.py tests/test_staged_fakes.py tests/test_staged_adapters.py tests/test_staged_ports.py tests/test_staged_eurusd_happy_path.py tests/test_staged_multi_pair.py tests/test_staged_orchestrator.py tests/test_staged_shadow_runner.py tests/test_staged_publication_health.py
```

Additional scoped checks passed:

```text
python -m ruff check <owned staged source and test files>
All checks passed!

python -m mypy src/staged/stages/validate_stage.py src/staged/ports.py src/staged/adapters/writer.py src/staged/fakes.py
Success: no issues found in 4 source files
```

`git diff --check` reported no whitespace errors in the owned tracked files.

## Impact and limits

Before editing, GitNexus rated `ValidateStage` low risk, `FakeWriterPort` medium risk, and both `WriterPort` and `ProductionWriterPort` high risk. The interface had 15 direct dependants and three implementations, so all staged implementations and their owned contract tests were updated together.

The required post-change `gitnexus detect-changes` scan reported critical risk across the shared dirty checkout: 61 files, 413 symbols and 293 flows. That result covers all concurrent repair work in the checkout and is not a leaf-11.2-only score. This worker did not commit, deploy, contact providers, use credentials, or modify production data. Docker and heavier Hermes services were not required for these pure Python checks.

The passing local gate proves staged contract and adapter behavior. It does not prove production database contents or deployed runtime behavior; the parent integration review remains G2.
