# Independent review — JPY policy history and evidence publication

**Review date:** 1 October 2026  
**Verdict:** **PASS — bounded source and focused-test review**

I found no consequential defect in the reviewed JPY policy-history extension or the four evidence CLI publication routes.

This PASS is limited to the exact files and hashes below. It does not accept a live BIS capture, actual eight-leg source coverage, the complete test suite, a running private desk, predictive value, forecast qualification, production use, deployment or release. The coordinator owns those checks and any acceptance decision.

## Reviewed evidence

The required source-research file independently matched SHA-256 `70c2e9309ba60382aaaa9b4dd7c735de89b3956dbeb95279cb2b4436ac27024d`.

| File | SHA-256 |
|---|---|
| `docs/PRIVATE_POLICY_HISTORY_CONTRACT.md` | `03af4b421750f4d955b1753fc6d734600707983eb077aeb54288d1088a1d5542` |
| `reports/private-jpy-policy-source-research.md` | `70c2e9309ba60382aaaa9b4dd7c735de89b3956dbeb95279cb2b4436ac27024d` |
| `pipeline/src/private_desk/policy_history.py` | `edfa78e9a18bb9592f346accb9e54439431fbd8db2b1017c1ae5aea0449cca0f` |
| `pipeline/src/private_desk/report.py` | `99c7203d7c65b95cadca7abd74b436222294626542476d44f4f04c82dd948fe3` |
| `pipeline/src/private_desk/cli.py` | `9419b101c58a5d68893879b2a6d982cf97048c630517bc903fa2a37bf89b9318` |
| `private-desk/index.html` | `db8946d2fc1124de71b30c50804cafebb1fcd75340ee53cdc5096fe2820b8e6a` |
| `pipeline/tests/test_private_desk_policy_history.py` | `0c610347f20709499e8c05b1132c9fa8ebf8e27c73558efd1d87fe6897683e51` |
| `pipeline/tests/test_private_desk_jpy_policy.py` | `9690cf5fa55f874f62e564ac6c507609765e3efcb0b9b50b3d17abb824228d4a` |
| `pipeline/tests/test_private_desk_cli_publication.py` | `02bc9d456a37d18a0ed22bed54c8a4b07bfc38fc464397419faa1ff312e1878f` |
| `pipeline/tests/test_private_desk_report.py` | `aba72d266efbf16113e7449b0a534429be9bbb01c7471edbbabc89f357b5651a` |

The checkout contains a broad uncommitted repair tree, so this receipt binds its conclusion to these file hashes rather than to a commit.

## Review result

- JPY maps only to `D.JP`. The three unsupported intervals return a null instrument, including the January–September 2016 period; a numeric source cell in one of those intervals is retained as evidence but cannot become a policy feature.
- Point-target level changes keep the stable `BOJ_OVERNIGHT_CALL_TARGET` identity and remain measurable when the complete six-observation, five-FX-weekday window is present.
- The 21 September 2016 Policy-Rate Balance marker under yield-curve control and the 21 March 2024 `0–0.1%` target-band midpoint use different identities. Windows crossing that boundary are unavailable, so the move from `-0.1%` to `0.05%` cannot appear as ordinary policy momentum.
- The original seven-currency method remains `private-policy-history-v1` and reproduces from its saved method explicitly. The JPY extension is `private-policy-history-v2`, accepts at most eight distinct currencies and rejects a ninth request before capture writes.
- Original legs retain an 8 MiB response limit; JPY has a separate 16 MiB limit. Redirects remain disabled and body, receipt, request, path, length and SHA-256 controls remain fail-closed.
- JPY validation pins daily frequency, Japan area, annual-percent unit, zero multiplier, blank time format, four-decimal metadata, Bank of Japan source, end-of-period title and the exact reviewed compilation text. I independently hashed the UTF-8 compilation value as `0475bc856e35136523426884cd40d364d369b0545f343a16f47a89a325a574b7`, matching the source review.
- Policy features remain `RETROSPECTIVE_ONLY`; historical availability and vintage remain unknown, provider availability is absent, and forecast qualification remains `UNQUALIFIED`. The policy attachment does not change price research, candidates, backtests or AI qualification.
- `bidask`, `vintage`, `release` and `policy-history` write an immutable report artifact and use the shared publication path. For the current eight-pair universe, that path records and commits the journal publication and evaluates only saved later evidence. Each route preserves the earlier current-review receipt and AI output as prior evidence, marks the current receipt detached, and shows current AI as unavailable without a model call. Repeated detachment does not overwrite the archived review.
- The JPY dashboard note describes the unavailable periods and separates call-rate targets, target midpoints and the YCC short-term marker from observed funding costs and the complete policy stance.

