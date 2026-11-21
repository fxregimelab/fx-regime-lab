# FPI qualification order v2

28 September 2026. Leaf 25.1 implementation and self-check report. Parent acceptance remains separate.

The new pure model represents ACCEPT, RESOLVE and later WITHDRAW even when all three timestamps are equal or decrease. Explicit event ordinals determine transition order. Historical witnesses preserve the qualification state used by a resolution; current heads determine whether that resolution is usable today. Existing v1 types and consumers retain their old meaning.

## Delivered scope

Only these files were created by this leaf:

- `pipeline/src/research/fpi_qualification.py`
- `pipeline/tests/test_fpi_qualification.py`
- `reports/repair-fpi-qualification-order.md`

The implementation follows `docs/FPI_QUALIFICATION_ORDER_CONTRACT.md`, including the parent's amendments for batch evaluation, value-hash/date consistency and explicit canonical sort keys. It provides frozen commands, heads, resolution witnesses, ordered events, compact member references, complete asserted views, strict command/event decoders, a batch result and the two scalar convenience queries.

Current heads must explicitly cover every membership, value, parser and date in the supplied universe. Events are exactly the referenced current and historical witness heads. Missing ancestors are allowed; supplied wrong-target or later predecessors, repeated roots/successors and inconsistent witnesses reject. A value hash cannot claim two reporting dates. Shared value/date references across distinct members or parsers remain valid.

Nested records are rebuilt at the view boundary, including their commands and witnesses. Canonical documents and identities are checked against supplied cached fields, and valid nested objects are copied so later mutation of the caller's original objects cannot change an existing view. Evaluation validates the entire supplied view once before using shared maps. No mutable cache is trusted as evidence.

## Verification evidence

The inspected G1 command was run through the Unlazy checker with the already authorized `--approve` action:

```text
node C:/Users/sakha/.codex/skills/unlazy/scripts/gate-check.mjs --approve .unlazy/repair/gates/leaf-25.1.md --cwd D:/Projects/fxregimelab
```

`leaf-25.1:G1` passed with process exit zero and `REPAIR_PYTEST_VERIFIED`. Its command runs the new qualification tests and unchanged v1 selector tests: **215 passed**, comprising **136 v2 tests and 79 v1 tests**. The checker itself returned exit one because the parent's manual G2 was still pending; that was not a test failure.

Saved G1 evidence:

- Definition SHA-256: `13034c18fad41cbdf46b764b09f791584f508f0a65dfcdcc4b75989deede4b3c`
- Output SHA-256: `2145efc0f118c0e83bf74ffcc369f9f804ccf47471ca42fef8a08d71dd0f063c`
- Output bytes: 288
- Working directory: `D:/Projects/fxregimelab/pipeline`

Final scoped checks, repeated after the interruption without changing implementation or tests:

```text
python -m ruff check src/research/fpi_qualification.py tests/test_fpi_qualification.py
All checks passed!

python -m mypy src/research/fpi_qualification.py tests/test_fpi_qualification.py
Success: no issues found in 2 source files
```

The tests cover the original v1 tied-clock failure, v2 tied/decreasing clocks and input permutations, explicit absence and complete scope heads, all 64 membership/value/parser action combinations, scope clearing, reinstatement, stale candidate bases, different parsers, historical blocks despite current reinstatement, absent long-history ancestors, supplied predecessor faults, forks, duplicated identities, malformed JSON and forged nested frozen objects. They independently construct canonical documents to check view and evaluation hashes.

Resource checks use both exact small boundary controls and real contract limits:

- A 4,096-member resolution basis accepts; 4,097 rejects. Member/head/event tuple count overflows reject before record reconstruction.
- A complete 20,000-member universe accepts. A batch over 20,000 members and 100 dates calls view reconstruction once and member evaluation exactly 20,000 times.
- A real 16,000,000-byte overflow rejects before all supplied events are reconstructed. Incremental exact byte accounting happens before building the combined view document. The exact-byte and one-byte-over checks also use a small independently serialized control.
- Across 250 dates sharing historical parser heads, each view construction performs exactly 750 binary-search witness lookups. Current and historical evidence remain distinct without scanning all events for each witness.
- Ordinals near the signed 64-bit maximum work with three compact referenced events and an absent historical predecessor; no full-chain traversal occurs.

## Review passes and observed failures

1. Implemented the complete ordered model, codecs and strict view checks against the frozen contract.
2. Reviewed the state rules and historical evidence. Incorporated the parent's batch-evaluation and value/date consistency amendments before final verification.
3. Added malformed-object, canonical-identity, real-size and many-date adversarial checks. The first 120 tests passed; expanded checks reached 136 v2 cases. Initial lint formatting and test-only typing findings were corrected. The final scoped checks are clean.
4. Re-read the resulting validation and evaluation paths, checked canonical ordering and incremental size accounting, and verified UTF-8 files with LF endings and no BOM. No remaining bounded leaf implementation defect was found in this pass.

A post-interruption status inspection initially combined `--status` with `--cwd`; the checker rejects that combination because `--cwd` is execution-only. The existing G1 evidence was preserved. Status was then inspected using the supported command. No runtime or implementation action depended on that failed status command.

## Provenance and limits

Base HEAD remained `9fa150538d08ab5a2a6c587976552944f47a724d`; the shared dirty checkout was preserved. GitNexus impact was requested for all twelve new public symbols. Each returned target not found, zero mapped impacts and risk UNKNOWN. This is an index coverage limit, not verified absence of callers. No index rebuild or commit was performed.

Final file identities:

| File | Bytes | SHA-256 |
|---|---:|---|
| `pipeline/src/research/fpi_qualification.py` | 29,153 | `004e32dc8fe03710f80fb95da41add7b13bc395a08c5e59f3bfa1c6010953a28` |
| `pipeline/tests/test_fpi_qualification.py` | 37,533 | `f81a639aa3f03df604210c4a4ce0915ab16fededa5db6497831cc7443eef2f21` |

Repository instructions, the repair amendment, current sprint, frozen contract, v1 selector, parse-record context, the storage design report and the quality-first policy were read. Humanscope and Unlazy were applied. A narrow memory search found no project/FPI entry used by this leaf.

No network, provider, AI, credentials, database or runtime startup was used. The inspected process list showed no Docker/Hermes match, and the pure module and tests required neither. No SQL, central writer, published record or production consumer was changed. Synthetic test fixtures are not presented as live data.

At handoff the leaf ledger has **one met gate, one pending parent gate and zero abandoned gates**. G2, independent mutation/reference acceptance and full pipeline regression remain parent work. The parent has reported independent batch comparisons and negative controls, but this report does not substitute that message for saved parent gate evidence.

These objects validate consistency of supplied assertions. They do not authenticate ordinal assignment, prove a complete database read, verify parser or selector execution, or authorize FPI activation. Durable ordering, saved decision reads, trusted execution and real consumer integration remain open outside this leaf.
