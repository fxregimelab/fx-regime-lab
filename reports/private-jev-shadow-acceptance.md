# Jev adapter and authentic passage review

1 October 2026. The optional adapter and source-capture layer are implemented and directly tested. Jev has made **zero actual requests**: the process has no `TYPESAFE_API_KEY`, and the adapter defaults to disabled. No semantic accuracy, speed, billed cost or trading improvement has been measured. The private desk still has zero qualified trades.

This receipt covers `docs/PRIVATE_JEV_SHADOW_CONTRACT.md` revision 1. It advances the source-review experiment in `docs/PRIVATE_JEV_EVALUATION_CONTRACT.md`; it does not complete that experiment or R1–R5. The shared checkout remains based on `9fa150538d08ab5a2a6c587976552944f47a724d`, with earlier uncommitted work preserved.

## What was built

`pipeline/src/private_desk/evidence.py` captures bounded original responses from the seven allowed central-bank hosts. It saves raw bytes, selected article text, extraction rules, exact UTF-8 text offsets and immutable receipts. Replay re-extracts the original and compares every saved span. Invalid hosts, redirects, unavailable sources, unsupported encoding, challenge pages, changed bytes and forged receipts fail closed. These spans cover selected article blocks, not a guaranteed complete document. Supplied publication dates remain publisher-feed claims; the actual receipt clock is neither historical arrival nor verified vintage.

`pipeline/src/private_desk/jev_shadow.py` builds a deterministic token-overlap shortlist from replay-verified spans. It saves the full span order, candidate counts, omissions, exact request and five narrow questions: relevance, event family, stated currency mechanism, claim support and selected source span. This baseline is not BM25. Literal claim absence is not a semantic verdict. Even a structurally valid provider result remains `INDETERMINATE` for accepted semantic support, `UNQUALIFIED` for forecasting and subject to human review.

All model HTTP calls stay in `pipeline/src/ai/client.py`. The new adapter pins `jev-1.13.0`, accepts only the declared Noul and Choice answers, checks complete finite distributions, selected choices, model identity and token counts, and rejects extra or partial answers. It bounds the UTF-8 request to 25,000 bytes and response to 65,536 bytes. An enabled packet permits one attempt, with a twelve-second requests transport timeout, redirects disabled and no retry. That timeout has not been measured as a hard wall-clock deadline. Failures preserve the deterministic packet with sanitized status; no provider body or key is exposed. Missing billed cost stays unknown.

The separate CLI requires an explicit `--enable` and a process-level key for a live call. Normal research, refresh, report replay, pair ranking, probabilities, eligibility and the dashboard do not invoke Jev. The existing DeepSeek review is unchanged. No TypeSafe SDK was installed, and no other environment file was searched for a TypeSafe key.

## Actual sources and shadow receipts

Eight documents were attempted, below the twelve-document cap. Six yielded replayable article blocks; two returned HTTP 403. This is a small integration sample, not a labelled evaluation corpus.

| Currency | Actual source | Result |
|---|---|---|
| USD | Federal Reserve, 16 September policy statement | Available; one span |
| EUR | ECB, 30 September speech | Available; 21 spans |
| GBP | Bank of England, 17 September policy summary/minutes | Available; 41 spans |
| CAD | Bank of Canada, 2 September policy decision | Available; four spans |
| CHF | Swiss National Bank, 24 September release | Available; four spans |
| CAD | Bank of Canada, 10 September recruitment notice | Available; two spans; intended non-policy control |
| AUD | RBA, 1 October financial-stability release | HTTP 403; failed original retained |
| NZD | RBNZ, cash-services discovery page | HTTP 403; failed original retained |

The governance notice is a test candidate, not a human-labelled semantic result. Several policy documents are older than the current headline freshness window; they are retrospective examples only. No proxy was represented as an original bank response. All six successful receipts replayed from raw bytes. Their URLs and supplied publication instants were independently compared with the pinned source report.

Six disabled shadow evaluations then used those actual sources. The USD claim was literal source text; the other five deliberately proposed an unsupported next-week currency forecast. Every evaluation saved its deterministic packet, recorded `attempted=false` and returned indeterminate support. The two unavailable sources stayed unavailable. No model was asked to label either the positive or negative examples.

The source manifest is `.private-fx/evidence/manifest.json`. The integration receipt is `.private-fx/jev-shadow/verification-summary.json`; it lists the six immutable shadow receipts and failures. The latest shadow pointer refers to the CAD governance case and replays offline.

## Review and direct checks

The capture worker independently reviewed the root adapter's request, schema, replay and failure controls and ran the then-current 38 adapter tests. Root independently reviewed source extraction and receipt replay, found a metadata-binding gap and had it repaired: the supplied receipt must match its immutable saved file and recomputed identity before raw/text/span checks can pass. URL, publication, HTTP and clock tampering now fail. Root added integration controls that use genuine captured fixture bytes, rather than replacing source verification with a stub. A structurally valid mocked provider answer still cannot grant accepted support or a trade probability.

Final direct verification on the recorded code hashes:

