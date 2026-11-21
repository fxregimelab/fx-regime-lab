# Private release-clock packet — direct local evidence

Reviewed 1 October 2026. The desk now preserves named first-party release archives, checks their identity and stated clock, converts US Eastern time correctly and replays the audit offline. Three original Federal Reserve statements pass; three BLS CPI requests remain unavailable after HTTP 403. The dashboard shows both outcomes. **R2 and the full research goal remain open.**

This packet does not add a fundamental forecasting feature, qualify a trade or claim improvement in profitability. A source-stated publication clock is not proof of actual historical transmission, provider ingestion or receipt.

## Actual original captures

The bounded FOMC command captured the official statement pages directly from this workstation. Each response was HTTP 200 with `text/html`, an exact statement title, a matching date, one release clock and one target range.

| Official statement | Stated local clock | UTC conversion | Announced target range |
|---|---|---|---|
| [1 February 2023](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230201a.htm) | 2:00 p.m. EST | 2023-02-01T19:00:00+00:00 | 4.50–4.75 percent |
| [22 March 2023](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230322a.htm) | 2:00 p.m. EDT | 2023-03-22T18:00:00+00:00 | 4.75–5.00 percent |
| [26 July 2023](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230726a.htm) | 2:00 p.m. EDT | 2023-07-26T18:00:00+00:00 | 5.25–5.50 percent |

The difference between winter and summer is one hour in UTC. Mixed fractions such as `4-3/4` are parsed as 4.75, not 4.3 or 4.34. The original range wording is retained. An announced overnight policy target is distinct from the realized effective federal funds rate and a two-year Treasury yield. No target midpoint is substituted for either statistic.

The official BLS CPI HTML archive requests for 2023-02-14, 2023-04-12 and 2024-02-13 each returned HTTP 403 with a 1,323-byte HTML denial body. Those bodies and receipts are preserved. No CPI event or release value was accepted from them. Separate bounded HTML/text/PDF source investigation also found blocked direct routes. Indexed/readable official content was used for the source review, not as a successful original capture.

### Original response fingerprints

All receipt times below are current workstation receipts in 2026, not historical publication or market receipt times.

| Request | HTTP | Bytes | UTC receipt | SHA-256 |
|---|---:|---:|---|---|
| FOMC / 2023-02-01 | 200 | 82,434 | 2026-10-01T12:45:27.453404+00:00 | `d6e94305c206ae19478e4d8d25af0c2b574dd5a1f97153c74acbb34c40ebae3d` |
| FOMC / 2023-03-22 | 200 | 82,630 | 2026-10-01T12:45:28.108498+00:00 | `1bcfa23dfaa1b7437ed337bfad2e181d976b99f0a92dfc89b9770ade2e28672c` |
| FOMC / 2023-07-26 | 200 | 82,440 | 2026-10-01T12:45:28.863905+00:00 | `48a3234801bd4212628a846b24dc0de05815fde4ee12db2e89f3046a92033505` |
| CPI / 2023-02-14 | 403 | 1,323 | 2026-10-01T12:45:32.128901+00:00 | `970523699bced8d46253205c8752dcf2d20838dfc694afc2af781ecd93b6882c` |
| CPI / 2023-04-12 | 403 | 1,323 | 2026-10-01T12:45:32.528321+00:00 | `2039c0185d5f8c0872af274e475e148a2a9c30f6b8454b75ecce97629712ad3a` |
| CPI / 2024-02-13 | 403 | 1,323 | 2026-10-01T12:45:32.935113+00:00 | `83e9574d0f68309744b88be937915781aff49ee526b254bda27cc1893303c076` |

## Chronology and value-identity controls

A deliberately unsafe calendar-date join would expose the February statement from the start of 1 February, before its stated release clock. The new timestamp audit excludes that event at 18:59:59 UTC and at exactly 19:00:00 UTC; it appears only after the stated clock. For the March statement, the corresponding boundary is 18:00 UTC, not 19:00 UTC. The earlier February event remains visible while the March event is excluded before and at its boundary. Date-only or offset-free decisions are rejected; an explicit non-UTC offset is converted before comparison.

