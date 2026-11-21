# Private FX desk: implementation evidence and open research

1 October 2026. The authenticated local desk is implemented, connected to real captured data and directly tested. It is running at http://127.0.0.1:8765. **No current trade qualifies. The profitable fundamental strategy and the full repository repair remain unfinished.** This is a local engineering and baseline-research receipt, not a live-trading or release certificate.

The owner authorized private research beyond the former three-pair public scope. The universe is EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF and EURGBP. This is six USD majors plus one cross; JPY is excluded. Existing USDINR/public research, immutable ledgers and prior uncommitted repairs were preserved.

## What is working

| Work item | Delivered behavior | Evidence |
|---|---|---|
| 1. Private access | Password login, HTTP-only SameSite cookie, CSRF and origin checks, login rate limit, logout revocation | Focused auth regressions and actual browser controls |
| 2. Source acquisition | Seven real daily histories, shared ECB reference archive, recent hourly histories, current policy observations and dated headlines | Immutable captures with URLs, receipt times, SHA-256 and actual coverage |
| 3. Data quality | Malformed daily rows quarantined unchanged; entire contaminated feature and holding windows excluded | Source/engine regressions, original rejected captures retained |
| 4. Exit policy | Next-bar entry, half-position +1R exit, remaining stop to entry/+3R, time exit, adverse intrabar order and explicit costs | Simulator regressions, auditable per-trade gross/net rows |
| 5. Chronological research | Twelve fixed daily trials, training-only selection, separate calibration/test, five-bar embargo and fully matured labels | Trial/fold records and chronology/negative-control tests |
| 6. Probability boundary | Selected policy needs its own evidence; no borrowed profits, invented probability or forced trade | All current probabilities null, seven ABSTAIN candidates |
| 7. Long history | Separate indicative reference-close direction study from 1999 | 7,104 reference dates per pair; no claimed stop/target proof |
| 8. Session research | London/New York local-clock entries, DST, separate train/test and missing-hour exclusions | Recent hourly captures and session regressions |
| 9. Current AI context | Central DeepSeek client supplies conditional headline scenarios and opposing evidence | Successful live bounded call plus malformed-output controls |
| 10. Dashboard | Pair selection, briefs, OHLC/equity charts, qualification reasons, source records, session evidence, trade pagination and IST/UTC | Four deterministic UI checks and actual desktop/mobile browser journey |
| 11. Local operations | Background refresh preserves the old report on failure; authenticated CSV; start/stop scripts with health and process checks | Real refresh, 2,000-row export, restart, login recovery and logout |
| 12. Reproduction | Saved price studies reproduce exactly from pinned captures without a provider or model call | Seven-pair offline replay, 7.64 seconds |

Implementation lives in `pipeline/src/private_desk/`, `private-desk/` and the existing central `pipeline/src/ai/client.py`. The [contract](../docs/PRIVATE_DESK_CONTRACT.md) describes the interfaces and boundaries. No broker integration exists. Dashboard levels are completed-price research references; the future executable entry is unknown.

## Measured daily baseline

These are the adaptive walk-forward held-out calls across the fixed trials. They are not the current selected policy's own qualification summary. The dashboard keeps that second summary separate. R means return divided by the initial stop distance, before account position sizing. Costs are assumptions: 1.2 pip spread, 0.2 pip slippage per side and 0.15 pip holding charge per calendar day. These are not verified broker spreads or swaps.

| Pair | Valid original candles | Quarantined candles | Held-out trades | Net-positive rate | +1R target hit rate | Mean net R | Maximum drawdown R |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | 5,796 | 128 | 158 | 48.7% | 10.1% | -0.0972 | 19.5851 |
| GBPUSD | 5,833 | 103 | 287 | 43.9% | 8.4% | -0.0636 | 23.1829 |
| AUDUSD | 5,154 | 146 | 269 | 50.2% | 5.6% | -0.0180 | 10.8110 |
| NZDUSD | 5,557 | 368 | 83 | 49.4% | 10.8% | -0.0098 | 5.3650 |
| USDCAD | 5,878 | 114 | 350 | 49.7% | 8.9% | -0.0207 | 14.9915 |
| USDCHF | 5,887 | 103 | 322 | 53.4% | 17.1% | +0.0145 | 9.0790 |
| EURGBP | 7,155 | 69 | 531 | 45.0% | 8.3% | -0.0708 | 39.4184 |

