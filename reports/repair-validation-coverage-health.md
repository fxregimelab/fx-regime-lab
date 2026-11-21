# Validation coverage health repair

Source revision: `9fa150538d08ab5a2a6c587976552944f47a724d`

## Result

Live and staged validation now use one coverage report for the complete returned
published-call population. The report keeps the existing row-list interface for
`ValidateStage.run` and exposes detailed health through `run_with_report` and
`engine.run_validation`.

The report counts every returned call, every T+5 or T+20 horizon mature on the
scan date, and every structurally valid completed horizon. Missing publication
entry evidence, missing exact endpoint closes, duplicate call IDs, invalid call
identity, future-dated calls, malformed current-version records, and future
completed horizons cannot produce a healthy result. Neutral calls still count as
completed when a valid realized return exists, even though directional accuracy
and Brier fields remain null.

Missing locked-pair definitions are recorded as a coverage limitation rather
than as invalid published calls. The limitation makes the report unhealthy while
leaving `invalid_calls` as an honest count of malformed calls. Successful scans
always include `validation_scan_completed`; an empty scan also includes
`no_mature_horizons`.

Completed publication-snapshot-v2 rows are counted only when their call ID,
evaluation version, finite returns, publication entry evidence, and exact
horizon-price evidence match. A valid completed row is not refetched or
rewritten. Reader and persistence failures propagate to the caller, so the
pipeline cannot convert an unavailable dependency into a healthy report.

`ValidationRunResult.healthy` also rejects malformed counters: booleans,
non-integers, negatives, more completed horizons than due horizons, more than two
due horizons per scanned call, or more invalid calls than scanned calls.

## Verification

- Required repair gate from `pipeline`:
  `node ../scripts/repair/verify-pytest.mjs tests/test_validation_coverage_health.py tests/test_validation_backlog.py tests/test_staged_validation.py tests/test_validation_price_evidence.py`
  — `57 passed`, `REPAIR_PYTEST_VERIFIED`.
- Adjacent engine and scheduler checks:
  `pytest -q tests/test_validation_engine.py tests/test_scheduler_health_contract.py tests/test_run_pipeline_flags.py`
  — `73 passed`.
- Scoped Ruff on the three implementation files and three owned test files —
  clean.
- Full pipeline mypy: `mypy .` — no issues in 183 source files.

## Limits

These are local deterministic checks. They do not prove production database
contents, real price availability, Prefect execution, deployment, or observed
rolling accuracy. No credentials, provider AI, alerts, production database,
Docker, Hermes gateway, commit, or deployment were used. The Hermes MCP server
configuration was not changed.

GitNexus reported `run_validation` as CRITICAL with 73 impacts, but its results
included unrelated same-name symbols and cross-language UI code. The new
untracked coverage symbols were absent from the index and returned UNKNOWN.
The implementation therefore preserved the public function names and caller
shapes and used focused live, staged, engine, and scheduler regression checks.
The final repository-wide change scan also reported CRITICAL because the shared
checkout contains 67 changed files and 463 indexed symbols across all repair
leaves; it did not isolate this seven-file leaf.