These are chronology controls, not accepted information-arrival estimates. Every event keeps actual transmission, historical receipt, provider availability, effective implementation date, consensus and surprise as null, with decision qualification UNQUALIFIED. Archival revision status remains UNKNOWN: a currently accessible old page is not proof that its bytes never changed.

The strict parser rejects mismatched dates/titles, duplicate article containers, ambiguous clocks/ranges, missing or seasonally inconsistent EST/EDT labels, invalid or unordered fractional bounds, unsupported media types and a release clock after receipt. Conflicting same-source/date values reject that source's accepted events; equal duplicates count once.

The CPI parser has separate observation month, release ID, weekday/date, source embargo clock, headline month-on-month seasonally adjusted percentage and year-on-year unadjusted percentage. It does not take the future schedule's clock or confuse CPI-U with CPI-W, core inflation or an index level. Its controls pass on synthetic source-schema fixtures. Original successful CPI parsing remains unverified because the actual requests were blocked.

The independent [source review](D:/Projects/fxregimelab/reports/private-release-source-research.md) found that the readable BLS CPI archive publishes rounded percentage changes and an unadjusted index level, not the exact seasonally adjusted CPIAUCSL levels 300.536 or 300.356. A matching release date does not establish identity with those ALFRED values. No such join was added. Implementation notes can establish when an announced target becomes effective, but they were not attached to this bounded capture cohort; the implemented effective-date field therefore remains unknown.

## Integration and preservation

`pipeline/src/private_desk/releases.py` adds bounded named requests, immutable original receipts, strict parsing, source-clock inspection and replay. The CLI `release` command accepts one supported source and up to twelve distinct past dates; each body is limited to two megabytes. Redirects and arbitrary URLs are rejected. Failed, blocked and truncated responses retain their own evidence. Cache and saved-cohort reuse verify request identity, path boundary, receipt hash, original length/body hash and recomputed statistics. Corruption does not trigger a silent replacement request.

Report refresh reads saved release evidence after current AI work. It does not fetch additional historical releases or feed these values into a forecast. The separate dashboard panel shows the announced measures, original local clock, UTC conversion, source failures, missing pair currencies and unknown actual arrival. The mobile table scrolls within its panel, with document names and clocks kept on a readable line.

The coordinator compared the new report with the prior vintage report. All `pair_reports`, `news`, `ai_summary` and `historical_fundamentals` are equal. This preserves daily/reference backtests, session studies, bid/ask audits, vintage/revision evidence and saved AI commentary. The prior pinned report's hash is unchanged. There are still **2,000 held-out price calls**, seven ABSTAIN/null-probability candidates and zero eligible current trades.

GitNexus query/impact attempts returned the existing storage-version incompatibility, so automated impact risk remains UNKNOWN. Manual caller review confines this packet to private evidence/report/CLI/UI paths and tests. No public writer, database schema or immutable ledger was edited for this work.

## Verification on the final revision

