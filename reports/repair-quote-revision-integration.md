# Quote revision integration — packet 17

27 September 2026. Parent acceptance against `docs/QUOTE_REVISION_CONTRACT.md`, on branch `codex/frontend`, HEAD `9fa150538d08ab5a2a6c587976552944f47a724d` plus the preserved uncommitted repair work.

The comparison verifies the exact stored snapshot text and rebuilds its reference from validated pages before comparing rows. It reports every changed row hash and multiplicity. It distinguishes snapshot provenance changes, retained-source changes and reference-price changes. An incomplete acquisition is not comparable and cannot create apparent removals. Inputs remain unchanged; outputs remain provisional and validation-ineligible.

The parent reviewed the implementation and independently ran both leaf gates. The new writer bridge uses the actual central capture and snapshot writers with mocked RPC storage, then supplies their exact serialized envelopes to reconciliation. Across all three locked pairs it checks capture-before-snapshot ordering, exact snapshot retries, one retained/one removed/one added row, close/high effects, preserved originals and no database calls during comparison. It is a serialization/integration test, not a new PostgreSQL or provider test.

Parent review strengthened the contract to measure actual retained text before parsing, in addition to asserted raw response sizes, and to reject mixed identity even in an otherwise matching incomplete snapshot. Review also corrected an erroneous test expectation: the five-row fixture retains three occurrences, removes two and adds two. Conservation now has explicit assertions.

Verification:

- Quote revision leaf gate: passed; 22 focused cases.
- Writer/capture/reference/revision integration gate: passed; 138 cases collected.
- Complete pipeline regression gate: passed; 1,028 tests collected independently.
- Full Ruff: passed. Full MyPy: passed across 198 source files, including tests.
- Source review: exact-text hashes, strict JSON types, canonical UTC ordering, resource preflight, duplicate multiplicity, complete versus incomplete acquisitions, ambiguous prices and deterministic output.

The [economic action audit](repair-pair-economic-actions.md) was also accepted as research guidance, not implemented strategy repair. The parent inspected current composite, COT fallback and special-score formulas and independently checked [CFTC category definitions](https://www.cftc.gov/sites/default/files/idc/groups/public/@commitmentsoftraders/documents/file/tfmexplanatorynotes.pdf), [Japan's intervention authority](https://www.boj.or.jp/en/about/education/oshiete/intl/g19.htm), [MoF's April–June 2024 transactions](https://www.mof.go.jp/english/policy/international_policy/reference/feio/quarter/2024_2Qe.html) and [the monthly Japanese call-money series](https://fred.stlouisfed.org/series/IRSTCI01JPM156N). These support the stated definitions and contradictions, not predictive coefficients. The audit explicitly limits RBI search-excerpt evidence and NSDL pilot-host evidence. Its 17 regression cases remain implementation requirements.

The GitNexus index did not contain the new symbols. Its MCP version mismatch and CLI missing full-text indexes limited exploration. The worker's aggregate change scan reported CRITICAL risk across 73 accumulated dirty files, 494 indexed symbols and 293 flows; that is not this leaf's isolated impact. No commit was made.

Remaining work includes durable append-only reconciliation/qualification events, as-of selection, actual provider coverage and revision evidence, qualified evaluation inputs, and the economic regressions. A full row delta may be large within the declared input limits; persistence/chunking is not implemented here. No provider request, credential read, production write, runtime startup, deployment or forecast experiment occurred in this packet. The full repair goal remains active.
