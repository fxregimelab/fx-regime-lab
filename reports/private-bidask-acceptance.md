# Private bid/ask archive evidence — local review

1 October 2026. The private desk now reads explicitly named FXCM minute archives, preserves original responses and receipts, audits both price sides, and shows the results in a separate authenticated dashboard panel. This advances R1's data work. **R1 remains open**, and no strategy or forecasting improvement is claimed.

## Actual sampled week

The new reader fetched all seven pairs for ISO week `2025-W40`. Every request returned HTTP 200. Six archives passed the exact-header, price, side-OHLC, uncrossed-bounds, timestamp-order, week-envelope and receipt-clock checks. The CHF archive failed.

Missing minutes below use an **unverified** Sunday 17:00 to Friday 17:00 New York market-clock proxy. Each requested week has 7,200 expected proxy minutes. A missing minute is not automatically an outage or holiday. No replacement quote is inserted.

| Pair | Accepted distinct minutes | Missing proxy minutes | Source audit |
|---|---:|---:|---|
| EURUSD | 7,168 | 32 | Indicative source audit |
| GBPUSD | 7,121 | 79 | Indicative source audit |
| AUDUSD | 7,148 | 52 | Indicative source audit |
| NZDUSD | 7,111 | 89 | Indicative source audit |
| USDCAD | 7,134 | 66 | Indicative source audit |
| USDCHF | Unavailable | Unavailable | Entire archive rejected |
| EURGBP | 7,183 | 17 | Indicative source audit |

All six accepted cohorts have zero observations outside that market-clock proxy. These are selected-week observations, not a complete historical dataset or a live price feed.

## Deterministic adverse evidence

An independent pass over the original CHF body found **four crossed rows among 7,068 raw rows**. At `2025-10-01 20:12 UTC`, the original bid close is `0.79711` and ask close is `0.79710`. The strict reader rejects the entire archive with `Crossed side bounds`; it does not delete the four rows and present the rest as a clean cohort.

Unit controls also reject malformed headers, invalid/non-finite/non-positive prices, invalid side OHLC, non-minute timestamps, wrong date order, future observations, out-of-week rows, duplicate/reversed timestamps and oversized gzip bodies. Equal quotes from duplicate archive receipts count once; conflicting quotes reject the whole pair cohort. Cache corruption, request mismatch and paths outside the evidence directory fail without silently making another request. Failed and truncated responses are retained and do not acquire accepted observation counts.

## Preservation and integration

Successful and failed responses have unique original body files and JSON receipts recording URL, HTTP status, UTC receipt time, completeness, byte count and SHA-256. Mutable indexes point to those immutable files. New requests preserve former captures. Both receipt and body hashes are checked on reuse. Saved audit statistics must reproduce from the original bodies.

Dashboard refresh reads saved bid/ask evidence; it does not acquire unspecified archive weeks. The CLI accepts one to twelve distinct named weeks per invocation and the private pair universe only. A bid/ask evidence failure cannot erase daily, reference-price or session research.

The new report was compared with the previous pinned report, `20261001T110930-19e5f1a2d560468296cb505653feb4b6.json`. Every pair record is equal after removing the new `bidask_evidence` field. The saved AI review is also equal. The previous report file remains unchanged. Existing backtests still have 2,000 held-out calls; every current candidate remains ABSTAIN with no qualified probability or execution permission.

## Verification

