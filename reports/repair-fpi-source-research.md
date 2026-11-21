# FPI source and dated observation repair

Research date: 27 September 2026. Owned output: this report only; leaf 20.1, wave20-research. Reviewed checkout: `9fa150538d08ab5a2a6c587976552944f47a724d` plus the shared, uncommitted repair work. No provider ingestion, database access/write, model call, credential use, service startup or deployment was performed. Public pages were read with web search and Agent Reach's Jina Reader route. Humanscope and Research instructions applied.

The production FPI feature needs a source-qualified, dated observation record before it can safely affect a call. Restoring `fpi_flow` to a database projection would fix only one defect. The present scraper does not implement the actual official table, and a bare amount does not establish which market activity it measures or when it became available.

## Official evidence and its limits

| Source read | Verified finding | Limit |
|---|---|---|
| [NSDL production latest report](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx) | The public rendered page showed one investment block dated 25-Sep-2026, followed by a separate derivatives report. Investment columns and category groups are described below. An Excel export is advertised. | Direct browser retrieval returned 502; direct `curl` returned connection reset, exit 56. Jina Reader succeeded. No operational direct-ingestion reliability, downloaded Excel schema or official release timestamp was established. |
| [NSDL production current-month report](https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx) | The rendered page showed 18 daily reporting-date blocks from 1 through 25 September 2026. It is a collection of daily observations, despite the URL name. | Observed dates: 1, 2, 3, 4, 7, 8, 9, 10, 11, 15, 16, 17, 18, 21, 22, 23, 24, 25. This does not prove a complete expected reporting calendar or an immutable archive. |
| [NSE FII/FPI and DII activity](https://www.nseindia.com/reports/fii-dii) | NSE distinguishes its own exchange coverage from the combined NSE/BSE/MSEI capital-market series. Its indexed official note describes T-day trades, provisional data, custodial confirmations/modifications and physical-settlement expiry obligations. It directs readers to NSDL/CDSL for final FPI data. | The rendered page did not populate the daily numbers in this read. Do not replace confirmed depository observations with these provisional trades under the same series identity. |
| [SEBI URL currently used by the code](https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&smsId=2283&smsTitle=FPI) | Jina returned the general SEBI homepage, with news and departments. No `Date / Equity / Debt / Total` FPI table was verified. | HTTP success or four table cells would not prove the required dataset. The claimed 18:00 IST publication and 30-day archive limit remain unsupported. |
| [SEBI February 2026 Bulletin](https://www.sebi.gov.in/sebi_data/attachdocs/feb-2026/1771916844403.pdf) | The official bulletin footnote says FPI net investment includes mutual-fund investment from September 2024. | A historical total changes meaning when coverage expands; do not silently splice definitions. This monthly bulletin is not evidence for a daily 18:00 release. |
| [RBI Table 35, 22 July 2026](https://www.rbi.org.in/Scripts/BS_ViewBulletin.aspx?Id=24344) | Public table, read via Jina, is in USD millions, with monthly and financial-year cumulative columns. FPI is component 1.2.2. Net portfolio investment also includes GDR/ADR and offshore funds, and subtracts portfolio investment by India. The table marks provisional data and warns of reporting-lag differences from balance-of-payments data. | This release contains May 2026 observations. That is one observed lag, not a promised publication calendar. It cannot reconstruct daily FPI observations. |
| [CDSL FPI publication directory](https://www.cdslindia.com/Publications/ForeignPortInvestor.html) | Public depository report directory, separately listing daily and fortnightly material. | Directory visibility does not establish identical coverage, complete history or interchangeability with NSDL. No alternate ingest adapter was verified. |

The [NSDL pilot monthly page](https://pilot.fpi.nsdl.co.in/Reports/Monthly.aspx) initially provided October 2025 schema evidence; the production pages subsequently confirmed the current rendered structure. Pilot values are not an approved live fallback. Search snippets were followed to primary publishers; secondary sites were not used as evidence.

NSDL's explanation distinguishes confirmed trades reported by custodians from provisional exchange trades. The confirmed reports can cover trades on and before earlier trading days. Preserve **reporting date**; do not relabel it as trade date, settlement date, or publication time. “Confirmed” also does not prove immutable values or a one-day universal settlement mapping. No revision timetable, historical first-release archive, complete coverage start date, or fixed publication hour was verified. [NSDL explanation](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx)

## Verified table structure and parser requirements

The investment table's eight logical columns are reporting date; asset category; investment route; gross purchases in INR crore; gross sales in INR crore; net investment in INR crore; net investment in USD million; and INR per USD conversion. The category header still mentions only a subset of the categories actually present: trust validated row labels, not that abbreviated heading alone. [NSDL latest report](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx)

For each reporting date, the rendered grouping is:

| Category | Detail rows, followed by one subtotal |
|---|---|
| Equity | Stock Exchange; Primary market & others |
| Debt-General Limit | Stock Exchange; Primary market & others |
| Debt-VRR | Stock Exchange; Primary market & others |
| Debt-FAR | Stock Exchange; Primary market & others |
| Hybrid | Stock Exchange; Primary market & others |
| Mutual Funds | Equity schemes; Debt schemes; Hybrid schemes; Solution oriented schemes; Other schemes |
| AIFs | Stock Exchange; Primary market & others |

One final total follows all seven subtotals: 25 rendered rows per complete date block. VRR means Voluntary Retention Route; FAR means Fully Accessible Route. These are distinct debt routes, not currency-conversion observations. [NSDL structure](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx), [RBI description of the three debt channels](https://systemhealth.rbi.org.in/Scripts/AnnualReportPublications.aspx_Id%3D1402.html)

Observed 25-Sep-2026 net subtotals, in INR crore: equity **-4,521.96**; general-limit debt **220.75**; VRR **-1,012.18**; FAR **-1,442.62**; hybrid **4.36**; mutual funds **198.94**; AIF **0.00**; published total **-6,552.71**. This is a bounded source example, not an imported production observation. [NSDL latest report](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx)

Implement the parser against captured original HTML, not a guessed ordinal-cell scraper or search text:

1. Locate the investment table by its full heading and validated logical column labels. Stop before the derivative-trades table. Check its report date against the requested snapshot scope.
2. Expand actual `rowspan`/`colspan` into a logical grid, then validate category and route boundaries. **Actual DOM attributes, table IDs and span counts were not available in this investigation.** The reader omits repeated date/category/conversion fields, but that does not establish how the original HTML encodes them. Capture raw HTML and inspect it before implementing selectors. Do not present an invented HTML excerpt as evidence.
3. Parse decimals, commas and parenthesized negatives strictly. Reject blanks, dashes, nonfinite values, unknown categories, duplicate routes or categories, and ambiguous units. A printed numeric zero is valid; a missing row is not zero.
4. Retain all seven categories and their detail rows. Validate purchases minus sales against net, detail sums against category subtotal, and the seven subtotals against the published total. Use decimal arithmetic and a documented rounding tolerance based on displayed precision (at most the summed half-unit rounding bounds); never silently replace the published total with a partial sum.
5. Preserve INR and USD fields separately. A displayed converted USD value does not document an actual FX transaction. The starred conversion footnote was not exposed by the rendered `Note` link; its rate-source rule remains unverified for this current table.
6. Save unknown schema or failed reconciliation as unavailable evidence with the raw capture retained. A page response, parse exception, or site homepage is not a successful zero-flow observation. Monthly captures must preserve each reporting-date block, not only the headline date.

## Economic interpretation

These are securities purchases and sales reported through an institutional reporting process. They do not identify when a foreign investor converted USD to INR, how much was funded from an existing rupee balance, whether proceeds were reinvested, or whether currency exposure was hedged. Treat their potential relationship with USD/INR as a hypothesis requiring dated evaluation. An INR purchase total is not measured USD selling. RBI's own older [foreign-investment discussion](https://www.rbi.org.in/Upload/AnnualReport/Pdfs/56232.pdf) explicitly distinguishes investment inflows from exchange investment statistics; its historical numbers are not current observations.

A holdings/AUC change is also not a flow: valuation and exchange-rate changes can alter stocks without purchases. Keep derivatives turnover/open interest, AUC, debt-limit utilization, monthly balance-of-payments aggregates and daily securities net investment in separate series.

The existing normalizer measures deviation from a prior median. An outflow of -100 after typical -1,000 outflows can score positive. Calling that “positive inflow” or treating it as established INR demand is wrong. Preserve the raw amount, the relative-deviation score and the experimental directional mapping as separate fields. Constant history provides no usable scale; choose an explicit unavailable/degenerate-scale status rather than asserting normal evidence from zero MAD.

## Implementable observation and decision contract

The following is a proposed versioned engineering contract, not a statement of source publication policy.

**Identity.** Use a series key containing publisher, report family, confirmation basis, frequency, units, coverage version and category/route. Proposed aggregate: `NSDL_FPI_CONFIRMED_REPORTED_ALL7_INR_CRORE_DAILY_V1`. It is the published total across the seven categories above. Store components even when using the total. A restricted equity-plus-debt feature must have a different explicit key and model version; never label it the all-category total. NSE-only/combined provisional activity, RBI monthly FPI, and NSDL confirmed reports never share a key.

**Observation record.** Require `series_id`, `reporting_date`, `date_basis=reporting_date`, nullable `trade_date` and `settlement_date`, signed decimal values, category components, `source_url`, raw bytes SHA-256, canonical observation SHA-256, schema/parser version and quality status. An all-category observation hash covers its date, units, definitions and every component, not just the final net amount. One crore is ten million INR; use explicit conversions, never a unit guess.

**Knowledge times.** Require timezone-aware UTC `retrieved_at` for every capture, and immutable `first_seen_at` for each distinct observation hash. Record optional publisher `released_at` only when evidenced for that exact vintage, with time precision and evidence. A page-wide modified date, reporting date or assumed 18:00 is not release evidence. Until independently established otherwise, set decision `available_at=first_seen_at`, the first successful verified retrieval of that vintage. Do not backdate the 18 September rows first collected on 27 September. A reader's cached page is research evidence here, not an earlier system availability record.

**Vintages and revisions.** Store captures and observations append-only through `pipeline/src/db/writer.py`. A revised same-date category value produces a new observation hash/version and first-seen time; preserve the old version. An unchanged repeated capture updates neither first-seen nor availability. Store retrieval provenance separately so a new monthly page hash does not falsely revise every unchanged date. Conflicting contents with the same series/date/availability ordering, or a later invalidated observation, fail closed rather than selecting whichever database row happens to arrive first.

**Selection at decision instant `T`.** One shared pure selector serves daily scheduler, staged pipeline and replay:

1. Require the frozen expected series/version, date basis and units. Exclude unknown provenance, invalid schema and unavailable/rejected evidence. Require `available_at <= T` and, if publisher release time exists, `released_at <= T` too. Use the same recorded instant `T` as the rest of the call's input snapshot.
2. For each reporting date select the last valid vintage known by `T`, using first-seen ordering plus deterministic version identity. Resolve conflicts explicitly; do not use post-`T` revisions. Never let a malformed latest revision silently resurrect an older value.
3. Pick the latest eligible **reporting date** as current. A late revision to an older date must not become current merely because it was fetched last. Reject future reporting dates relative to `T` in Asia/Kolkata.
4. Select distinct, strictly earlier reporting dates from the same series, as known by the same `T`. Sort oldest first and take the last 20. Exclude the current date and all its revisions. Require at least 10 prior observations, matching the present normalizer's minimum, and store the actual count/window dates.
5. Suggested initial engineering limits, to freeze and evaluate: current reporting date no more than five calendar days old in India; prior observations within 45 calendar days. These limits are conservative operating choices, not inferred publication promises. Explicitly known missing expected reports break the window; absent source rows cannot automatically be called holidays. Until a reviewed source reporting calendar exists, expose calendar coverage as unverified and restrict the feature to research status. Never compress arbitrary gaps into an apparently daily sample or expand monthly data into days.
6. Return the selected observation IDs/hashes, exact prior window, raw amount, normalized feature or `None`, and specific quality reasons. The model consumes only an eligible feature. Repeated use of the same latest source observation across FX sessions must retain its source date and age; it must not create additional history observations.

**Research modes.** A replay claiming point-in-time validity uses exactly the observations demonstrably known before each decision. A historical archive downloaded today without old release vintages supports only explicitly labelled current-vintage research for earlier decisions. Those historical observations can legitimately form the reference window for a new decision made after today's complete, validated capture: they were known by that new decision even though their earlier availability is unknown. Their immutable first-seen times must remain today. Persist dedicated capture receipts and per-observation hashes through the immutable writer before qualifying them for live use. Do not combine research modes, manufacture old first-seen times, or claim out-of-sample live evidence from reconstructed records. There is no authorised record rewrite here.

## Code findings and migration

Current `pipeline/src/fetchers/fpi_india.py` scans any four-cell table at the SEBI listing URL, guesses the first four column meanings, can synthesize total from equity and debt, and equates target date with the source observation. It stores no knowledge time, revision or coverage. Its historical loop re-requests the same page for every date; that is not verified historical access.

`pipeline/src/scheduler/orchestrator.py` constructs `historical_fpi` from numeric `fpi_flow` values after loading generic signal history, then fetches for the FX bar date. `writer.get_historical_signals` currently omits `fpi_flow` and supplies no source vintage. The requested name `get_historical_signal_rows` was not present in this checkout. The rate-history qualification step does not establish FPI provenance. `normalize_fpi_signal` expects chronological numeric history but cannot enforce dates or availability. `staged/stages/signal_stage.py` supplies no FPI; `backfill/simulation_engine.py` loads naked historical raw amounts but deliberately leaves the normalized feature unavailable. Those paths must not become a mixture of live FPI and silently absent replay FPI.

Migration sequence:

1. Retire the unsupported SEBI parser and correct its claims. Preserve existing naked `signals.fpi_flow` as legacy evidence with unknown series/vintage, not accepted point-in-time history.
2. Add offline parser fixtures from actual validated production captures and an immutable capture/observation contract. Audit downstream dependencies before schema changes; all writes remain in `writer.py`. This report author did not acquire a raw HTML fixture or run ingestion.
3. Implement the pure dated selector and use its identical output in scheduler, staged path and simulation. Keep the scalar normalizer downstream of that selector; never repair the issue solely by adding a database column to a SELECT.
4. Begin prospective capture only after the authorised implementation passes parsing, revision, missingness and time-cutoff tests. Capture Latest and current-month pages to detect late revisions; document month-boundary/archive retrieval separately before assuming historical coverage. Production capture must show real source reachability, persisted hashes and UTC first-seen evidence. A Jina research read does not prove that gate.
5. Keep FPI unavailable to production calls until a validated current observation, qualified history, coverage policy and model identity are present. Then enable the explicitly versioned input without rewriting prior calls. Frozen evaluation must compare the same cohort with/without FPI and account for overlapping outcomes and model selection; no accuracy gain is assumed.

Independent acceptance examples:

- For the observed 25-Sep report, equity plus general-limit debt is -4,301.21, not the published -6,552.71. Adding all debt routes still excludes hybrid/MF/AIF. A partial total must fail its identity contract.
- A September report first captured in October is unavailable to a September decision, even if its printed date precedes that decision. A same-date correction first seen at 18:10 cannot affect an 18:00 replay.
- A late revision of Monday observed on Thursday must not replace Wednesday as the latest reporting-date observation. Revised current date must not also appear in prior history.
- Equal-valued flows on ten distinct dates are ten observations; ten captures of one date are one. Same net total with changed offsetting categories is a new vintage.
- NSE provisional equity and NSDL all-category confirmed investment can have different signs without either being a parsing error. Refuse source substitution and synthetic reconciliation.
- RBI monthly +100 cannot determine whether daily paths were +100 then zero, -100 then +200, or something else. Linear interpolation produces invented information and can leak the later monthly release into earlier days.
- A negative raw amount above a more negative historical median must retain its outflow label even if its relative score is positive. Missing/degenerate history remains unavailable.

`docs/V2_NSDL_FPI_RESEARCH.md` needs replacement or a prominent superseded notice: its e-voting source, SEBI table/schedule/archive assertions, same-day claims, INR-only claim, unsupported vendor pricing/tickers, monthly-to-daily interpolation and blanket copyright/scraping assertion are not an accepted implementation basis. Current NSDL pages include restrictive reproduction/redistribution terms; public readability does not establish permission for unrestricted redistribution. Source-specific terms and permitted public output need review before publishing acquired tables. Do not introduce a paid subscription as a repair prerequisite.

Remaining evidence gaps: original HTML/Excel schema and fixtures; stable direct access; exact current conversion footnote; complete reporting calendar and historical coverage; publication times and revision archive; authorised prospective persistence; accepted model evaluation. No Docker or heavy Hermes component was required for this document-only task. The Hermes MCP configuration was not changed. Agent Reach's optional CLI update check could not run because `agent-reach` was absent from this shell; its documented public reader route worked.
