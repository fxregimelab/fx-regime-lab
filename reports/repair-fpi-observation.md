# Dated FPI observation implementation

Packet 21, 27 September 2026. New pure module `pipeline/src/research/fpi_observation.py`; no production consumer activated. The complete [contract](../docs/FPI_OBSERVATION_CONTRACT.md) defines source limits and remaining integration.

The constructor requires all seven categories and exact routes, validates row and group arithmetic, and detaches canonical INR amounts. It uses integer hundredths of crore; ambient floating-point or Decimal precision cannot change results. Identity covers all INR components, so offsetting revisions remain distinct. Source URL, raw hash, parser version and UTC retrieval/first-seen times remain separate provenance.

The selector validates canonical evidence again, filters captures unavailable at the decision instant, rejects altered first-seen times and conflicting revisions, resolves by knowledge time within each report date, and then chooses the latest report date. A late old-date revision cannot replace the current date. Prior history contains unique older dates in chronological order with explicit age limits. Available means structurally available for research only.

Parent review fixed an order-dependent same-time revision conflict, allowed legitimate simultaneous Latest/Monthly captures, made duplicate selection deterministic and enforced the ten-observation minimum. Boundary checks also reject impossible timezone ranges. The initial synthetic fixture's hand-calculated expected total was corrected from 398 to 397 (272 from ordinary groups plus125 from mutual funds); source figures were not used as synthetic expected values.

Focused verification: 52 synthetic observation cases pass, including negative numeric/schema/time/hash cases, real rounding-bound mathematics, offsetting revisions, future versions/captures, altered immutable times, duplicate captures, tie permutations, stale/short history and India date boundaries. Scoped Ruff and MyPy passed before final integration. These fixtures prove contracts, not source availability or forecasting value.

GitNexus CLI returned UNKNOWN for both new public functions; MCP calls for new helper/class/test symbols failed with the existing storage-version42/runtime40 mismatch. Direct inspection confirms this module has no production callers. No existing production function was changed by this leaf. No DB access, provider request, runtime startup or model call is required by it.

Original NSDL HTML is now separately available in private research captures, with its verified spans and malformed footer described in the source report. The parser is now separately verified under leaf21.3. Durable first-seen assignment, source acceptance/withdrawal events, production consumer parity and frozen feature evaluation remain required. A caller-supplied time cannot prove historical knowledge by itself.

Parent bridge check also converted the independently inspected original Monthly source rows into all18 canonical observations. Before the candidate capture instant the selector returned missing; at capture it returned25September as current with17 prior dates. The final parser verifier repeats this bridge using actual original bytes and conservatively ceiled receipt completion. Neither check treats the research receipt as durable production provenance.
