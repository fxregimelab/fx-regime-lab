# Durable qualification database — packet27

Parent completion and independent acceptance report, 28 September 2026. The worker's code and saved self-check survived an interruption; its report did not. The parent checked that its native handle and verifier process were absent, preserved the implementation, re-ran the declared gate and completed this report.

The new migration retains administrative qualification events in a private append-only table. A transaction-held lock serializes transitions across membership, value, parser and date scopes. The append function verifies exact canonical commands, retained targets and the expected predecessor before assigning an ordinal. Exact retries return the same event, clock and ordinal. Sequence gaps after rollback are permitted. Timestamps do not order events.

A date resolution reads its full same-date candidate basis and three qualifying heads in one committed snapshot. The retained witness preserves that observation even if another parse commits afterward. A later complete view then diagnoses the stale basis. This is evidence for this resolution transaction, not a durable saved decision-read implementation.

## Verification

The parent independently re-ran leaf27.2:G1 through the declared Unlazy checker with a600-second outer limit. It passed with output SHA-2562c5a4044de2634a3bb5d99b00ebab4517784a00c796fab1ad7078da07637c17a (1434bytes). The checker exit of one represented pending manual G2; the verifier itself exited zero and emitted FPI_QUALIFICATION_DB_VERIFIED.

The real PostgreSQL17.11 verifier covers eight scenario groups: strict document/type/identity/isolation refusal; transaction order and observed locks; tied/backward clocks with the Python view; resolution snapshots around parse commits; actual concurrent identical and conflicting RPCs; permissions/immutability/insert rollback; real request timeout cancellation; and populated migration reapplication. Synthetic complete capture/artifact/parse fixtures enter through the actual central writer and SQL adapters. Distinct connections and observed advisory-lock barriers establish concurrency, rather than sleeping and assuming a race occurred. Existing artifact, parse, member and capture evidence and unrelated permissions remain unchanged.

Parent negative control changed only the predecessor comparison to false in an in-memory copy of the migration. The unchanged real verifier passed its strict-input phase and failed in the expected transaction-order phase. The on-disk migration hash stayed unchanged, and the scratch database was removed. Marker: FPI_QUALIFICATION_SQL_PREDECESSOR_NEGATIVE_CONTROL_VERIFIED. This demonstrates that the verifier can detect this structural defect; it is not proof against every possible implementation defect.

Configured Ruff and strict MyPy pass for the standalone verifier. The actual central writer also passed parent receipt substitution testing: a different command with freshly computed valid event hashes was refused while the valid controls before and afterward passed. See reports/repair-fpi-qualification-writer.md and reports/repair-fpi-qualification-storage-integration.md.

## Timeout correction and runtime

The parent reproduced that function-local statement_timeout did not arm the outer statement timer. The RPC now requires a nonzero inherited timeout of at most30seconds, while the caller must arm that timeout before the request. The test cancels a200ms scratch delay using an actual50ms outer timeout, verifies rollback and succeeds with30seconds. A displayed setting alone cannot prove correct timer setup inside hostile nested SQL; deployed connection configuration remains a release requirement. The function still bounds lock waiting separately.

The parent used the existing task-local PostgreSQL installation with the private socket, port55437 and empty listen_addresses. After positive and negative checks, actual SQL confirmed zero packet scratch databases and zero other clients. The parent stopped the server and confirmed pg_ctl reported no server running. No Docker or heavy Hermes runtime was started or enabled.

## Source identities and limits

- Migration SHA-256: ad1e12c9b6ec012e46e0fe9166a862a317c289b78922b2cc97bbc0e79b790c34.
- Verifier SHA-256: 9b7676faff7c8bd4615e236c890a3d896f0f9a577db2dd439fe47908e4e21392.
- Git base: 9fa150538d08ab5a2a6c587976552944f47a724d, branch codex/frontend; existing dirty work preserved.

The new symbols were absent from the current GitNexus index, yielding UNKNOWN risk. That is a coverage limitation, not evidence of zero callers. Existing helpers were reused without edits. No index rebuild or commit occurred.

An ACCEPT row records administrative intent. It does not authenticate source acquisition or executed code, confer eligibility, create a saved complete decision read, or activate FPI. Protected verification/release authority must still be checked independently before consumption, including for these retained events. Production FPI remains inactive. No provider request, credential access, production write, push or deployment occurred.