- **70 focused tests passed:** 61 release controls plus nine report tests. Cases include calendar/same-instant leakage, daylight-saving conversion, ambiguous/malformed source identity, mixed fractions, CPI period/adjustment identity, conflicts, media/HTTP failures, timeouts/truncation, immutable cache reuse and path/hash/statistics tampering.
- **2,297 full pipeline tests passed in 54.37 seconds.** Ruff passed; MyPy found no issues in 250 source files. [Final transcript](D:/Projects/fxregimelab/reports/private-release-checks.txt). An initial test import failed MyPy's explicit-export rule; it was corrected and the full command rerun successfully.
- All four final UI verification groups passed, including actual schema rendering, null qualification, missing currencies, failures and untrusted plain-text controls.
- Offline replay reproduced all seven price/reference/session/bidask studies, the ALFRED vintage audit and the new release-clock audit in 10.04 seconds, with `HISTORICAL_RELEASE_REPLAY_OK` and `PRIVATE_DESK_REPLAY_OK`. No network or model call was made.
- The final authenticated Chromium run visited all seven pairs and checked every accepted document/clock/range, visible HTTP 403 failures, unknown actual arrival, UNQUALIFIED historical model and zero eligible trades. Reload retained authentication; refresh without CSRF proof returned 403; report/status/CSV returned 401 after logout. [Browser transcript](D:/Projects/fxregimelab/reports/private-release-browser.txt).
- At a 390-pixel viewport, layout client width and document scroll width are both 375 pixels because the browser reserves a scrollbar. There is no document overflow. An injected 900-pixel element made the overflow detector fail as intended, then was removed. Screenshot review found and corrected cramped release-table wrapping; final desktop, EURGBP and mobile left/right views were visually inspected. These are bounded Chromium checks, not every-browser certification.

The Unlazy ledger has seven gates: three manual reviews met, four automatic gates awaiting formal checker approval, zero abandoned. Direct command success is recorded separately from bound checker certification. The skill says: “Only the user's explicit, inspected approval may cross that boundary.” See [Unlazy](C:/Users/sakha/.codex/skills/unlazy/SKILL.md) and [the packet gates](D:/Projects/fxregimelab/.unlazy/private-release/GATES.md). No `--approve` command was run.

## Pinned artifacts

| Artifact | SHA-256 |
|---|---|
| `.private-fx/reports/20261001T124533-release-e9d5dc234ac14a14a52a402442e322ad.json` | `ef3a93e23ad0743ff00344e5893fe7b5db2f5ef45d38015e7f79883e352a7847` |
| `.private-fx/releases/evidence.json` | `4e88c8e88c028dd95c26de9173e3e3da62b5f1885b27bf87619911d0edc957b9` |
| `reports/private-release-checks.txt` | `ce939b2fb4665f9564d0f041ea380ab04ae4e1960c2ce4c0510a39efa44f19d8` |
| `reports/private-release-source-research.md` | `7a71d54e9bf089f43bb656fbafc14722fcbaa09b3e16a79919eaeffe29922321` |
| `reports/private-release-browser.txt` | `02b6a2a7bddd3ce233f3a8c6ece49a99c125fb6916a6b3003514e9a2366beb70` |
| Prior `.private-fx/reports/20261001T122616-vintage-8ccb0fabae194583857b170e337230b7.json` | `22f58cce9177e4d3a8f8dc6d4d2c7e2fe676afd1c0eb077b318e0429356fc197` |

The latest `.private-fx/report.json` matches the new pinned artifact. Original responses, immutable receipts and versioned cohorts remain under ignored `.private-fx/releases`. Screenshots are under ignored `output/playwright/private-release-*.png`.

## Remaining work and local operation

The sampled source-clock evidence is USD only. Six other currency legs, long original release history, effective-policy metadata, CPI original capture/value identity, usable arrival evidence and timestamped expectations remain open. A source-stated clock cannot clear those requirements. R1 still needs executable prices/costs; R3 needs predeclared fundamental trials and untouched evaluation; R4 needs direction-specific calibration and common-currency/tail-risk controls; R5 needs forward paper evidence and reliable operation. The public repair register also remains open.

The private loopback service was restarted through its existing manual launcher after the Python integration change. Its root page passed HTTP 200/content readiness; listener PID 22368 binds 127.0.0.1:8765. It is left running for the owner at [the dashboard](http://127.0.0.1:8765). No Docker, heavy Hermes service, production write, broker action, commit, push or deployment occurred.

Final checks: current report matches its pinned release artifact and recomputed original release audit; prior vintage bytes/hash remain unchanged. Named privaterelease browser closed after final evidence capture. Root page again returned HTTP 200 with Historical release clocks content; loopback desk left running.
