# Seven-currency policy history — bounded verification

1 October 2026. Contract: docs/PRIVATE_POLICY_HISTORY_CONTRACT.md revision 2. Larger goal remains ACTIVE.

All seven current BIS histories are captured and connected to a separate authenticated research panel. There are 57,566 numeric source observations and 3,408 missing observations from 5 January 1999 onward. No current trade is qualified. Existing price results and probabilities are unchanged. Historical release, arrival and vintage evidence remains unknown.

## Actual source coverage

Requests cover 1999-01-05 through 2026-09-30, one daily region per currency. Seven HTTP 200 CSV originals and seven immutable receipts were saved, with no failed legs. Raw bodies total 27,409,958 bytes. A requested end date is not the last observed date. Numeric counts include source weekends when supplied; pair features use FX weekdays only.

| Currency | Numeric rows | Missing rows | First numeric | Last numeric |
|---|---:|---:|---|---|
| USD | 10128 | 0 | 1999-01-05 | 2026-09-28 |
| EUR | 10098 | 32 | 1999-01-05 | 2026-09-29 |
| GBP | 7013 | 231 | 1999-01-05 | 2026-09-28 |
| AUD | 7021 | 0 | 1999-01-05 | 2026-09-24 |
| NZD | 8859 | 1245 | 1999-01-05 | 2026-09-25 |
| CAD | 7216 | 1895 | 1999-01-05 | 2026-09-28 |
| CHF | 7231 | 5 | 1999-01-05 | 2026-09-29 |

