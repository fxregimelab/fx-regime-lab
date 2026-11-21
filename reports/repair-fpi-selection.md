# FPI decision-snapshot selection repair

Leaf 23.1 implements a pure replacement domain in `pipeline/src/research/fpi_selection.py`. It keeps canonical INR values separate from capture occurrences, parser implementations, qualification events and exact decision input sets. Nothing in this leaf connects FPI to production, activates a forecast feature or proves a database read was complete or committed.

The concrete interface and policy are frozen in `docs/FPI_SELECTION_CONTRACT.md`. The main consumer function is `select_fpi(snapshot, policy)`. A missing saved snapshot returns `VISIBILITY_UNPROVEN`; a bare timestamp is rejected. Every result binds the complete frozen policy, selector artifact assertion, exact input set and complete returned content.

## Changes and evidence

- A -> B -> A uses three capture memberships while preserving the first and third value hash. Exact duplicate retries add no record. All tested permutations produce the same result.
- Delayed parsing and qualification are allowed. Exact snapshots determine membership; retrieval and recording clocks do not manufacture historical read visibility.
- Strictly separated, explicitly asserted request intervals can order occurrences within an endpoint. Overlapping, touching or unordered conflicting responses remain missing. Latest/Monthly disagreement remains a conflict unless a frozen priority policy or explicit reviewed resolution applies.
- Complete parse results retain failures separately. Reusing a capture/parser/definition identity for changed output rejects. Successful results require HTTP 200 and the canonical INR definition; partial responses cannot carry successful membership sets.
- Full qualification chains validate scope, predecessor references and competing successors. Withdrawals do not revive older captures by default. Resolution requires the chosen membership to be qualified when the event is recorded and binds its complete candidate basis.
- The original research floor remains ten unique earlier dates, with explicit India calendar-day age limits and a bounded window. Missingness stays distinct from a measured zero, including stale, conflicted, withdrawn, unqualified and insufficient-history states.
- Counts and document sizes are bounded. Predecessor-chain validation is linear. Capture metadata is decoded once per distinct capture per selection; interval-frontier selection avoids a pairwise scan. A synthetic 20-capture/25-date regression verifies the decode count.

Final worker checks from `pipeline`:

```text
node ../scripts/repair/verify-pytest.mjs tests/test_fpi_selection.py
79 passed; REPAIR_PYTEST_VERIFIED

python -m ruff check src/research/fpi_selection.py tests/test_fpi_selection.py
All checks passed

python -m mypy src/research/fpi_selection.py tests/test_fpi_selection.py
Success: no issues found in 2 source files
```

The first test set passed 49 cases. Parent review then required the preserved history floor, exact selector artifact identity, complete result fingerprint, HTTP/definition restrictions, bounded linear chain validation, historical resolution qualification and cached capture metadata. Those changes have explicit regression coverage. One later worker test used the fixture's default September 15 reporting date when testing zero on September 25; it correctly returned STALE. The fixture date was corrected without weakening age policy. The final 79-case gate passed.

## Four review passes

1. **Temporal behavior:** exercised saved snapshots before and after qualification; late imports; reversion; overlapping/reversed responses; endpoint conflict; newest-date blocking; withdrawals and explicit reinstatement. Value first-seen never participates.
2. **Identity and replay:** checked canonical value components, separate source-evidence identity, parser implementation identity, full policy hash, complete result hash, input-order invariance, exact retries and unchanged prior results. Equal totals with changed components remain different values.
3. **Invalid inputs and resource bounds:** checked malformed/relabelled values, partial/failing responses, naive/future/reversed times, missing references, transition forks, mutable tuples, missing request start, policy floors, record limits and a 1,001-event chain. Caller assertions still require external authenticity and completeness evidence.
4. **Scope and maintainability:** kept all temporal rules behind the new selector; no old module, writer, ledger, source fixture or integration file was edited by this worker. Parsed documents and raw capture metadata stay private inputs. Existing canonical math is reused; there are no network, database, AI or runtime calls in the new module.

## Timing-review checks and remaining gates

| Review check | Pure evidence in this leaf | Still required externally |
|---|---|---|
| 1. A -> B -> A | Snapshot progression, different capture IDs, same returning value hash, permutations/retries | Durable registration |
| 2. Visibility after retrieval | Separate capture/parse/qualification times and exact saved sets | Real decision read witness |
| 3. Commit gap | Exact old input sets remain unchanged | Paused transaction, concurrent reader and reverse allocated-ID commit order |
| 4. Late import | Prior replay unchanged; late recording cannot supersede newer ordered capture | Import authenticity and retained receipts |
| 5. Out-of-order responses | Overlap conflict, strict interval frontier, later non-overlapping resolution | Trusted acquisition timing |
| 6. Endpoint disagreement | Conflict, equal-value corroboration and explicit hashed priority | Accepted source policy/research use |
| 7. Parser change | Both candidates/failures retained; qualified correction; identity mismatch rejection | Artifact/code/dependency retention and verification |
| 8. Withdrawal scope | Membership/value/parser scope, no implicit older fallback, reinstatement | Durable append-only events |
| 9. Whole-result atomicity | Complete-object validation and failure without partial dates | Real transaction rollback and source-date completeness |
| 10. Retry/concurrency | Deduplicated identity and competing-predecessor rejection | Concurrent writer serialization and interrupted-response reconciliation |
| 11. Frozen policy/parity | Full policy/result hash and deterministic pure repeatability | Actual live/staged/replay consumer integration parity |
| 12. Replay/missingness | No bare-cutoff replay; stale/conflict/withdrawn/unqualified stay missing; coverage floor | Persisted original decision snapshots |

Seven-digit receipt normalization remains an import-adapter requirement and is not implemented here. Unknown request-start input is rejected; a pure constructor cannot detect a caller inventing a plausible start. Neither ordered capture IDs nor implementation hashes are authentication flags.

## Runtime, tools and ownership

Python alone is sufficient. Local process/service inspection found no PostgreSQL, Docker backend or Hermes process and a stopped Docker service. No service was started; Hermes MCP configuration was untouched. No provider requests, credentials, DB/AI calls, production writes, commits or raw source data were introduced.

GitNexus CLI impact checks for the new selector and public record types returned UNKNOWN because those new symbols were not indexed, with no indexed callers returned. MCP impact attempts reproduced the known storage-version 42/runtime-version 40 incompatibility. This is not proof of zero impact; the module has no production caller added by this leaf. The parent owns legacy-selector retirement and independent integration review. No index was rebuilt and no commit was made.

Only four worker-owned paths were changed: the new source, its test file, the frozen contract and this report. Relevant memory search had no matches; no memory-derived project fact was used.

Source SHA-256: `ab5e524ea027a66e7518d3784692b2a107c6f78cb994beda99c599ac439dab06`.
Test SHA-256: `dba4be068486e40e9993bbab44403c8089755700840a4d4e4f5b8e1469f2c561`.
Contract SHA-256: `8b136ba9ee6c4c968832baa89057313d2cc7a4c674e458819930af5432849a5a`.
