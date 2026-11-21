# Private historical-vintage packet — local evidence

Reviewed 1 October 2026. The desk now preserves four original ALFRED CSV responses, checks their requested vintage dates, compares revisions and replays the audit offline. The authenticated dashboard shows this evidence separately from price research and current AI commentary. This is a bounded data repair, not proof of an economic edge. **R2 and the full goal remain open.**

## Actual source evidence

The coordinator witnessed ALFRED's generated CSV download link in its official graph UI and captured the original responses below. This is a first-party UI route, not a documented API guarantee. Each accepted header must be exactly `observation_date,SERIES_YYYYMMDD`; a current FRED export with an undated series header is rejected. The private registry initially allows only CPIAUCSL and DGS2, both USD series. Other currency legs are missing.

All four requests returned HTTP 200. The observation window is 2022-01-01 through 2023-01-01 for CPIAUCSL, and 2023-02-01 through 2023-02-14 for DGS2. No value was interpolated or invented.

| Series | Requested vintage | Numeric rows | Latest included observation | Exported level |
|---|---|---:|---|---:|
| CPIAUCSL | 2023-02-13 | 12 | 2022-12-01 | 298.990 |
| CPIAUCSL | 2023-02-14 | 13 | 2023-01-01 | 300.536 |
| CPIAUCSL | 2024-02-13 | 13 | 2023-01-01 | 300.356 |
| DGS2 | 2023-02-14 | 9 | 2023-02-13 | 4.52 |

The January 2023 CPI observation is absent from the 13 February snapshot and present on 14 February. Twelve common earlier observations are unchanged between those two snapshots. All thirteen common observations change between the February 2023 and February 2024 snapshots. The DGS2 response does not contain a 14 February observation; its request date is not used as an observation date.

### Original response fingerprints

The receipt clocks below are when this workstation received the response in 2026, not historical release times.

| Series / vintage | Bytes | UTC receipt | SHA-256 of original response |
|---|---:|---|---|
| CPIAUCSL / 2023-02-13 | 263 | 2026-10-01T12:25:38.744526+00:00 | `80a2048914c90870ceb0b99323200459c37061d47c9d96aca1bf06c8e6b73c80` |
| CPIAUCSL / 2023-02-14 | 282 | 2026-10-01T12:25:39.643542+00:00 | `06c0aa1f6e1264e44ceaedb351378ef12f30b76dde25091cd8aea18c2936da1b` |
| CPIAUCSL / 2024-02-13 | 282 | 2026-10-01T12:25:40.650894+00:00 | `98b0552471a18fc47d10d32d9a6d31125f02663675432ff0a5c88d5ed47d413a` |
| DGS2 / 2023-02-14 | 175 | 2026-10-01T12:26:15.684418+00:00 | `72baf71b67497cc006d45a63dfc08c6b38731685e4bf22dc9bc11ac2d6b2751d` |

Original bodies, immutable receipt files and versioned cohorts are under the ignored `.private-fx/vintages` directory. The bounded command requires named series, dates and observation windows, allows at most twelve distinct requests per invocation and limits each body to two megabytes. Successes, transport failures and truncations retain their own receipts. Cache reuse verifies the request, receipt hash, body hash, byte count and path boundary. It does not quietly replace a corrupt capture.

## Calendar-date negative control

A deliberately unsafe control would take the January 2023 observation from the later snapshot merely because its observation month is old. That would expose 300.356 before the January observation appears in the captured February 2023 snapshot. This is an adverse control for the new audit, not a claim that the existing private price engine used this macro shortcut; it previously excluded historical macro features.

The implemented calendar selector instead produces:

| Calendar cutoff | Selected captured vintage | Latest observation / level |
|---|---|---|
| 2023-02-12 | None | None |
| 2023-02-13 | 2023-02-13 | 2022-12-01 / 298.990 |
| 2023-02-14 | 2023-02-14 | 2023-01-01 / 300.536 |
| 2024-02-13 | 2024-02-13 | 2023-01-01 / 300.356 |