Units are annual percentage rates: BIS code 368, multiplier 0. M/NaN observations remain missing. F means the confidentiality category “Free”; it does not establish a final vintage. The coordinator independently checked those meanings in the original [BIS structure response](https://stats.bis.org/api/v2/structure/dataflow/BIS/WS_CBPOL/1.0?references=all).

## Instrument and negative controls

The parser requires exact reviewed COMPILATION and SOURCE_REF strings. It validates the complete witnessed column schema, dimensions, units, statuses, ordered canonical dates, window/receipt limits, finite rate bounds of −10 to 100, and consistent metadata. Equal same-date observations count once; conflicting values reject the leg. Original receipt/body/request/hash/path mismatches fail closed. Future requests and receipts fail closed. The maximum window is 31 calendar years; leap-day anniversary handling is tested. Cache refresh retains previous originals and receipts.

The registry covers the ECB fixed/minimum-bid/fixed/deposit representations, BoE repo/Bank Rate, New Zealand overnight/OCR, and Swiss discount/target-range midpoint/policy rate. USD, AUD and CAD retain their BIS instrument identity within this window. The source report separately records the US target-form and Canadian operating-convention events. Current CSV OBS_PRE_BREAK fields are empty, so the registry provides the splice guard. Definitions were checked against the [BIS documentation dated 24 September 2026](https://www.bis.org/statistics/cbpol/cbpol_doc.pdf). The coordinator independently matched its SHA-256: `66919c739f2393e854d81000ee02aa8814dfb12ee92a7731f37d43df064b69c8`.

Actual EURUSD negative control: a naive five-weekday difference change from 2024-09-11 to 2024-09-18 is −0.75 percentage points. Its endpoints cross ECB_MRO_FIXED to ECB_DEPOSIT_FACILITY. The repaired feature returns null and INSTRUMENT_DEFINITION_BREAK. The naive number combines different policy representations and is rejected as a comparable policy change.

A separate red test showed the former 31×366-day bound accepted one day beyond a 31-year anniversary. The calendar-year guard now rejects that date and handles 29 February correctly. Deterministic controls cover missingness, no filling, pair signs, absent legs, row break markers, unknown instruments, immutable capture failure, definition drift and a future-value perturbation.

## Pair features

Level = base marker minus quote marker, in percentage points. A five-weekday change requires six exact matched weekday observations and one stable instrument in each leg throughout the window. Every feature is RETROSPECTIVE_ONLY, with historical provider availability and vintage absent and forecast qualification UNQUALIFIED.

| Pair | Matched numeric dates | Valid five-weekday changes | Definition-break windows | Last matched date |
|---|---:|---:|---:|---|
| EURUSD | 7234 | 7209 | 15 | 2026-09-28 |
| GBPUSD | 7003 | 6201 | 5 | 2026-09-28 |
| AUDUSD | 7020 | 6294 | 0 | 2026-09-24 |
| NZDUSD | 7160 | 6945 | 5 | 2026-09-25 |
| USDCAD | 7215 | 7124 | 0 | 2026-09-28 |
| USDCHF | 7229 | 7194 | 5 | 2026-09-28 |
| EURGBP | 7004 | 6192 | 20 | 2026-09-28 |

No forward filling is used, including holidays. Raw weekend rows remain in the complete source audit but are excluded from weekday features. A snapshot captured now cannot prove what an earlier trader could observe. These differences are not two-year yield spreads, carry or surprises. They do not enter model trials, calibration, candidate qualification or AI inputs. Dashboard refresh reads saved policy evidence after the existing AI step. Source or feature failure is isolated and leaves price research intact.

## Preservation and performance

The previous quantitative report and current report were compared after removing only historical_policy, per-pair historical_policy_features and policy_history_updated_at. All remaining values are exactly equal: price/reference/session/bidask/vintage/release/portfolio results, source captures, candidates, news and AI. The price engine hash remains `81d3e42aec13b9b947831fdc1e30646a11863220f3cb629806824096b4c12c6a`.

The complete saved report is 56,642,633 bytes. GET /api/report omits full policy rows from its response only. It retains currency summaries, original source metadata/receipts, counts, last matched markers, six recent pair rows and complete-history break counts. The actual authenticated response was 8,433,243 bytes and fetched in 515 ms in the final local browser run. These are observed sizes and one workstation measurement, not a throughput benchmark. Disk bytes remain unchanged. API controls compare every projected field with its original and verify that other research fields remain identical.

## Direct verification

- 77 focused policy/report/API tests passed.
- 2,386 full pipeline tests passed in 52.90 seconds; Ruff passed; MyPy passed over 254 files.
- Pinned daily/reference/session/bidask/vintage/release/portfolio/policy replay passed in 10.45 seconds, with no network or AI request.
- Four static UI groups passed, including nulls, failures, untrusted text and compact-history counts.
- The actual browser visited all seven briefs, read seven policy-history rows, checked values and complete-history break counts, reloaded with authentication, and exported 2,000 trade rows.
- Desktop 1440px and mobile 390px screenshots were visually reviewed. The initial three-column mobile metrics were corrected to two columns and the browser run repeated. Document/client widths are both 390. An injected 900px overflow control made the detection oracle fire.
- Refresh without CSRF returned 403 and did not start work. Report/status/export after logout returned 401. Console failures corresponded to expected authorization responses; no application script failure was observed.

Transcripts: reports/private-policy-history-checks.txt and reports/private-policy-history-browser.txt. Screenshots: output/playwright/private-policy-desktop.png and output/playwright/private-policy-mobile.png. Live service: http://127.0.0.1:8765, recorded PID 31624, confirmed Python private_desk.cli serve, loopback listener and root HTTP 200. The browser test session is closed; the owner desk remains running. No Docker, PostgreSQL or heavy Hermes service was needed or started. Hermes MCP remains separate.

## Review boundary and remaining work

The independent source reviewer owned only reports/private-policy-source-research.md. Its bounded manual gate was reviewed, the native wave returned, and its exact lease was released. The implementation ledger has three manual gates met and four automatic gates pending bound checker approval; root integration remains unmet. No abandonment, --approve or whole-scope release occurred. Direct command success is not checker certification. The [Unlazy skill](C:/Users/sakha/.codex/skills/unlazy/SKILL.md) says: “Only the user's explicit, inspected approval may cross that boundary.”

GitNexus query/impact/API-impact calls failed with storage version 42 versus reader 40. Risk was UNKNOWN, not zero. Manual caller review limited changes to private capture, report attachment, offline replay, authenticated report presentation and private tests/UI. The protected CSV still reads original saved trade data. No commit was attempted.

R1–R5 and the public repair register remain open. Policy history advances R2 coverage but does not complete it. The next required evidence is observation-specific historical release/arrival and vintage for both legs, followed by separately declared expectations/surprises and independent predictive trials. No positive expected-return or 60–70% success claim is made. The fixed overlap study remains −54.28R on 1,198 accepted counterfactual calls; all 2,000 fold probabilities remain unavailable and eligible current trades remain zero. No broker action, production database write, migration, commit, push or deployment occurred.

## Final artifact hashes

| Artifact | SHA-256 |
|---|---|
| pipeline/src/private_desk/policy_history.py | `d3e469ec2be0bb8da16366905c528de4160c6e1a5cb3cf956610cc903d10a525` |
| pipeline/src/private_desk/report.py | `4d4037d3efd74b1ec669beb9f36e4ee91b223b829c4386fa8a0ff460737f7cc8` |
| pipeline/src/private_desk/cli.py | `164092c8c1049e10e84e90b8386d98550901717abc1b46178c8a2fe62b9ea86d` |
| pipeline/src/private_desk/api.py | `d3c9e712f73fa61e7bfc2c06b6586af94ae3c44beb12598b6209aea166ff18c2` |
| pipeline/tests/test_private_desk_policy_history.py | `7e61f305008d9fd0073b63ef7da2add10b648ab9caf6ad6d7f00dd685b534b8e` |
| pipeline/tests/test_private_desk_report.py | `f7466263da3feca83b241cf16dca9bc47f2d0e602531a51d07b3969be952613e` |
| pipeline/tests/test_private_desk_api.py | `b9f37d3d269b906cb02795c0eac41609f3ca52e241e41a76ee038911ed5f2f16` |
| private-desk/index.html | `8e14694df49ba7a21a107878b6b3b8297f188e26466a2124229cd8198d0e8639` |
| private-desk/verify-ui.mjs | `51bb92af9ab5ceb03d3c909398a21b2e052d5c4099a4fc2249436b8edfd36411` |
| docs/PRIVATE_POLICY_HISTORY_CONTRACT.md | `4506284427867c288fe4c510ab511a42e477bdd68b078cda5fc7d41143e2bab9` |
| docs/PRIVATE_DESK_CONTRACT.md | `475d1474abd5626bdf08e037d851c695b747cc7c11e419f49102a7b8f5371db5` |
| reports/private-policy-source-research.md | `e5eb991348df298bbfd46beb0b92efb17c151409a37ac087766fe1ef2382586f` |
| reports/private-policy-history-checks.txt | `b8f7ba06f461c82953851a8b5e130d31bce452273cd20118dc1070ed48b399ee` |
| reports/private-policy-history-browser.txt | `67bddcdc0c924f00bb59589097c22df72cf4de2c9013cd0f636c37993b9e0a42` |
| .private-fx/report.json | `02e0a594b4635ffab1b4ce1450d4863320d9b8afc88c20f5a6ba934d7e03ea01` |
| .private-fx/reports/20261001T134227-policy-9e0a6b5ba9d54705a0677811cb4fbf81.json | `02e0a594b4635ffab1b4ce1450d4863320d9b8afc88c20f5a6ba934d7e03ea01` |
| .private-fx/reports/20261001T131739-recalculate-14f1ae6ae2d64e0cb0c009609b8c2db5.json | `b8eb3155582288476ee046a8010be1b250b28a09ae723b3b7dd5d3b08bf05ecb` |

| Currency | Original CSV SHA-256 |
|---|---|
| USD | `5cab1ba9f3adff53d712d1a43ed86fca975b1a0ec4315c9c481f1989ef3bed1d` |
| EUR | `550d7f2d6c7b2ce2060e6b944019ec0d36a548c4f66ef43cd4b33eab0987eb06` |
| GBP | `d419c3d6e0b68034ed18f74c344368232266f092c5e3859066d1cb7e869ac531` |
| AUD | `5868ee48f456391f5c02b85bf3f9fa942e2749a019cffa9424f1d9ba27df4f07` |
| NZD | `9d549190e796033b7c38c41821e7e86835d7515fae13b2e8527c49b0aec396a7` |
| CAD | `baeda90767f94270c69efdefab29e74a7fff5497824e8e87078c857267bb198d` |
| CHF | `4d7d537d2010af738506b856b1bfd2274d2f41461308f2f134de2ec91515a144` |
