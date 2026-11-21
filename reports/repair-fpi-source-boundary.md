# FPI source boundary repair

Packet 20, 27 September 2026. Base HEAD `9fa150538d08ab5a2a6c587976552944f47a724d`, branch `codex/frontend`, shared uncommitted repair checkout. This is a local safety and source-definition repair. FPI replacement acquisition and empirical validation remain open.

## Findings and implemented behavior

The [primary-source review](repair-fpi-source-research.md) established that the old SEBI URL did not supply the assumed daily table. Its claimed release clock and archive duration were unsupported. The actual NSDL investment report has seven category groups, reporting dates, separate INR-crore and USD-million columns, and a separate derivatives section. Equity plus one debt leg cannot represent its total. Source observations were verified through rendered official pages; original HTML/export structure and reliable direct ingestion remain unverified.

Both old FPI fetch APIs now raise before network access. The guessed scraper and repeated-current-page pseudo-history are removed. Retained scalar/date helpers reject nonfinite values, invalid calendar dates and trailing date text.

The live scheduler no longer tries to normalize an unqualified amount against descending, undated signal-row history. Live, staged and both replay versions record `fpi_source_unqualified` and `fpi_history_unavailable` for USDINR. Other pairs do not inherit those warnings. The v2 replay no longer republishes naked legacy flow values into a new signal row. The common builder rejects non-null raw FPI or normalized FPI inputs, including zero, until a qualified dated path is implemented. Original stored records are not rewritten.

The pure normalizer returns unavailable when prior median absolute deviation is effectively zero. Flat history cannot supply neutral evidence or make an extreme current observation meaningful. Legitimate zero in varying history remains supported. Positive normalized deviation is still distinct from positive cash inflow.

[The observation contract](../docs/FPI_OBSERVATION_CONTRACT.md) specifies series identity, complete categories, units, original payloads, immutable first-seen times, revisions, causal history selection and activation requirements. The former research recommendation is explicitly superseded.

## Verification and review

- Parent focused FPI gate: 63 passing cases across numeric, retired-fetch, builder, direction-consumer and both replay contracts.
- Parent network-isolation gate: eight passing cases, including fail-if-called request controls, caught attempts, threads and actual local aiohttp transport.
- Full pipeline integration: parent Unlazy R2 passed after the replay correction; 1216 tests independently collected.
- Final full Ruff passed; final MyPy passed across 209 files. Git diff whitespace check passed.

The first full integration attempt exposed one outdated exact warning-list expectation in the USDINR replay test. Direct full diagnostics returned 1215 passes and that one failure. Parent inspection also found that the older replay version should disclose the same FPI limitations; both implementations and the exact expectation were aligned. No missingness assertion was removed.

GitNexus was run for edited symbols. Shared production and even test symbols returned CRITICAL graphs containing unrelated UI/process entries; new tests were unindexed. The parent warned before changes and inspected actual live, staged, replay and builder consumers. This graph is supplementary evidence, not a reliable exact dependency map. No commit was made.

## Network verification correction

The former FPI smoke test performed an unmocked public request and accepted missing data as success. Prior blanket full-suite no-provider-request claims are withdrawn. Exact successful responses and request counts are unknown; no source observations from those runs are accepted. A stubbed negative control reproduced the request boundary without external access.

The new default test guard covers Python DNS, TCP and UDP socket paths during each test and detects caught attempts at teardown. It is not an OS sandbox; collection-time imports, higher-scope fixture setup, subprocess/native bypasses and workers surviving fixture teardown need separate controls. See [the guard report](repair-test-network-isolation.md). Public source-page research is intentionally separate from test isolation.

## Remaining requirements

Do not mark FPI repaired in full. Original-source capture/export inspection, strict real-fixture parsing, private append-only storage through writer.py, first-seen/version selection, actual historical coverage, shared-consumer integration and frozen out-of-sample feature tests are all required. A source definition is not a working adapter; deterministic tests do not establish predictive value.

No credentials, paid AI, production database writes, deployment or runtime startup were used for this packet. Docker and heavier Hermes services were unnecessary; the Hermes MCP configuration was unchanged. Frontend files were unchanged, so packet 19 remains the latest frontend verification receipt.
