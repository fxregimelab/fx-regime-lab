# Retained FPI read references — leaf 28.1

The pure codec now builds complete, compact references from retained capture and parse documents. The frozen interface in `docs/FPI_READ_REFERENCES_CONTRACT.md` is unchanged: `FpiReadReferences(reference_sha256, document_json)` and keyword-only `build_fpi_read_references(captures=..., records=...)`.

The builder copies exact primitive fields, checks input counts and original-document limits before decoding or SHA-256 hashing, rejects contradictory identities, and validates each distinct capture and parse once. It requires exact capture dependency coverage. Every validated membership remains present, including all 31 dates in the synthetic Monthly test. References contain only the specified metadata and hashes; retained source and numeric documents remain necessary for later use.

The new boundary preserves existing restoration checks: parse time cannot precede receipt, successful results require HTTP 200 and the canonical definition, and reporting dates cannot follow the receipt date in India. It also preserves the selector's timestamp representability limit at UTC+05:30. Output is detached, sorted, canonical ASCII JSON with an exact SHA-256. Membership and output-size limits reject before aggregate construction.

## Observed local checks

- `python -m pytest -q tests/test_fpi_read_references.py tests/test_fpi_parse_record.py`: **124 passed**, comprising 54 new reference cases and 70 existing codec cases.
- `python -m ruff check src/research/fpi_parse_record.py tests/test_fpi_read_references.py`: passed.
- `python -m mypy src/research/fpi_parse_record.py tests/test_fpi_read_references.py`: passed, two source files.
- Gate lint: passed, with the expected warning that parent-owned G2 is a manual gate.
- `leaf-28.1:G1`: passed through its declared Node pytest wrapper, using `--cwd D:/Projects/fxregimelab`. Output fingerprint `788f6579640d5821558f16bea5720b562a2b6eead29f398bbe8097f7d4fc8d43`, 207 output bytes. At worker handoff, **one gate met, one unmet, zero abandoned**. G2 remains parent-owned; the whole ledger therefore exits 1.

Tests independently serialize expected reference documents and compare every field and hash. They cover shared captures across 40 distinct parser results, one capture validation and 40 parse validations despite repeated entries, successful and failed results, input permutations, complete Monthly membership retention, earliest/latest supported dates and times, India midnight, invalid source/body/member hashes, exact types and forged fields, missing/unused dependencies, and input mutation after snapshots.

Resource tests use actual 7,000,001-character capture text and 4,000,001-character parse text, 2,049 repeated inputs, and a combined budget one byte below the originals. Patches make any premature JSON decoding or SHA-256 hashing fail the test. The exact 2,048-entry bound and controlled exact byte limits pass. Controlled membership and reference-document limits check values below, at and above the boundary, including empty output. These are engineering limits, not source-completeness evidence.

The initial check found four test line-length issues and MyPy narrowing/import/tuple-annotation errors; these were corrected before the passing run. A first gate status command incorrectly combined `--status` with execution-only `--cwd`; the corrected status call succeeded. The normal G1 call found no cached oracle approval and did not execute it. After inspecting the ledger and wrapper, the authorized scoped check ran with explicit approval and passed.

## Preservation and limits

GitNexus upstream impact calls for the new builder, record class and test module returned `UNKNOWN` because those targets were not indexed. No callers or affected processes were available from that index. No index rebuild was performed.

The original codec was already untracked in the shared dirty tree. Before editing, its SHA-256 was `5b3116bf7ce6beb70fc1ab164aa6f5d4fe43cefb532ff9fb15df6deb1b0026f9`. Removing the added class/builder and constants and restoring only the extended datetime import reproduces those exact original LF bytes and that SHA-256. A formatter's temporary single-line change to the old restoration function was reverted before this preservation check. No existing function or v1 type changed.

Final implementation SHA-256: `c3d6a77b4218e464d3d17df7babe321f292813346a6f361ff236db3bc50792f8`.

Final tests SHA-256: `c83b7efa4234d8776052d51e2472ead13e0ff4e1ac0a155c927ffd21545944fd`.

The worker changed only its implementation, new test file, this report and its gate evidence. No SQL, provider, credential, AI or runtime access occurred. No database service was started. No commit, push or deployment occurred. Full pipeline checks and independent original-report verification remain parent responsibilities. This addition does not establish a database snapshot, acquisition order, source authenticity, executed-code trust, consumer eligibility or FPI activation.
