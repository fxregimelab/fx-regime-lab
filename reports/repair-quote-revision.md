# Packet 17.1 — quote snapshot reconciliation

## Outcome

Implemented the pure snapshot reconciliation layer in
`pipeline/src/research/quote_revision.py`. It verifies the authoritative stored
snapshot text and supplied capture pages before comparing any source content.
It does not read from the network or database, qualify a price, infer provider
event identity, or claim provider finality.

For complete acquisitions, the comparison uses a multiset of every retained
row. Multiplicity and all retained row fields matter. Page boundaries, page
order metadata, capture time, snapshot time, and implementation labels do not
enter the source-content fingerprint. The output reports the full hash-only row
delta and the separately observed reference-value changes.

For incomplete acquisitions, envelope and page integrity are still checked.
The result is marked non-comparable and every content comparison field is
`null`, so an incomplete prefix cannot be reported as removed source rows.

## Integrity and resource checks

- Each envelope has exactly `snapshot_sha256` and `unsigned_json`.
- SHA-256 is checked against the original UTF-8 text, including accepted outer
  whitespace. The code does not replace it with reserialized JSON.
- Snapshot JSON rejects duplicate keys and non-finite numbers. Provenance,
  version, reference shape, canonical UTC `as_of`, and exact typed reference
  values are verified.
- Every page passes `validate_quote_page`, and each stored reference must equal
  a fresh `build_quote_reference` result with type-sensitive equality.
- A snapshot containing mixed pair, instrument, or UTC-window pages is rejected,
  including a hash-consistent incomplete diagnostic assembled outside the
  central writer.
- Per side, inputs are limited to 1–10,000 pages and 256 MiB of asserted raw
  response bytes. Retained `body_text` is also measured directly before JSON
  parsing: 32 MiB per page and 512 MiB per side.
- Decimal parsing is exact and the output is independent of the process Decimal
  context. SHA-256 collisions between different retained row signatures fail
  closed.

## Verification

Run from `pipeline` on 27 September 2026:

```text
python -m pytest tests/test_quote_revision.py -q
22 passed in 0.11s

python -m ruff check src/research/quote_revision.py tests/test_quote_revision.py
All checks passed!

python -m mypy .
Success: no issues found in 198 source files

python -m pytest tests/test_quote_capture.py tests/test_quote_reference.py \
  tests/test_quote_storage_writer.py tests/test_quote_revision.py -q
170 passed in 3.35s
```

The tests use synthetic captures only. They independently assert multiplicity,
conservation of retained/added/removed counts, complete empty sets, metadata-only
changes, repartitioning and row reordering, boundary ambiguity, malformed and
out-of-window retained rows, incomplete acquisition behavior, all three locked
pairs, authoritative-text hashing, strict types, timestamp ordering, actual-text
resource limits, hostile Decimal context, input non-mutation, and deterministic
output.

These checks prove local deterministic behavior against the frozen contract.
They do not provide acquired market evidence, accepted coverage policy,
provider finality, production database evidence, or price qualification.