Total: **2,000 calls**. Six pairs have negative average net return. USDCHF's approximate 95% mean-return interval is **[-0.0576R, +0.0866R]**, so its small positive mean does not establish an edge. These approximate intervals do not fully address dependence, repeated research trials or portfolio exposure. Adding correlated pair returns is not an account backtest.

All seven candidates have status **ABSTAIN**, current probability **null**, fundamental qualification **UNQUALIFIED** and execution status **RESEARCH_ONLY**. Some can display an unqualified price-only direction and reference levels for inspection; that does not make them eligible trades. The current probability, when eligible, would mean P(net R > 0), not P(reaching +1R). Its current implementation pools BUY and SELL within policy/strength buckets and discloses that direction-specific calibration is absent.

## What the evidence says about the theory

The requested partial exit is **50% of a position**, not 50% of the account. Half at +1R and half at +3R gives **+2R gross** if both targets fill. If the second half exits at entry, the full position earns **+0.5R gross**. Costs reduce both. A stop can lose more than -1R after a gap. Moving a stop after a target has been reached cannot guarantee reaching that target first.

The daily baseline uses momentum/reversion signals and stops at 1.25 or 1.75 times recent average daily range, with three/five-day holding trials. The measured +1R hit rates show that this particular combination does not regularly deliver the requested first target. Shortening the stop, extending the hold or changing the signal might change the result, but choosing them after viewing these tests is another research trial. It cannot create independent validation by relabelling the same observations.

Current policy levels do not establish policy surprises, the expected future rate path, what the market has priced, funding costs or the future FX return. Adding AI prose to the price model does not turn it into a tested fundamental model. A 60–70% win target and one/two desired weekly trades are aspirations; neither can be forced while preserving measured positive expected return. The research objective is positive return after realistic costs, with defensible uncertainty and acceptable losses; win rate and frequency must be reported alongside it.

## Actual coverage and source limits

All daily captures end on **2026-09-30**. Starts: EURUSD/GBPUSD 2003-12-01, AUDUSD 2006-05-16, NZDUSD 2003-12-03, USDCAD/USDCHF 2003-09-17, EURGBP 1999-01-04. Actual spans are approximately **20.38–27.74 years**. Yahoo supplies current reconstructed daily candles, without a verified historical receipt/vintage archive or executable bid/ask. Quarantine conditions the results on valid available windows; missing observations may be concentrated in difficult market conditions. No price was repaired or interpolated.

The shared ECB archive through Frankfurter has **7,104 dates from 1999-01-04 to 2026-09-30**. Crosses use the same dated euro fix. The separate study's held-out direction rates range from **48.9% to 50.5%**. Its next-reference entry and 2bp cost scenario cannot validate intrabar partial exits or live fills. The [ECB describes these reference rates as informational and discourages transaction use](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).

Hourly evidence covers roughly two years. London/New York entries are evaluated at their actual local 08:00 clocks, with daylight saving changes. Complete pre-entry and holding paths must be present. Three-day held-out session samples are small; every five-day comparison currently has zero usable held-out trades after strict missing-hour controls. For example, USDCAD New York has 70% positive trades from just **10** observations, with a Wilson interval of approximately **39.7–89.2%**. It cannot justify a 70% current probability. Weekday results are descriptive, and market holiday schedules remain unverified.

Current policy observations cover USD, EUR, GBP, AUD, NZD, CAD and CHF. Overall fundamentals remain **PARTIAL**: historical releases/vintages, inflation surprises, growth, market expectations, positioning and a verified event calendar are unavailable. Observation date, page-observation date, effective date and publication time remain distinct. Unknown announcement times are null. RBNZ used a disclosed public reader of its official page after direct access failed. Current snapshots are excluded from historical tests.

The final capture has **116 dated headlines from eight feeds**; the model receives a balanced subset of 40. RBNZ RSS is not configured. These are titles and URLs, not read and verified article bodies or a complete geopolitical archive.

## Observed AI failure and repair

