# Scheduled pipeline health repair — 27 September 2026

The scheduled entrypoint now runs the full wrapper. Previously Prefect invoked only the legacy daily flow, bypassing the wrapper's overnight, aggregate and feature-flag responsibilities. The wrapper itself ignored staged health, substituted missing DQS with 1.0, and reported seven processed pairs despite the three-pair lock.

## Reproduced failure

The parent loaded only `run_pipeline` and `_dqs_from_v2_output` function definitions from the original Git HEAD into a mocked namespace. A staged output explicitly marked FAILED, with all DQS scores missing, still called the original success heartbeat with `pairs_processed=7`, `regime_calls_count=3`, and `dqs_score=1.0`. The isolated reproduction printed `NEGATIVE_CONTROL_REPRODUCED`; no original module initialization or external service was run.

## Changed behavior

`pipeline/prefect.yaml` now selects `src/scheduler/run_pipeline.py:run_pipeline`. That function is a Prefect flow and the supported scheduled completion boundary. Both live feature-flag paths return typed execution evidence. It verifies the requested date, locked pair identities, actual publication counts and completed validation evidence. Missing quality stays null; zero stays zero; invalid values cannot produce healthy completion. Input degradation and failed stage reports survive the wrapper.

The order is daily inference/publication and validation, optional isolated shadow comparison, overnight checks, dated validation aggregation, and the health write. The final heartbeat follows those required operations. The staged inner flow suppresses its own run-completion notice when called by the wrapper. Pair publication notices remain separate from whole-run completion.

Required-stage exceptions reach Prefect. Diagnostic writes and failure notices cannot mask the original exception. Shadow errors or divergent outputs remain visible as DEGRADED while required live work continues. Empty aggregation results remain DEGRADED and do not claim that validation statistics were produced.

Health is recorded from this execution, without reading old database rows to invent completed stages. Unconfirmed publication counts after early failures remain null. AI brief completion stays unknown because this wrapper has no receipt proving it. Non-OK stage details are retained in the existing health row's `errors` JSON. The health writer uses one upsert on the existing unique date key; it no longer deletes the previous snapshot before inserting its replacement. Tests verify the writer call and exception behavior, not a production database transaction.

Overnight checks return explicit health. Fetch failures propagate even if updating their failure counter also fails. Missing pair inputs, stale card dates and invalid prices remain DEGRADED. The check operates only on EURUSD/USDJPY/USDINR. A historical requested date cannot silently use today's live prices; that check returns DEGRADED before fetching. This is not a historical overnight replay implementation.

## Verification

The two actual Prefect integration cases run the decorated wrapper with the real staged flow, fake market/writer/alert ports, and mocked overnight/aggregate services. They cover normal degraded completion and an aggregation exception after three real staged publications. Both produced exactly three pair notices plus one final wrapper notice, with no inner healthy heartbeat.

The parent scheduler gate covers 66 collected tests across wrapper flags, execution ordering, required-stage failures, failed diagnostic channels, missing/invalid quality, missing or extra pairs, shadow isolation, actual Prefect integration, signal publication and stage health. The independently rerun legacy gate covers 13 tests; its helper and structural evidence is described in `repair-daily-run-contract.md`. Full-suite results and gate counts are recorded in `REPAIR_CHECKPOINT.md` after integration.

Ruff passed and MyPy passed 170 source files. No deployment, production database write, real notification or original-ledger rewrite occurred. The checks did not require Docker or a heavier Hermes component. The existing Prefect test configuration and fake external ports were used for execution tests.

## Remaining requirements

O01/O02 retain release acceptance and wider operational evidence. The legacy flow still contains optional AI/research catches that need explicit per-stage receipts. This packet does not prove every expected session, upstream source freshness, forecasting skill or the deployed schedule. The public health readers can still infer integrity from table presence; U04 remains open. Current rate-deficient production inputs remain DEGRADED.

Health storage is still a daily snapshot, not an immutable per-attempt event ledger. Notification helpers remain best effort. Signal/call/rationale publication still needs the atomic L02 contract, and destructive backfills remain L01 work. Source timing, historical reconstruction and model-version release gates remain open.

GitNexus impact returned CRITICAL across the shared scheduler/storage graph, including unrelated UI paths. Parent and worker traced exact callers and inspected the expanded return contracts. Worker detect-changes succeeded on the shared checkout (53 files, 335 symbols); this was not a leaf-only diff or release approval.
