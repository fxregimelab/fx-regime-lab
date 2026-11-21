# Quote reference constructor repair

## Result

`build_quote_reference` now constructs a deterministic provisional daily midpoint reference from validated Massive quote-page manifests. It validates every manifest before interpreting any page, binds the ordered `capture_sha256` list to an algorithm-versioned input fingerprint, and keeps `as_of` outside that source fingerprint.

Complete acquisitions use integer nanosecond timestamps and exact `Decimal` midpoint arithmetic. The arithmetic uses its own context, so host precision, exponent limits and traps cannot alter the result. Price coefficients, exponents and adjusted exponents are restricted to the contract's 128-unit software resource envelope. Source values outside that envelope remain counted as occurrences, but are invalid and carry `numeric_limit_exceeded`.

The constructor separately reports source occurrences, distinct canonical rows, duplicates, invalid rows and out-of-window rows. Equal repeated rows do not change OHLC. Different midpoints at the first or last timestamp make the corresponding open or close ambiguous and null. High and low remain valid-subset diagnostics for a complete acquisition.

## Fail-closed boundaries

- Every page manifest passes `validate_quote_page` before cross-page or body interpretation.
- Pair, instrument, window, page order, cursor chain, fixed request parameters, HTTP status, manifest issues, body schema and acquisition timing are checked explicitly.
- Every request must begin at or after the UTC day has ended, and `as_of` must be at or after the same boundary.
- Missing, failed, cyclic, reordered, duplicated, late or otherwise incomplete acquisitions return null OHLC, zero/not-computed occurrence counts and null timing fields. Those values do not imply an empty daily dataset. A captured prefix is never presented as a daily reference.
- Malformed and out-of-window quote occurrences remain visible on a complete acquisition and prevent qualification.
- Every result remains `project_maturity=provisional`, `provider_finality=unknown`, `validation_eligible=false`, with `coverage_policy_unverified` in its exclusions.

## Verification

- GitNexus pre-edit impact: the new `build_quote_reference` symbol was not yet indexed; zero callers and zero affected processes were found, with risk reported as `UNKNOWN`, which is expected for a new symbol.
- Scoped repair gate: 25 tests passed with `REPAIR_PYTEST_VERIFIED`.
- Scoped Ruff: clean.
- Scoped strict MyPy: clean for the implementation and tests.
- The tests cover exact nanosecond boundaries, 128 fixed-seed Fraction comparisons under a hostile ambient Decimal context, resource-limit failures, first/last timestamp ties, duplicate occurrences, malformed rows, noninteger source timestamp evidence, closed-day timing, pagination defects, cross-page identity and parameter changes, tampering, corrections and all three locked pairs.

## Limits

These synthetic tests establish deterministic construction behavior only. They do not prove Massive coverage, provider finality, a holiday or boundary-age policy, actual pagination, durable raw-page storage, market volume, executable prices or validation eligibility. No network request, provider credential, database write, notification, Docker service or Hermes runtime was used.