- 75 focused tests passed: 25 source tests and 50 adapter/integration tests.
- 2,514 full pipeline tests passed in 62.49 seconds; Ruff passed and MyPy checked 260 source files. Transcript: `reports/private-jev-shadow-checks.txt`.
- Actual separate shadow replay printed `PRIVATE_JEV_SHADOW_REPLAY_OK` with `DISABLED / SHADOW_DISABLED`.
- Full current-report replay passed all seven daily, reference, session and bid/ask comparisons, plus vintage, release, policy, current review and portfolio audits; `PRIVATE_DESK_REPLAY_OK`.

Controls include forged source metadata, raw/text/span/path hashes, changed question/baseline definitions, rehashed packet tampering, missing keys, redirects, timeout, oversized bodies, key echoes, malformed UTF-8/JSON, aliases, wrong returned models, incomplete answers and invalid distributions. Mock provider tests prove local handling, not live API compatibility or semantic quality.

GitNexus impact was attempted before symbol edits. Its database version 42 could not be read by the available version-40 runtime, so every graph result was `UNKNOWN`. Manual traces bound the new capture module to the shadow consumer and the new central-client functions to the explicit shadow command; graph-certified safety is not claimed.

## Preserved research and local service

The source manifest pins the earlier immutable report at SHA-256 `7b075844f1d1ad7594e13b4284dde06f24d0f2bbb003a2023c3dc747a73638da`; that original remains intact. During this packet a separate refresh produced a newer current report, SHA-256 `a15080e656b5ee021855719a116d6293ddf0bf5f7a2819389e52db08b9377f43`, generated at `2026-10-01T15:54:21.457627+00:00`. The actor that initiated that refresh is unverified. This packet did not invoke normal research or refresh, and its shadow evaluations preserved the newer report byte-for-byte. Both versions were retained; the older one is not described as the latest report.

The newer report also replayed successfully. Its seven candidates abstain, with null probabilities, and its daily backtests contain 2,000 calls in total. Those calls do not establish a qualified profitable policy. The quantitative engine hash remains `81d3e42aec13b9b947831fdc1e30646a11863220f3cb629806824096b4c12c6a`.

The local service remains at http://127.0.0.1:8765. Final health verification found Python PID10948 listening on loopback and the root page returned HTTP200. This packet changes no dashboard UI; the prior browser evidence belongs to the earlier UI review. No new browser feature is claimed. No Docker or heavier Hermes component was required or started. No broker action, production write, migration, commit, push or deployment occurred.

## Bound files

| File | SHA-256 |
|---|---|
| `pipeline/src/ai/client.py` | `2c7399464ec914f61414276f7ba2e937c334edf3766aad32c44361cec0042488` |
| `pipeline/src/private_desk/jev_shadow.py` | `48094fe494ba63942a8826155e4f9f2e1fc957533e8d1a859538a1e59608c3e2` |
| `pipeline/tests/test_private_desk_jev_shadow.py` | `d8f281a638ef17580c663ddd4294f4d16355d83001c85798776b02567bc80be8` |
| `pipeline/src/private_desk/evidence.py` | `cbe95156cea6ad4691362499c3bcfb646524d5d5fbb7b9c6a53c3f43df6760a1` |
| `pipeline/tests/test_private_desk_evidence.py` | `d108e6bc5f7a57ecbb1bc2a356560ef183f09f24925f2c93d9b3bcb34e025e5b` |
| `reports/private-evidence-capture.md` | `de329dbcade2d543bdf5a6492f8696a7f7c074335aa003b05a2081628ee75730` |
| `reports/private-jev-shadow-checks.txt` | `ba12991f499df87fc0e4ee6c55bc518d7c83e15ccc3d299215546aebf6a155cf` |
| `.private-fx/evidence/manifest.json` | `4d992195362f051619da4fddafa666db61b53740fc491646cfd60766571157dc` |
| `.private-fx/jev-shadow/verification-summary.json` | `661913ab8f64051493b94db3ae99a0dcf26025be9f7845ee9f2cc6bb5485b9bf` |

## Remaining acceptance

This scope has two manual gates met and five unmet gates, with no abandonment. Four runnable gates lack inspected checker approval and bound automatic evidence; the parent integration gate remains pending that certification. Direct command success is recorded separately. Exact leaf leases remain held. There is no whole-scope or whole-goal completion claim.

The [Unlazy skill](C:/Users/sakha/.codex/skills/unlazy/SKILL.md) states: “Only the user's explicit, inspected approval may cross that boundary.” This applies to executing inherited `CHECK` lines through its approval store, not to the owner's already-authorized direct development checks. No such checker approval was supplied, so the successful direct commands have not been converted into automatic certification. Status inspection confirms two met/five unmet; ledger lint has no errors and four expected warnings for the manual review gates.

The next research step is a frozen source-event corpus with at least 240 groups and independent human labels, chronological development/validation/test separation and measured comparisons against deterministic retrieval/support baselines. A live key alone cannot supply those labels. Account-visible model/terms, actual latency, billed cost, unsupported claims, hostile-text behavior and thin class coverage need measurement before assistive promotion. Historical forecasting additionally needs authentic availability/vintage, expectations and surprises, grouped net-after-cost trials and forward confirmation. Jev confidence cannot become an FX win probability. R1–R5 and public repairs remain open.
