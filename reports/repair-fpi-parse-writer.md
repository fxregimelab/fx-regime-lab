# Leaf 24.1 — durable FPI parse codec and writer

## Result

The Python leaf now retains two kinds of private evidence:

- exact parser or selector artifact bytes in a canonical `fpi-implementation-artifact-v1`
  envelope;
- a complete successful or failed FPI parse in a canonical `fpi-parse-record-v1`
  envelope, including every canonical INR day and its independently retained USD source
  evidence.

The codec reconstructs frozen input objects instead of trusting their attributes. It checks the
capture, parser and definition identities; parse content hash; date order; value and membership
hashes; canonical INR documents; exact seven-category USD documents; conversion-rate spelling;
and route, subtotal and total rounding bounds. Failed parses retain only a bounded machine code.
They cannot carry partial days or source documents.

`archive_fpi_artifact` calls only `append_fpi_artifact`. `archive_fpi_parse_result` calls only
`append_fpi_parse_result`. Both validate before client access, require exact receipts, return
detached data and replace transport/provider exceptions with bounded messages.

This work does not execute an artifact, prove that its dependencies are complete, qualify a
parse, authenticate an NSDL response, prove historical availability, read a database or save a
decision snapshot.

## Four-pass review

1. Implemented the complete artifact, parse-record, restoration and writer interfaces from the
   frozen contract.
2. Re-read the codec against the existing capture, parser, observation and selection identities.
   Added reconstruction of each `FpiParsedDay`, not only the containing `FpiParseResult`, and
   retained the exact source USD document rather than deriving USD from INR.
3. Tested malformed hashes, fields, primitive types, duplicate keys, noncanonical number text,
   negative zero, broken reconciliation, incomplete source evidence, forged frozen objects,
   wrong captures, reordered receipts, excess timestamp precision and sanitized failures.
4. Ran focused tests, scoped lint and type checks, checked LF line endings and reviewed the final
   diff. The final improvement pass found no further scoped change.

## Verification

- `node ../scripts/repair/verify-pytest.mjs tests/test_fpi_parse_record.py`
  - `70 passed in 2.63s`
  - `REPAIR_PYTEST_VERIFIED`
- `C:/Python314/python.exe -m ruff check src/research/fpi_parse_record.py src/db/writer.py tests/test_fpi_parse_record.py`
  - `All checks passed!`
- `C:/Python314/python.exe -m mypy src/research/fpi_parse_record.py src/db/writer.py tests/test_fpi_parse_record.py`
  - `Success: no issues found in 3 source files`
- UTF-8/LF check over all three owned Python files
  - `UTF8_LF_VERIFIED`
- `git diff --check` over the owned Python paths
  - exited zero

The first focused run passed 27 tests and failed two test-harness expectations. One expected an
empty failure code to survive the existing `FpiParseResult` constructor; the other required one
specific error phrase after a forged day instead caused an earlier duplicate-date rejection. The
second run passed 28 tests and exposed the remaining empty-code message expectation. The codec
was tightened to reject invalid machine codes before reconstruction, after which the gate passed
29/29. A later adversarial expansion initially passed 63 tests and failed five because a receipt
mutation assertion was placed in the wrong test block; moving that assertion back to its owning
test produced the final 70/70 pass. These were local failed attempts; no database or provider call
occurred.

## Source snapshot

Base commit: `9fa150538d08ab5a2a6c587976552944f47a724d`

| Input | SHA-256 |
|---|---|
| `docs/FPI_PARSE_STORAGE_CONTRACT.md` | `5a6544a183855178501db2a4468de14f9d971e828cad8de33e49c67c4a610a12` |
| `docs/FPI_SELECTION_CONTRACT.md` | `8b136ba9ee6c4c968832baa89057313d2cc7a4c674e458819930af5432849a5a` |
| `pipeline/src/research/fpi_selection.py` | `ab5e524ea027a66e7518d3784692b2a107c6f78cb994beda99c599ac439dab06` |
| `pipeline/src/research/fpi_capture.py` | `56c9ca17b7d6772306a4bc66615e8990985539bd80a787697557889db0d87d4a` |
| `pipeline/src/research/fpi_parser.py` | `afe9fdc67c1fabe27f51dcf29478c73574a837ddd0b4285eba61c2ff9a94cabe` |
| `pipeline/src/research/fpi_observation.py` | `4582bbe61ebf5f0a0d4fb6fb2f5380c5bbb24feeb4a74ce56f93a9350542f8bd` |

The shared `writer.py` already contained uncommitted repair work outside this leaf. This leaf only
adds the two imports, one receipt-timestamp helper and the two FPI archive methods near the
existing capture writer. No unrelated writer changes were reverted or claimed.

## Impact and acceptance state

Pre-edit GitNexus impact calls for `archive_fpi_capture`, `archive_fpi_artifact` and
`archive_fpi_parse_result` returned `UNKNOWN` / target not found under the known index mismatch.
The index was not rebuilt, and this is not a no-impact result. The later change scan reported
`CRITICAL` across 93 files, 614 symbols and 293 flows because it measured the whole shared dirty
repair checkout. It cannot isolate this leaf's blast radius.

Leaf gate G1 is met by the focused verifier. G2 remains pending because it belongs to the parent:
independent identity, canonicalization, source-reconciliation and integration review. No commit,
database access, service startup, credential read, network/provider request, AI call or deployment
was performed.
