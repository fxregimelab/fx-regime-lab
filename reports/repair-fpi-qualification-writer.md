# FPI qualification writer — leaf 27.1

The central writer now exposes `append_fpi_qualification(command: FpiQualificationCommand) -> dict[str, Any]`. It rebuilds the command with the accepted v2 canonical decoder, checks every original field and cached identity with exact primitive types, and rejects altered frozen objects before acquiring a client. The request uses one `append_fpi_qualification` RPC with only `p_command_id` and `p_document_json`. It neither fetches heads nor retries against a different predecessor.

The response must have the exact seven receipt fields and version `fpi-qualification-receipt-v2`. The writer decodes the full event document and binds its complete command, identity, ordinal and canonical UTC timestamp to the submitted command and receipt. It requires an exact boolean for `inserted` and an exact integer in the signed-bigint range for the ordinal. It returns a new plain dictionary. Client, transport and receipt failures use fixed messages without rendering the underlying exception or private payload. Cancellation and other base exceptions still propagate.

Verification on 28 September 2026:

- The focused writer suite passed all 149 synthetic cases. With the existing 136 qualification cases, the declared G1 command passed 285 tests. The cases cover every scope/action, resolution witnesses, first/retry receipts, boundary ordinals and years, forged fields/caches, exact types, altered command meaning with freshly recomputed hashes, noncanonical and oversized documents, missing/extra fields, invalid witnesses, error privacy, and cancellation at all six checked boundaries.
- `python -m ruff check src/db/writer.py tests/test_fpi_qualification_writer.py` passed from `pipeline`.
- `python -m mypy src/db/writer.py tests/test_fpi_qualification_writer.py` passed for both files from `pipeline`.
- The unlazy self-check was rerun with `--cwd D:/Projects/fxregimelab`. G1 has current automatic evidence: definition SHA-256 `d7b9074610c608a6ee14d2e006360ad76ffc8da6f617861b8995a3b9b709c0f0`, output SHA-256 `c30375ed4776264cffd3b03eb98462effb38c2e932c7401d40ca532cad839dbf`, 369 output bytes, zero check exit, expected marker matched. At handoff, one gate is met, G2 awaits independent parent review, and none are abandoned. Gate lint passed with its expected manual-G2 warning.
- Removing just the new import block and new function from the final writer bytes restores the captured pre-change SHA-256 `33a214b18ffbc85ce71601b8817cb850221d40cab67ab211c5634668338112a0`. Existing writer changes are preserved exactly.

GitNexus impact was requested before edits for the new writer function and all four new test functions through the repository-local CLI. Each returned target-not-found and `UNKNOWN` risk. Direct callers and affected processes could not be measured for these new symbols; this is a coverage limit, not a zero-impact result. No existing function or codec was changed, and no index rebuild was attempted.

The initial test attempt had oversized generated pytest case names that caused two setup/teardown error pairs. Explicit bounded case names corrected that test-fixture issue. The final runs above have no such errors.

Source snapshot: Git HEAD `9fa150538d08ab5a2a6c587976552944f47a724d`, with the existing uncommitted repair work preserved. Final artifact SHA-256 values:

| Artifact | SHA-256 |
| --- | --- |
| `pipeline/src/db/writer.py` | `59c0b9c8981fe03b1918c6636a789c9c04e9bd386a4de287ebf091e32598a961` |
| `pipeline/tests/test_fpi_qualification_writer.py` | `314505f00b173131a9fc463ff5d345748f671862203af91d309a769bbf06fadd` |
| Existing `pipeline/src/research/fpi_qualification.py` | `004e32dc8fe03710f80fb95da41add7b13bc395a08c5e59f3bfa1c6010953a28` |
| Frozen storage contract | `648803534d956b4704763daffed266445829e60340c10d77750f8a26de08aa58` |

These checks use mocked clients and synthetic records. They do not prove database transactions, current or historical database visibility, source authenticity, execution trust, or production policy. An ACCEPT receipt does not enable consumption. No runtime was needed or started; no provider, credential, database, AI or production access was used. No commit, push or deployment was performed. SQL integration and the parent's negative-control review remain outside this leaf's self-verification.