- Final focused controls: **42 passed** in 1.07 seconds.
- Final full pipeline: **2,197 passed** in 53.22 seconds; Ruff passed; MyPy passed for **246 source files**. The initial full run caught a test import/type issue, which was fixed before the final successful run. Transcript: [private-bidask-checks.txt](D:/Projects/fxregimelab/reports/private-bidask-checks.txt).
- Offline replay recomputed all seven pinned daily, reference-price, session and bid/ask cohorts: `PRIVATE_DESK_REPLAY_OK`, 8.98 seconds. This makes no network or AI call. CLI report verification checked capture hashes and research bounds.
- UI schema/null/security regressions: four groups passed, `PRIVATE_DESK_UI_VERIFIED`.
- Actual authenticated Chromium: all seven pair views displayed the expected counts or CHF rejection, unknown timestamp role, unqualified execution and zero eligible trades. Desktop 1440×1000 and mobile 390×844 were inspected. Mobile document width equals viewport width, 390 pixels. Cramped mobile labels were corrected to a two-column layout and visually reviewed again.
- Authenticated reload passed. A refresh request without a CSRF token returned 403. After logout, report, status and CSV endpoints each returned 401. Browser transcript: [private-bidask-browser.txt](D:/Projects/fxregimelab/reports/private-bidask-browser.txt). Screenshots: `output/playwright/private-bidask-eurusd.png`, `private-bidask-chf-rejected.png` and `private-bidask-mobile.png`.

The local listener is healthy at [the private desk](http://127.0.0.1:8765), bound to loopback only. Password: the owner's ignored `.private-fx/access.txt`. The manual launcher was used; no Docker, PostgreSQL, heavy Hermes process, boot task or watchdog was started. The browser test session was signed out. No commit, push, deployment or production database write occurred.

## Pinned evidence

| Artifact | SHA-256 |
|---|---|
| `.private-fx/reports/20261001T114627-bidask-b469bf614e9146e0975c08177bb232f4.json` and identical latest report | `dd094642149985b78240a86e0b56bb2f0c6ee15b3e26318a004cef827dad3158` |
| `.private-fx/bidask/evidence.json` | `6d2a4df8d025068087971f7dbb71c9e8929eee9a4c526e8c058f8c0cef1f50e4` |
| Final full-check transcript | `07683006f994a46f62e097a068354e037a9e1cc47241604c049a83088d9122e7` |
| First-party source research | `8b42c658249e2dc537fa4314d219c4251bf39692634a8fc53ba1f31415489e6c` |

Raw body and receipt hashes for every pair are embedded in the pinned report. The source research preserves earlier 2012/2017/2025 EURUSD probes and the failed 2026 request separately.

## Remaining research and acceptance

FXCM describes indicative Active Trader quotes and UTC, but the inspected documentation does not establish candle start/end allocation or exact boundary tick treatment. Side open/close differences are descriptive OHLC differences, **not synchronized tick spreads or actual account costs**. This packet adds no fill simulator and cannot qualify next-bar execution or session timing from these archives. Continuous history, historical availability, corrections, holidays, commissions, slippage, financing and this owner's broker fills remain unverified.

The first-party review compares FXCM with Dukascopy and records access conditions: [private-bidask-source-research.md](D:/Projects/fxregimelab/reports/private-bidask-source-research.md). No paid S3 access, Dukascopy automated acquisition, public redistribution or assumption of unrestricted licensing was made. The bounded contract is [PRIVATE_BIDASK_CONTRACT.md](D:/Projects/fxregimelab/docs/PRIVATE_BIDASK_CONTRACT.md).

R1–R5 in the main private-desk plan remain open. The next data requirement is to resolve timestamp meaning and source gaps before studying trades on these quotes. Historical fundamental release/vintage evidence, frozen fundamental-plus-price models, direction-specific calibration, portfolio/tail risk and forward paper evidence still require their own work and tests. The public repair register also remains open.

Unlazy's new seven-gate ledger has three manually reviewed outcomes and four automatic gates awaiting formal checker approval. Direct command results above are evidence of local verification, not checker certification. No approval was manufactured and no automatic gate was silently marked met. The [Unlazy skill](C:/Users/sakha/.codex/skills/unlazy/SKILL.md) says: "Only the user's explicit, inspected approval may cross that boundary." The formal reverify call reran zero commands and left four approvals pending; its working-directory definitions were corrected to the verified absolute paths before that call. This does not prevent the already-authorized development work or direct checks. GitNexus impact attempts returned UNKNOWN because storage version 42 is incompatible with runtime version 40; direct source callers limited this change to the private CLI/report/UI and tests. No zero-risk claim is made.