## Checks independently run

From `pipeline/`:

```text
python -m pytest -q tests/test_private_desk_policy_history.py tests/test_private_desk_jpy_policy.py tests/test_private_desk_cli_publication.py tests/test_private_desk_report.py
98 passed in 3.70s
```

```text
python -m ruff check src/private_desk/policy_history.py src/private_desk/report.py src/private_desk/cli.py tests/test_private_desk_policy_history.py tests/test_private_desk_jpy_policy.py tests/test_private_desk_cli_publication.py tests/test_private_desk_report.py
All checks passed!
```

I also parsed `policy_history.py` and `cli.py` with Python's AST parser, inspected the four CLI branches and shared publisher calls, recomputed every reviewed SHA-256 above, and independently recomputed the JPY compilation-field hash. I did not use coordinator test output as review evidence.

## Holds that remain

- No live or cached BIS JPY body was captured or replayed in this review. Actual status, media type, bytes, source coverage and observed metadata remain for coordinator verification.
- The full pytest, MyPy, frontend checks, authenticated browser checks, API projection, actual journal replay and runtime health were not run here.
- No historical arrival clock or point-in-time vintage has been established. Observation dates cannot be used as provider-arrival or announcement timestamps.
- Nothing reviewed here shows that the policy marker improves USD/JPY forecasts, probabilities, returns, execution or live decisions. AI and forecast qualification remain unavailable or unqualified.
- R1–R5, the wider repair goal, production writes, deployment and release acceptance remain open.

No implementation, test, source data, service, credential, model, journal, production or release state was changed by this review.

## Supplemental independent runtime review — actual JPY capture and publication

**Supplement date:** 1 October 2026  
**Supplement verdict:** **PASS — bounded pinned-capture and publication replay**

No consequential discrepancy was found in the actual JPY capture or its publication. This supplement preserves the original review above and adds only measured file evidence. The requested path `.private-fx/policy-history-evidence.json` was absent; the implementation-owned current artifact is `.private-fx/policy-history/evidence.json`.

### Exact supplemental inputs

| Input | SHA-256 | Bytes |
|---|---|---:|
| `.private-fx/jpy-policy/source-verification.json` | `3a538825387d456003f43224c0d6f89c502dc462ee2495862aa610f4bd783f74` | 1,637 |
| `reports/private-jpy-policy-runtime.json` | `c5a28303b7c3fbd541a632cfb0eb6fa9aca6618577f5fab873f67f866619edbc` | 810 |
| `.private-fx/policy-history/evidence.json` | `c149224466bf98417d5bdc72fe1fda1fad3caadea889992a1a7d6206b8dd96b2` | 13,432,189 |
| `.private-fx/report.json` | `861d0799918805ee6ef571deb2968820ced36a385e5f89071c87e0a2807bd745` | 71,427,625 |
| `.private-fx/jpy-policy/policy-history-evidence.json` | `cbb53c36f98129cfd77d538b187b73507a88303926891388b7fae20f5b2070b0` | 12,251,531 |
| `.private-fx/jpy-policy/.private-fx-report.json` | `d70d94256bc4c16986d69793e596927429d5bc1619d820c5292865e428543c81` | 65,931,135 |
| Original JPY source body | `75146b9afa795f2e27e6f47b2af5303879ccd7604857512848793cedd6c5984a` | 13,861,201 |
| Original JPY receipt | `0fff019702e0cfaae71a3afe05940da391a0cdbba9f21e66dc36b82e098fb13c` | 629 |

The review receipt before this supplement had SHA-256 `a8f304b628b9e810e3d1d8c59baf5831a661877a949f0611f1c91d1a6359228b`.

### Independent replay and comparison