A live review incorrectly said the 3.75% UK rate matched the upper bound of the supplied 3.75–4.0% Fed range. It also inferred a carry advantage from policy targets alone. That report was retained as historical evidence and superseded for the dashboard.

The private client now requires thesis/opposing fields to start with `If`, rejects prose containing numeric, rate-bound, differential or carry claims, ignores extra probability/price fields, filters citations to supplied URLs and uses a deterministic global summary. Rate facts remain in the source table. Four adverse fixtures reproduce the unsafe output classes and fail closed. The final live call returned seven conditional scenarios, status **GENERATED_UNVALIDATED**, model **deepseek-v4-pro**, 5,199 input/1,209 output tokens and zero reported cached input tokens. Structural checks are not semantic fact checking; full-document grounding and predictive contribution remain unvalidated.

Provider model availability was checked, rather than assuming an old alias existed. Explicit unavailable model selection fails without completion. Empty/malformed responses retain sanitized status and usage, without exposing credentials. The initial empty response was repaired using explicit thinking configuration documented by [DeepSeek](https://api-docs.deepseek.com/guides/thinking_mode/); the request is bounded to a single completion with a timeout and no automatic retries.

## Direct verification on the final implementation

| Check | Measured receipt |
|---|---|
| Focused private regressions | **108 passed in 5.43s** |
| Complete pipeline suite | **2,158 passed in 56.83s** |
| Pipeline Ruff | All checks passed |
| Pipeline MyPy | No issues in **244 source files** |
| UI verifier | Four passes; `PRIVATE_DESK_UI_VERIFIED` |
| Actual report verification | `PRIVATE_DESK_REPORT_OK`; all seven statuses and recursively collected capture hashes checked |
| Offline replay | Exact seven-pair daily/reference/session reproduction; `PRIVATE_DESK_REPLAY_OK`, **7.64s** |
| Existing frontend | Biome checked 204 files; TypeScript passed; local Next.js 15.3.9 production build succeeded |
| Browser | Seven selectable briefs; date-only precision; no document overflow at 1440px/390px; pagination/filter/timezone/export/reload/auth checks |
| Real export | **2,000 rows/seven pairs**, matching saved trades, every net return at or below gross |

Negative controls cover contaminated future holding windows, borrowed-policy profits, changed capture hashes, a secret-pattern positive control, hostile AI/source content, CSV formula injection, wrong credentials, rejected origins, incorrect CSRF and protected endpoints after logout. A browser locator initially used a pair's visible text instead of its explicit accessible name; the corrected seven-pair journey passed. This was a test-selector error, not a product fix.

The existing frontend build emitted metadataBase/edge-static-generation notices; they are not private-desk acceptance or a deployed Linux receipt. No Vercel deployment was made. Browser screenshots are under `output/playwright/`; the CLI/browser's initial unauthenticated 401 and intentional 403/401 controls are expected refusal evidence.

GitNexus impact was attempted before symbol changes but failed consistently with database storage version 42 versus runtime version 40. Graph risk remains **UNKNOWN**, not zero. Source caller tracing found private report/CLI/API/tests for the new modules. Existing central AI behavior and prior semantic repairs were preserved; formatting also changed in that file. No commit was made.

## Five research workstreams still open

| Next item | Required result before closure |
|---|---|
| R1 — executable data and costs | Verify one minute/hourly bid/ask acquisition and original captures; measure gaps/DST/holidays; use actual broker spread, slippage, financing and adverse fill stress. Start with one bounded EURUSD period before expanding coverage. |
| R2 — fundamental evidence | Capture historical observations and their available-at/revision times, policy expectations, inflation/growth surprises, positioning and dated events. Verify article bodies and separate cited facts from hypotheses. Exclude unsupported legs. |
| R3 — frozen models | Predeclare a small fundamental/quant model set and horizon/exit comparisons; use blocked/purged chronological selection and cost stress. These displayed test periods have been seen and cannot be reused as untouched tests after tuning. |
| R4 — probability and portfolio | Validate current-policy/direction probabilities with adequate samples and dependence-aware intervals; measure joint USD exposure, drawdowns, tail gaps, calibration, costs and trade frequency. |
| R5 — forward operations | Keep timestamped paper calls and outcomes, validate age/restart/recovery/refresh behavior and promotion rules, then decide whether a qualified strategy merits any execution integration. No real order is authorized by a high score alone. |

These are five workstreams for the private desk, not a claim that only five defects remain in the whole repository. The existing [45-item repair register](../docs/REPAIR_REGISTER.md) and [public repair checkpoint](REPAIR_CHECKPOINT.md) still govern their separate unfinished work. No existing repair was promoted to release acceptance by this desk.

## Launch and evidence boundary

Open http://127.0.0.1:8765 on this workstation. The generated password is in `.private-fx/access.txt`; its value is deliberately absent from this report. Use `powershell -File private-desk/start.ps1` to restart and `powershell -File private-desk/stop.ps1` to stop. The service is loopback-only and remains running for the requested dashboard. There is no boot/login/watchdog/recurring startup.

The owner-authorized DeepSeek key is read server-side from the configured environment path. Ignored captures, report versions, authentication state and provider configuration stay under `.private-fx/`. No key is sent to the browser. Remote hosting would require its own TLS/identity/storage/release work; this URL is local, not a public deployment.

No PostgreSQL, Docker or heavier Hermes component was needed or started. Hermes MCP remains enabled. No production database write, migration, historical ledger rewrite, commit, push, broker order or deployment occurred.

Formal Unlazy certification is pending. [The skill](C:/Users/sakha/.codex/skills/unlazy/SKILL.md) says: “Only the user's explicit, inspected approval may cross that boundary.” That applies to execution of inherited `CHECK` commands by its checker. Direct development tests were run within the owner's authorization; no `--approve`, forged automatic evidence or ALL MET claim was made. Manual browser/report review and direct receipts are recorded separately. The goal remains active.

Final scoped parser result: **19 gates total; three manual gates met, 16 unmet, zero abandoned**. Eleven unmet gates await automatic checker certification and five are the genuinely open research outcomes above. The final `--reverify` printed approval-required diagnostics, ran zero commands and preserved these counts. All three workers returned, dispatch is complete and exact leases remain held pending formal parent verification. Ledger lint passed, with eight advisory warnings about manual review and the mostly-manual future research inventory; those future outcomes need runnable validation once their data/model contracts exist.

## Final pinned receipts

Report: `.private-fx/reports/20261001T110930-19e5f1a2d560468296cb505653feb4b6.json`; report capture-start timestamp 2026-10-01T11:08:20.735579Z. AI review timestamp 2026-10-01T11:09:18.712320Z. Its latest-report hash is `8236a5c3d40ecc834c2c5ed667fec4fc7520656924d917ccb1f1d3b9b7482eaa`. Future refreshes will change the latest report; the retained version is the receipt for these numbers.

| File | SHA-256 |
|---|---|
| pipeline/src/private_desk/engine.py | 389ff425c37f3d9c63f50584fc5860e2306273530f34bafa64516eafc8da3854 |
| pipeline/src/private_desk/data.py | d73e26cc7a93d95eaee3597f7676b635b4be9d82a9017866e95cffee97e1b3e5 |
| pipeline/src/private_desk/report.py | 808c57ebae322403a35ecaf78b691af39f1f64bfdafd13ac09c80f3303a3cba4 |
| pipeline/src/private_desk/api.py | 46d7ef298fd03f2123300673ab4ef684e66f65b2602d089012ef04a240acff5f |
| pipeline/src/private_desk/sessions.py | 767691f59f5938877dd89587440fb5f9902c0b05f5b5619f88a7c915ee2bd549 |
| pipeline/src/private_desk/cli.py | f5b2b423d1126a188ee252e90e5e349e9e98c689645fc19a1a2c6a380fbd0ec9 |
| pipeline/src/ai/client.py | 486c9e137cf9454048a1e4df97017e07905dfabdd5e46b7eb620de4929643d06 |
| private-desk/index.html | 1edc632283c095cf0f09c26ebedf50cd2eb30ce3f441e04793e827feaf00bd84 |
| private-desk/verify-ui.mjs | 43265a8611a6df7f2023aa448365d67c558b8cd96b0e0b886408ae095f5c2242 |
| Downloaded trade CSV | 15bcbc399b88684a479faab243522ff0052c760412a2da84182124bcd87de743 |
