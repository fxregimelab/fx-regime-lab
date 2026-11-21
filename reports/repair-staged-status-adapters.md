# Staged signal persistence and status adapter repair — 27 September 2026

This leaf adds the two adapter contracts needed by the staged orchestrator. It does not run the production pipeline, write to the database, or send a real notification.

## Changes

`WriterPort` now accepts a `SignalRow`. The production adapter delegates that row unchanged to `src.db.writer.write_signal_row`; it contains no direct database access. The fake writer keeps detached snapshots and upserts retries by pair and date, so later mutation cannot change recorded fields or `data_quality_notes`.

`AlertPort` now accepts a date, `StageHealth`, and optional pair for non-OK stage status. The production adapter rejects `OK`, sends DEGRADED and FAILED notices through `send_slack_alert`, and includes the stage, pair, missing fields, and notes. It does not call the healthy heartbeat helper. Credential-shaped values, Slack webhook URLs, and raw exception details are removed from the notice. The fake records the full health object for assertions and follows the same `OK` rejection rule.

The existing `send_success`, `send_heartbeat`, and `send_low_dqs` signatures and behavior are unchanged. They remain the healthy-flow interfaces.

## Evidence

The leaf gate ran from `pipeline`:

```text
node ../scripts/repair/verify-pytest.mjs tests/test_staged_ports.py tests/test_staged_fakes.py tests/test_staged_adapters.py
21 passed
REPAIR_PYTEST_VERIFIED
```

The cases cover abstract-port implementations, production writer delegation, repeated signal writes, detached quality-note snapshots, DEGRADED and FAILED notices, missing fields and notes, secret and exception redaction, `OK` rejection, and proof that non-OK status does not call the healthy heartbeat helper.

Scoped Ruff passed all seven owned Python files. Scoped MyPy passed all seven with `--follow-imports=silent`. A full-import scoped MyPy attempt reached a concurrently owned `combine_stage_health` return-literal inference issue; the parent integration has since fixed it. This leaf did not edit `src/staged/contracts.py`. Git diff whitespace validation passed.

GitNexus classified `WriterPort` and `AlertPort` as MEDIUM risk with 15 impacted symbols each. The two writer implementations and fake alert were LOW. `ProductionAlertPort` was HIGH, lower-bound, because interface dispatch reaches three indexed process groups. This leaf kept every existing alert method intact and added only the non-OK path.

## Limits

Status delivery remains best effort through the existing monitoring module. These tests prove the adapter call and notice content with mocks; they do not prove Slack availability or delivery.

Signal-row persistence and regime-call persistence are still separate writer calls. Transactional atomicity across the signal and call remains future L02 work. No database, network notification, environment credential read, runtime start, deployment, commit, or historical rewrite was performed.