- I loaded the current v2 capture references and independently ran `audit_records` against the original receipt and source-body bytes. The recomputed object exactly equals `.private-fx/policy-history/evidence.json`.
- The recomputed v2 object exactly equals `.private-fx/report.json` `historical_policy`. A fresh `pair_policy_features` calculation for USDJPY exactly equals the report's saved USDJPY `historical_policy_features`: 4,642 matched policy-marker dates and 4,597 eligible five-weekday changes.
- I independently replayed the archived seven-leg snapshot with `private-policy-history-v1`. It exactly equals `.private-fx/jpy-policy/policy-history-evidence.json` and retains `RETROSPECTIVE_POLICY_HISTORY` status.
- Every original USD, EUR, GBP, AUD, NZD, CAD and CHF capture record is byte-reference identical between v1 and v2. The original receipt and body bytes independently matched their saved lengths and hashes:

| Currency | Receipt SHA-256 | Body SHA-256 | Body bytes |
|---|---|---|---:|
| USD | `5b78cc16e869f5425c34dc3c7df256f6a8f8c0e5361b68b212478d63a28abab3` | `5cab1ba9f3adff53d712d1a43ed86fca975b1a0ec4315c9c481f1989ef3bed1d` | 2,656,267 |
| EUR | `680c92b4c5c13f11b5311b3198b0098b41d02d9981445b249189c305f9b78ef9` | `550d7f2d6c7b2ce2060e6b944019ec0d36a548c4f66ef43cd4b33eab0987eb06` | 5,888,214 |
| GBP | `8220acfd0a0c89aec37d743624247cb3594b571ebac0827a1f56a622816ae6c7` | `d419c3d6e0b68034ed18f74c344368232266f092c5e3859066d1cb7e869ac531` | 2,760,065 |
| AUD | `ebe3945738b94c02af859e701ed63cdc6f8d5891c6ddc5ac76f54f023c25287b` | `5868ee48f456391f5c02b85bf3f9fa942e2749a019cffa9424f1d9ba27df4f07` | 4,860,234 |
| NZD | `218a4d716387911c2db37822fa95469b20e22324e01135072ff5749254cdb3ab` | `9d549190e796033b7c38c41821e7e86835d7515fae13b2e8527c49b0aec396a7` | 3,548,141 |
| CAD | `92d53a0ab66ba7fb56c79e15f1f3219d89f0f319196b5c2ac62fb84f22690430` | `baeda90767f94270c69efdefab29e74a7fff5497824e8e87078c857267bb198d` | 5,684,554 |
| CHF | `a8621db80d32943af59b63deb132835213a57557709975adb7803a2be49f76f5` | `4d7d537d2010af738506b856b1bfd2274d2f41461308f2f134de2ec91515a144` | 2,012,483 |

- The original JPY body contains 5,532 parsed rows, all numeric and all mapped to a supported instrument. It contains zero rows in each declared unsupported interval: 12 February 1999–10 August 2000, 19 March 2001–8 March 2006 and 4 April 2013–20 September 2016. No missing interval was fabricated or filled.
- The actual March 2024 rows are `-0.1` with `BOJ_SHORT_TERM_POLICY_RATE_YCC` on 18–20 March, then `0.05` with `BOJ_OVERNIGHT_CALL_TARGET_MIDPOINT` from 21 March. The saved feature replay therefore preserves the framework break instead of treating the 15-basis-point numerical difference as ordinary momentum.
- After removing only the policy attachment and AI-binding fields, the current report's non-policy and non-AI research exactly equals the parent report. The current report preserves the parent's `current_review`, `ai_summary` and all eight pair AI analyses as prior evidence. Current review is `DETACHED`, current AI is `UNAVAILABLE`, and forecast qualification is `UNQUALIFIED`.
- The source-verification and runtime records agree with the independently recomputed report, evidence, JPY source and parent hashes. I did not adopt their PASS labels as the basis of this verdict.

### Supplemental holds

- Historical provider arrival and vintage remain `UNKNOWN`. A current capture cannot establish when past observations were available.
- The JPY marker and USDJPY retrospective features remain `UNQUALIFIED` for forecasting. This replay does not show predictive contribution, profitable execution, or live decision quality.
- I did not fetch any source, call a model, start a service, rerun the full suite, inspect broad research, or write a report, journal, source, capture or production record. Coordinator acceptance, wider repair gates, production and release remain outside this supplement.
