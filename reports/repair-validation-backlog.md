# Validation backlog and call identity repair — 27 September 2026

The legacy engine previously read only the newest 30 calls per pair. Older unfinished horizons became unreachable. Evaluation lookup also selected a latest row by date/pair, which cannot identify two distinct published calls sharing those values.

## Changes

`writer.get_historical_regime_calls` now paginates all requested rows, including requests above the database page size. `limit=None` retrieves full history; finite limits apply across pages. Date and ID form a stable order, returned oldest first. The engine and staged validator request all history.

`writer.get_validation_log_for_call` selects the exact durable call ID, canonical scoring version and current evaluation. It does not pick an arbitrary row with a limit or fall back to date/pair. The obsolete ambiguous helper has been removed after repository-wide caller inspection. The legacy engine, single-call replay, batch replay, incomplete-call selector and staged adapter use the new identity contract.

Completed horizons retain their stored values. The engine and staged validator skip completed due horizons before fetching prices; completed neutral evaluations do not become incomplete merely because their directional scores are null. Missing exact prices remain unavailable. Database read failures propagate from the engine.

## Evidence

A mocked execution of the original engine from `9fa1505` processed 30 of 41 eligible calls, with oldest processed ID 12. The repaired engine processed all 41, beginning at ID 1. Both used the same call/price fixture and intercepted every database writer/read; no production access occurred. Output: `BACKLOG_NEGATIVE_CONTROL_VERIFIED`.

The parent packet's 50 tests pass, covering more than 30 old calls, same-date opposite directions, earlier-horizon preservation, completed-neutral replay, database failure propagation, exact identity filters, pagination over 1,000 rows and limits spanning pages. The staged packet's 31 tests were independently rerun by the parent. The full regression gate passed with 413 tests collected. Full Ruff passed and MyPy passed all 163 files. Git diff whitespace check passed.

GitNexus classified engine impact as HIGH (eight affected symbols, scheduler/backfill flows). Final shared tracked-change scan reported 35 files, 211 symbols, 29 flows and CRITICAL overall risk. No new schema or frontend change was made in this packet, so their prior verification was retained rather than presented as newly rerun evidence.

## Remaining limits

Full-history traversal does not manufacture historical prices. The staged production snapshot currently carries 120 calendar days of spot history; older incomplete calls still need a historical source path. Source/history parity remains open under P01. Validation skips and scheduler-level failures still need explicit status accounting under O02: the legacy orchestrator can catch a validation failure and subsequently send a success heartbeat. This packet does not claim to fix that scheduler behavior.

Large histories still require per-call current-evaluation reads. Bounded operational batching and restart progress need scheduler integration without reintroducing silent truncation. Publication-time tradability, calendars, source vintages, research validity and deployed observation remain open. No database runtime was needed, and no credentials, production writes, commit, push or deployment were used.