Every result still says `release_timing: UNKNOWN` and `decision_qualification: UNQUALIFIED`. A calendar vintage is not a release clock, timezone or proof of provider availability at an intraday decision. The [ALFRED help page](https://alfred.stlouisfed.org/help) describes a typical update delay, fallback release-date sources and retrospective verification limits. The [release-date API documentation](https://fred.stlouisfed.org/docs/api/fred/release_dates.html) also distinguishes source release dates from availability on FRED or ALFRED. A next-trading-day lag could be studied as an assumption; it does not prove availability. No such lag qualifies the implemented evidence.

## What changed and what was preserved

`pipeline/src/private_desk/vintage.py` adds the strict capture, parser, revision audit and calendar-date inspection. It retains missing cells as null, permits negative yields, rejects non-finite values and non-positive CPI levels, rejects duplicated/non-increasing/out-of-window dates, and fails an entire series on conflicting same-vintage observations. Only common observation dates are used to count revisions. Saved statistics are recomputed from original responses before reuse.

The `vintage` CLI attaches this audit to a new report artifact. Report refresh only reads saved vintage evidence; it does not acquire additional history. Offline replay reconstructs the audit alongside the existing studies. The dashboard shows actual series/vintage coverage, source receipts, revisions, missing pair currencies and unknown release timing. Historical values do not enter the saved AI review, candidate selection or price backtest.

The coordinator compared the prior bid/ask report and the new report directly. Every `pair_reports` record, news item and saved `ai_summary` is equal. This includes all price backtests, session studies and bid/ask audits. The prior report's bytes and SHA-256 remain unchanged. The baseline still contains **2,000 held-out price calls**, all seven current candidates are `ABSTAIN`, all current probabilities are null and eligible trades remain zero. No forecasting or profitability improvement is claimed.

GitNexus query and impact attempts failed because the stored graph uses version 42 and the installed reader uses version 40. Risk therefore remains UNKNOWN. Manual caller review limits the edits to private capture/report/CLI/UI code and its tests; no public writer, historical ledger or production route was changed for this packet.

## Direct verification

- **42 focused tests passed:** 35 vintage controls and seven report tests. These cover wrong/current headers, future vintages, revisions, missing values, malformed rows, duplicate conflicts, request bounds, HTTP/timeout/truncation, cache reuse, path/hash tampering, saved-statistics tampering and report failure isolation.
- **2,234 full pipeline tests passed in 59.03 seconds.** Ruff passed; MyPy found no issues in 248 source files. Transcript: [private-vintage-checks.txt](D:/Projects/fxregimelab/reports/private-vintage-checks.txt).
- All four existing UI verification groups passed, including the added historical coverage and untrusted-text cases.
- Offline replay reproduced all seven daily/reference/session/bidask studies and the historical-vintage audit in 9.94 seconds, with `HISTORICAL_VINTAGE_REPLAY_OK` and `PRIVATE_DESK_REPLAY_OK`.
- The authenticated Chromium check visited all seven pairs. The six USD pairs show the missing other currency; EURGBP shows both EUR and GBP missing. Actual series, dates and levels remain visible, with UNKNOWN release timing, UNQUALIFIED model status and zero eligible trades. At 390 pixels, the document width is 390 pixels. Reload retains authentication; a refresh request without CSRF proof returns 403; report/status/CSV return 401 after logout. The expected HTTP denial messages account for the browser's resource errors; no application exception was observed. [Browser transcript](D:/Projects/fxregimelab/reports/private-vintage-browser.txt).
- The coordinator visually inspected the desktop, mobile and EURGBP screenshots in `output/playwright/private-vintage-*.png`. Tables remain inside their own scrolling container and the missing-currency labels are readable.

The new Unlazy ledger has seven gates: three manual gates met, four automatic gates awaiting formal checker approval, zero abandoned. Direct commands passed; they do not create bound checker certification. The skill states: “Only the user's explicit, inspected approval may cross that boundary.” See [Unlazy](C:/Users/sakha/.codex/skills/unlazy/SKILL.md) and [.unlazy/private-vintage/GATES.md](D:/Projects/fxregimelab/.unlazy/private-vintage/GATES.md). Approval was not inferred, and no `--approve` command was run.

### Pinned report and evidence

| Artifact | SHA-256 |
|---|---|
| `.private-fx/reports/20261001T122616-vintage-8ccb0fabae194583857b170e337230b7.json` | `22f58cce9177e4d3a8f8dc6d4d2c7e2fe676afd1c0eb077b318e0429356fc197` |
| `.private-fx/vintages/evidence.json` | `17f3ff1d63b2cbe9e96fe5fd73bccbef44c356b2b832010865fe4b260b08d0c2` |
| `reports/private-vintage-checks.txt` | `f5519a42c204ccd41e82432b3f2bf3cd6d51eacfbe1ac43dd957ffdbc26fa913` |
| Prior `.private-fx/reports/20261001T114627-bidask-b469bf614e9146e0975c08177bb232f4.json` | `dd094642149985b78240a86e0b56bb2f0c6ee15b3e26318a004cef827dad3158` |

The current `.private-fx/report.json` matches the new pinned report. [Source research](D:/Projects/fxregimelab/reports/private-vintage-source-research.md) records the independent source investigation. Its next-day language was corrected during coordinator review so that a delay assumption cannot be mistaken for release-time proof.

## Remaining research

R2 needs qualified currency-specific historical series, stable instrument/area definitions, per-vintage metadata and coverage, source-release and usable-availability evidence, and separately captured expectations. Four selected USD snapshots do not establish a seven-currency 20–30-year fundamental panel. Retrospective archive records do not prove contemporaneous receipt, and actual values alone do not establish a surprise.

R1 still lacks executable history and verified costs; R3 needs predeclared fundamental trials and untouched evaluation; R4 needs direction-specific calibration and shared currency/tail-risk controls; R5 needs forward paper evidence and reliable operation. The broader public repair register remains open. The loopback desk at [127.0.0.1:8765](http://127.0.0.1:8765) is a working local research tool. No commit, push, deployment, production write, broker action or heavy runtime startup occurred.

Source report after coordinator correction: SHA-256 `eeab19a444545f866f93fa8b3065fdc9cbc7ce29addc79ce4ec4d7d63867a5d0`.

Final local health check: root page returned HTTP 200 and the expected Private desk content; loopback listener PID 14956. Named privatefx and alfred browser sessions were closed after evidence capture. The desk service was left running for the owner. No health endpoint is implemented; an initial probe to /health returned 404 and the documented root-page check passed.
