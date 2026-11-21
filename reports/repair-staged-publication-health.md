# Staged publication and health repair — 27 September 2026

The staged pipeline previously discarded its computed signal row and replaced input degradation with a successful publication status. A database write could therefore produce a healthy notice even when inference lacked required history. This packet repairs that behavior locally.

## Changed behavior

Publication requires a matching signal row and explicit upstream health. It saves signal evidence through the writer port before writing the call, checks for a durable call ID, and retains the worst upstream status and its details. Missing, nonfinite, out-of-range or low quality scores cannot use the healthy publication channel. Failed input stages and mismatched pair/date identities stop before persistence.

Single-pair and multi-pair flows share the same stage path. Ingestion and signal failures stop publication. Exceptions produce a FAILED notice identifying the stage; if notification also fails, the original error still reaches the caller. A validation exception stops the daily heartbeat. Skipped validation is explicitly DEGRADED. Empty or duplicate pair requests cannot report a completed run.

Each publication output retains upstream, quality and write-stage evidence. The multi-pair output retains its ingestion, publication and validation reports. DEGRADED and FAILED use the new status adapter; only a run whose required stage reports are OK can use the healthy heartbeat. Existing recorded fixtures remain DEGRADED because rate history is unavailable.

## Verification

The parent publication/flow gate passed all 45 collected tests, including 23 new failure-ordering and health cases. The actual Prefect flow and shadow tests also passed after their obsolete healthy-notice expectations were replaced with signal persistence and degradation assertions. The healthy publication branch has a separate synthetic positive control; it is not evidence that current market inputs qualify as healthy.

The parent independently reran all 21 adapter tests. They exercise production writer delegation, detached fake signal snapshots, non-OK routing, credential-shaped note redaction and suppression of raw exception messages. Full pipeline Ruff passed and MyPy passed 167 source files. The final full regression receipt is recorded in REPAIR_CHECKPOINT.md and the root gate ledger.

The inspected commands were local mocked tests. No production database write, real notification, deployment or historical rewrite occurred. No Docker or heavy Hermes runtime was required or started.

## Remaining boundaries

Signal and call persistence are separate operations. A partial write or a retry against an existing call can still create an evidence mismatch; L02 must provide an atomic, versioned publication contract. This report does not claim transactional publication or verified notification delivery. The legacy `alerts_sent` output records helper calls, not external delivery receipts.

A completed validation function does not prove every expected market session has an eligible outcome. Source history, timestamps, maturity, publication-time prices and backlog completeness remain governed by V08/P01/D03. Stage reports are currently returned in memory; durable run evidence and the public audit display remain U04 work.

The outer scheduler and deployed Prefect entrypoint still need O01/O02 repair. Their aggregation, completion and failure behavior is not made correct by this staged-flow change. Local successful tests are not release acceptance or a forecasting improvement.

GitNexus returned CRITICAL impact for the orchestration/test change with unrelated UI paths included. Exact call sites were manually traced and covered by the staged regression gate. The earlier detect-changes command exited without a usable report; no commit was attempted and no current change-scope acceptance is claimed.
