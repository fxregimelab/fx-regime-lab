# Validation price evidence repair

Leaf 11.1 now evaluates each published call from its own immutable publication snapshot and exact stored historical closes. The shared evaluator is the only scoring implementation used by the live engine, single-call replay and batch replay.

## What changed

- `EVALUATION_VERSION` is `publication-snapshot-v2`. Older evaluation versions remain separate and are not reinterpreted.
- `src.validation.evaluator.evaluate_call` validates a positive integer call ID, the three locked pairs, strict calendar dates, published direction and confidence, current-version existing rows, publication signal identity, and exact horizon price identity.
- Entry evidence comes only from `get_publication_signal_for_call(call_id)`. Endpoint evidence comes only from `get_exact_historical_price_for_date(pair, date)`. Missing or invalid evidence leaves the horizon unavailable.
- Completed horizons and their nested evidence are copied into a detached payload. A partial retry reads only the missing horizon. A complete or not-yet-due call performs no price or publication-evidence reads.
- Reader exceptions propagate. Invalid returned evidence fails closed with a warning.
- Live validation visits the complete history for EURUSD, USDJPY and USDINR. The batch replay also visits all three complete histories.
- The single and batch replay paths no longer use yfinance, mutable signal rows, nearest-date prices, raw PostgreSQL connections or unverified TLS.

## Evidence

- Exact G1 wrapper: `63 passed in 2.43s`, followed by `REPAIR_PYTEST_VERIFIED`.
- Ruff on all owned Python source and tests: `All checks passed!`.
- Full pipeline MyPy: `Success: no issues found in 175 source files`.
- `git diff --check` on all owned files: exit 0.
- Negative control: two same-date calls with publication spots 1.20 and 0.80 are scored against the same exact 1.00 endpoint. The test asserts opposite signed returns and fails if the old mutable signal reader is called.
- GitNexus impact checks reported CRITICAL reach for the public engine and replay entry points. The index included unrelated process names, so compatibility was checked with preserved public entry-point signatures and the scoped regression suite. The required pre-commit change scan was also run; it reported the shared checkout's 61-file repair wave as CRITICAL, not this leaf in isolation.

## Verification boundary

These checks prove the pure evaluator and the owned live/replay adapters against local fixtures. The parent still owns independent gate re-verification, full-pipeline checks, database migration integration and any deployed acceptance. No database write, production call, credential use, notification, commit or deployment was performed by this leaf.
