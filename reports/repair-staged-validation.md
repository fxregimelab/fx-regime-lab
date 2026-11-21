# Staged validation repair handoff

Date: 2026-09-27

Source revision: `9fa150538d08ab5a2a6c587976552944f47a724d`

Scope: P01 and staged-path parity for V01 through V05

## Result

The staged validator now evaluates persisted published calls instead of inspecting an in-memory fake. `WriterPort` has explicit read methods for published calls and their current evaluation. The production adapter delegates those reads to `src.db.writer`; the fake assigns deterministic persisted IDs and exposes the same read contract.

- Every evaluated payload carries the persisted `call_id`. A missing ID, duplicate call IDs for the same pair and date, or a current evaluation linked to another or unknown call ID fails closed with no write.
- Validation uses only the published `predicted_direction`. It does not substitute `rate_signal`.
- Staged T+5 and T+20 calculations call `src.validation.calculator.calculate_horizon`, so live, replay and staged paths share direction, deadband, Brier, neutral-abstention and signed cost behavior.
- Spot selection is exact-date. A nearby later bar is not used, and a horizon is not evaluated before it matures even when the snapshot contains a future bar.
- A later horizon carries all earlier T+5 fields and the original `call_id`. A repeated run with both horizons already present makes no new validation write.
- The required read methods are abstract. A legacy writer without the published-call reader raises instead of returning an empty successful validation result.

GitNexus reported LOW risk for `ValidateStage`, LOW with an interface-dispatch lower bound for `ProductionWriterPort`, MEDIUM with the same lower bound for `FakeWriterPort`, and HIGH risk for `WriterPort` itself: 24 affected symbols and 15 direct dependants. The direct implementation points were the production adapter, fake and one test-only subclass, all covered by the staged gate. The final repository-wide unstaged scan reported HIGH risk across 24 shared-worktree files, 242 symbols and seven flows; that result also includes concurrent validation, aggregate, writer and documentation repairs outside this packet.

## Files changed

- `pipeline/src/staged/stages/validate_stage.py`
- `pipeline/src/staged/ports.py`
- `pipeline/src/staged/adapters/writer.py`
- `pipeline/src/staged/fakes.py`
- `pipeline/tests/test_staged_validation.py` (new)
- `pipeline/tests/test_staged_adapters.py`
- `pipeline/tests/test_staged_ports.py`
- `pipeline/tests/test_staged_fakes.py`

## Verification

From `D:\Projects\fxregimelab\pipeline`:

```text
node ../scripts/repair/verify-pytest.mjs tests/test_staged_validation.py tests/test_staged_adapters.py tests/test_staged_ports.py tests/test_staged_fakes.py tests/test_staged_orchestrator.py tests/test_staged_multi_pair.py tests/test_staged_eurusd_happy_path.py
38 passed in 36.13s
REPAIR_PYTEST_VERIFIED

ruff check src/staged/stages/validate_stage.py src/staged/ports.py src/staged/adapters/writer.py src/staged/fakes.py tests/test_staged_validation.py tests/test_staged_adapters.py tests/test_staged_ports.py tests/test_staged_fakes.py
All checks passed!

mypy src/staged/stages/validate_stage.py src/staged/ports.py src/staged/adapters/writer.py src/staged/fakes.py tests/test_staged_validation.py tests/test_staged_adapters.py tests/test_staged_ports.py tests/test_staged_fakes.py tests/test_staged_orchestrator.py tests/test_staged_multi_pair.py tests/test_staged_eurusd_happy_path.py
Success: no issues found in 11 source files

git diff --check
No whitespace errors. Git printed CRLF-to-LF warnings for concurrently edited `pipeline/src/db/writer.py` and `pipeline/tests/test_writer.py`; neither file belongs to this packet.
```

The tests cover the real production reader delegation, deterministic fake IDs, mirrored bullish and bearish moves, a flat deadband case, a correct direction that loses after the explicit USD/INR cost assumption, neutral abstention, exact published direction, immature calls, exact-date missing spots, T+5 preservation during T+20, repeated runs, missing IDs and both forms of ambiguous call linkage.

## Limits

- No staged feature flag was enabled. No database, production service, deployment, historical ledger, Docker runtime or Hermes gateway was touched.
- The production read adapter is tested with public writer functions mocked. A real local database rehearsal, schema compatibility and append-only transaction behavior belong to the writer and migration repair.
- Evaluation-version filtering and atomic versioned writes remain the canonical writer's responsibility. This adapter deliberately delegates to that boundary rather than reproducing its policy.
- The shared snapshot must contain the exact call-date and horizon-date spots. This repair rejects missing history; it does not fetch missing bars or establish their publication-time availability.
- Weekend-only maturity remains the existing `add_trading_days` contract. Holiday calendars, delayed bars and tradability are still open under V08.
- The explicit cost values remain research assumptions, not observed fills.
- Local parity tests do not prove deployed scheduler behavior, production permissions, historical reconciliation or forecasting performance.
