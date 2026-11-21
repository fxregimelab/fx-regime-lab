# Research repair source report

Prepared 27 September 2026 for [the repair contract](../docs/RESEARCH_REPAIR_CONTRACT.md). Repository base: `9fa150538d08ab5a2a6c587976552944f47a724d`. Only the two new research documents were authored in this packet. No code, protected identity file, ledger, production pipeline or external account was changed.

Humanscope and its StoryScope reference were read for plain, evidence-conscious writing. StoryScope concerns fiction; it supplies no financial or statistical evidence here. Agent Reach's documented Exa route was exercised through `mcporter`; official pages and primary research were then read with the available web tool. No social-media opinion was used as evidence. `agent-reach check-update` could not run because the executable is not on PATH; no installation or runtime startup was attempted.

## Primary sources and what they support

Access date for every entry: 27 September 2026. Publication dates below describe the source, not the project's data vintage. Links establish methodology or source semantics; they do not establish the engine's performance.

| Source | Verified use and limit |
|---|---|
| [FRED DGS2](https://fred.stlouisfed.org/series/DGS2) | US Treasury two-year constant-maturity yield, daily, percent. Used to audit instrument matching; no forecast claim. |
| [FRED ECBDFR](https://fred.stlouisfed.org/series/ECBDFR) | ECB deposit facility rate. Not a two-year euro sovereign yield. |
| [FRED Japan long yield](https://fred.stlouisfed.org/series/IRLTLT01JPM156N) | OECD monthly ten-year government yield metadata. A monthly observation needs its actual availability date. |
| [FRED India long yield](https://fred.stlouisfed.org/series/INDIRLTLT01STM) | Monthly ten-year government-yield metadata. No verified two-year replacement feed is established by this audit. |
| [Federal Reserve, policy expectations and exchange rates, 22 September 2017](https://www.federalreserve.gov/econres/notes/ifdp-notes/the-sensitivity-of-the-us-dollar-exchange-rate-to-changes-in-monetary-policy-expectations-20170922.htm) | Distinguishes expected policy from surprises and uses relative OIS changes around announcements. Supports a news hypothesis, not daily level-z-score predictability. |
| [Federal Reserve, global tightening, 10 May 2024](https://www.federalreserve.gov/econres/notes/feds-notes/monetary-policy-and-exchange-rates-during-the-global-tightening-20240510.html) | Reports heterogeneous exchange-rate relationships, with clearer findings for advanced economies. Counters a universal rate-to-FX mapping. |
| [BIS, covered interest parity, September 2016](https://www.bis.org/publ/qtrpdf/r_qt1609e.htm) | Covered parity and persistent cross-currency basis. Forward premium needs funding/instrument interpretation; it is not a spot forecast. |
| [BIS Quarterly Review, December 2007](https://www.bis.org/publ/qtrpdf/r_qt0712.pdf) | Carry versus uncovered parity discussion; investing in a higher-yield currency does not remove exchange-rate risk. Used for theory, not a current empirical estimate. |
| [Brunnermeier, Nagel and Pedersen, Carry Trades and Currency Crashes](https://www.journals.uchicago.edu/doi/abs/10.1086/593088) | Original research identifying carry crash concerns. Publisher abstract/index evidence only in this audit; no numerical claim or replicated result is imported. |
| [BoJ intervention operations, revision June 2023](https://www.boj.or.jp/en/intl_finance/outline/expkainyu.htm) | Minister of Finance decides; BoJ executes as agent. Establishes authority, not an estimated reaction function. |
| [MoF July–September 2024 interventions, released 8 November 2024](https://www.mof.go.jp/english/policy/international_policy/reference/feio/quarter/2024_3Qe.html) | Actual July 11–12 dollar sales/yen purchases; separates transaction dates from publication. Does not prove a permanent spot threshold or intervention effect. |
| [RBI Bulletin policy discussion](https://rbi.org.in/Scripts/BS_ViewBulletin.aspx?Id=22995) | Official discussion of two-sided intervention and no specific targeted exchange-rate level. Institutional description, not identification of daily events. |
| [RBI exchange-market and reserve discussion](https://rbi.org.in/scripts/PublicationsView.aspx?Id=18086) | Reserve changes include valuation and income; intervention is not a one-for-one measure of market excess demand. Used to reject a simple reserves-equals-intervention label. |
| [CFTC release schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm) | 15:30 Eastern publication, normally Friday for Tuesday positions, plus explicit 2026 holiday delays. Historical experiments need the relevant historical schedule. |
| [CFTC TFF explanatory notes](https://www.cftc.gov/idc/groups/public/%40commitmentsoftraders/documents/file/tfmexplanatorynotes.pdf) | Trader categories based on activity. Categories are not a ranking of forecasting skill. Correct source is TFF, not physical-commodity disaggregated categories. |
| [CME yen futures specifications](https://www.cmegroup.com/markets/fx/g10/japanese-yen/specs) | USD per JPY quotation; confirms inversion relative to USD/JPY spot. Search returned official contract details; page variants may redirect. |
| [FRED real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) and [ALFRED](https://fred.stlouisfed.org/docs/api/fred/alfred.html) | Latest data and historical information sets differ; vintage fields are necessary. These do not guarantee every required series has sufficient vintage coverage or intraday release timestamps. |
| [Gneiting and Raftery, 2007](https://doi.org/10.1198/016214506000001437) | Proper scoring rule foundation. Brier calculations in the contract are explicit algebra, not source-reported project results. |
| [scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html) | Fitted sigmoid/isotonic calibration and independence of calibration data. Does not endorse the repository's affine heuristic. |
| [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) | Time-ordered splitting and gap parameter. Project-specific label-interval purging, timestamp checks and dependence policy remain additional requirements. |
| [Bailey, Borwein, López de Prado and Zhu, The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) | Primary author-hosted research on selection across backtests. Supports recording trial count and selection; no probability of this project's overfitting is estimated. |

## Repository evidence inspected

Read the authority chain: `AGENTS.md`, `IDENTITY.md`, `MASTERPLAN.md`, `TASK.md`, the relevant council workflow and `docs/REPAIR_REGISTER.md`. Inspected `pipeline/universe.json`; `src/fetchers/yields.py`; rate, COT, special, intervention, FPI, volatility and open-interest signal functions; composite/confidence functions; historical simulator; permutation diagnostic; internal sizing simulator; and the SSRN draft's method/result claims. Paths under `src/` in this report refer to `pipeline/src/`.

The important observed mismatches are recorded by symbol/file in the contract: rate-instrument definitions, USD-versus-pair orientation, same-period correlations described as precision, affine confidence described as Platt calibration, proxy substitutions and incomplete replay/diagnostic parity. These findings are source inspection, not results of a live data query. Other agents may be repairing adjacent files concurrently; the evidence anchors identify the inspected base and symbols so later reviews can resolve changes.

GitNexus query was attempted before direct source navigation. It returned no flows and warned that FTS indexes were missing. No function/class/method was edited in this packet, so symbol-impact edits were not needed; no commit was made. A memory registry search for this project returned no relevant entry and supplied no facts to the documents.

## Source and acceptance gaps

- No point-in-time data export, vendor license/coverage audit or actual vintage replay was performed. OIS expectations, matching local two-year yields, 25-delta risk reversal, source IV, timestamps for FPI and forwards, and detailed intervention labels remain gated by verified feeds.
- A guessed CFTC TFF HTML path and NBER landing page did not resolve through the web tool. Replaced them with the official CFTC PDF and the original research publisher link; no failed page is used as evidence.
- Source inspection does not confirm today's production path or published numerical cohort. The SSRN draft's counts, accuracy and Brier values remain unverified and must not be repeated as accepted results.
- The protocol's block lengths, paired uncertainty, promotion gates and manifest fields are explicit proposed research safeguards. They are not external standards guaranteeing skill or a substitute for a preregistered power/precision calculation.
- Protected `IDENTITY.md` was left intact. Its Japan intervention assertion requires owner-authorized textual correction; the contract supplies the exact proposed replacement and evidence.
- This packet requires no Docker, gateway, watchdog or pipeline execution. No temporary runtime was started. It leaves the Hermes MCP configuration unchanged.

Acceptance for this packet is a reviewable specification and source ledger. Closing the linked repair items requires their implementation, deterministic fixtures, frozen data, experimental receipts and any applicable release/live evidence.
