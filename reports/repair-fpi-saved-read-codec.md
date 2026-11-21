# Saved-read pure codec — leaf 30.1

28 September 2026. Based on shared checkout `codex/frontend`, HEAD `9fa150538d08ab5a2a6c587976552944f47a724d`, with existing repair changes preserved. This leaf adds only the pure saved-read module, its focused tests and this report. No database, provider, runtime, central writer, existing codec or selector was changed. No commit or deployment was made.

The module implements the frozen policy, request and manifest objects, both exact receipt validators and `verify_fpi_admin_read_originals` specified in `docs/FPI_SAVED_READ_CONTRACT.md` and `docs/FPI_SAVED_READ_API.md`.

Constructors check canonical ASCII JSON, duplicate and exact keys, primitive types, depth before JSON decoding, document limits, hashes, scope arithmetic, compact identities, whole supporting membership metadata, diagnostic membership, artifact coverage, storage times and the compact qualification view. All retained outcomes remain `UNVERIFIED`, ineligible and without a feature. A manifest proves internal consistency, not database origin, complete SQL discovery or source authenticity.

Original verification snapshots the exact primitive rows, requires exact identity sets, checks individual and aggregate sizes before body decoding, compares storage timestamps by their accepted UTC instants and matches full event documents. It validates each artifact once and calls the existing complete reference builder once. Full retained reference equality catches missing support that a compact document alone cannot prove. No source/value/record-body hash is presented as verified until the original boundary checks it.

## Verification

- `node ../scripts/repair/verify-pytest.mjs tests/test_fpi_saved_read.py`: 86 passed; `REPAIR_PYTEST_VERIFIED`.
- `python -m ruff check src/research/fpi_saved_read.py tests/test_fpi_saved_read.py`: all checks passed.
- `python -m mypy src/research/fpi_saved_read.py tests/test_fpi_saved_read.py`: strict check passed on both files.
- `leaf-30.1:G1`: automatic evidence passed. Output SHA256 `fdca3dedbc61aa74fa2ba0339492f1948596f966feb428092ef2b43972c79c6b`, 206 bytes. Current leaf count: one met, one unmet, zero abandoned. G2 belongs to the parent and remains pending.

The focused controls cover altered or omitted originals and projections, duplicates and extra rows, immutable-object forgery, exact receipt fields, invalid UUIDs and times, both lower-bound clamps, India overflow witnesses, future evidence, all eleven configurable count/byte dimensions at and below their fixture boundary, actual oversized artifact input, depth-before-decoder rejection, and propagation of system exceptions. Authored Monthly fixtures retain support-only dates. Alternate unqualified parsers and same-value memberships remain candidates even when policy intent specifies Latest. Failure-only captures cannot extend diagnostics beyond the declared window.

The measured shared-capture case uses two parse originals and three artifacts: one capture validation, two parse validations, three artifact validations, one bulk reference build and one qualification-view reconstruction during the originals call. Mutation of caller rows during artifact validation cannot alter the saved primitive copies.

Pinned golden vectors include the contract's policy/request/empty reference/empty qualification and independently serialized complete and overflow fixtures. Complete is 2805 bytes with SHA256 `d89e3d48d849e9284b0c70e2310a71a218e4d02211d8c6dfe502a3b8be998852`; overflow is 2104 bytes with SHA256 `fdfd74e271e5857a413c738e1766440ad0b0b8cb5a612c419e2f3c9156f4872b`. Expected hashes were computed from authored fixture documents without the new codec's canonical/hash functions. They are synthetic consistency evidence, not retained production reads.

## Review passes and remaining boundary

1. Implemented the complete API and both compact/original consistency boundaries.
2. Reviewed scope and administrative authority: no policy filtering, recursive diagnostic expansion, support-date heads, feature production or trust promotion.
3. Challenged corruption, exact types, clocks, resource checks, forged objects and row mutation. The parent identified the artifact minimum-body requirement; it is now one byte, with a fresh-rehashed zero-body negative control. Capture and artifact document sizes also match their compact metadata and base64 length.
4. Formatted the files, reviewed the final checks and reran the gate. The final local pass found no further issue.

GitNexus upstream impact was requested before implementation for all 29 module symbols and 19 test symbols. Every new symbol was absent from the index and returned `UNKNOWN`. This is not evidence of zero callers or zero risk. No index rebuild was performed.

Source SHA256: `4bbdfc64b3f916418d4a3b22a7d6abe67b44daa4656ea691b2ad062bb3679f8b`.
Test SHA256: `8bfa2ef8abc1310c5b92939799ca7219dc1063b2af4f0755e55f2afec6010f3e`.

Parent re-verification, the real saved-read SQL scenarios, writer/loader integration and the full regression remain separate work. This report does not close SR01–SR26, establish protected execution or acquisition trust, activate FPI, or complete the wider repair.
