# Federal Reserve FOMC statement history, 2015–2024

**Research status:** bounded source finding. This report identifies official Federal Reserve statement pages and the limits of using them. It does not acquire a source history, qualify a feature, or establish a trading result.

**Observation date:** 2026-10-02. The live official pages were inspected on this date. A current archive response is not evidence of what bytes were available to a user at the historical release time.

## Finding

The authoritative discovery source is the Federal Reserve's own meeting inventory. Use the [historical meeting pages for 2015](https://www.federalreserve.gov/monetarypolicy/fomchistorical2015.htm), [2016](https://www.federalreserve.gov/monetarypolicy/fomchistorical2016.htm), [2017](https://www.federalreserve.gov/monetarypolicy/fomchistorical2017.htm), [2018](https://www.federalreserve.gov/monetarypolicy/fomchistorical2018.htm), [2019](https://www.federalreserve.gov/monetarypolicy/fomchistorical2019.htm), and [2020](https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm), then the Fed's [meeting calendars and information page](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) for 2021–2024. The latter is a rolling page and should not be treated as an immutable manifest. The annual FOMC press-release index, for example [2024](https://www.federalreserve.gov/newsevents/pressreleases/2024-press-fomc.htm), is a useful second official cross-check.

The correct bounded inventory has **83 pages labelled “Statement” by those meeting indexes**. The expected yearly counts are `8, 8, 8, 8, 9, 10, 8, 8, 8, 8`. This count catches the October 2019 implementation statement, both emergency rate decisions in March 2020, the March 2020 notation-vote statement, and the cancelled March 17–18, 2020 meeting.

The ordinary archive route is:

```text
https://www.federalreserve.gov/newsevents/pressreleases/monetaryYYYYMMDDa.htm
```

Every date below resolved at that route on the observation date. The URL date is the **release date**, which is not always the meeting date.

| Year | Official statement release dates |
|---|---|
| 2015 | 01-28, 03-18, 04-29, 06-17, 07-29, 09-17, 10-28, 12-16 |
| 2016 | 01-27, 03-16, 04-27, 06-15, 07-27, 09-21, 11-02, 12-14 |
| 2017 | 02-01, 03-15, 05-03, 06-14, 07-26, 09-20, 11-01, 12-13 |
| 2018 | 01-31, 03-21, 05-02, 06-13, 08-01, 09-26, 11-08, 12-19 |
| 2019 | 01-30, 03-20, 05-01, 06-19, 07-31, 09-18, **10-11**, 10-30, 12-11 |
| 2020 | 01-29, **03-03**, **03-15**, **03-23**, 04-29, 06-10, 07-29, 09-16, 11-05, 12-16 |
| 2021 | 01-27, 03-17, 04-28, 06-16, 07-28, 09-22, 11-03, 12-15 |
| 2022 | 01-26, 03-16, 05-04, 06-15, 07-27, 09-21, 11-02, 12-14 |
| 2023 | 02-01, 03-22, 05-03, 06-14, 07-26, 09-20, 11-01, 12-13 |
| 2024 | 01-31, 03-20, 05-01, 06-12, 07-31, 09-18, 11-07, 12-18 |

The bold entries require explicit handling:

- [2019-10-11](https://www.federalreserve.gov/newsevents/pressreleases/monetary20191011a.htm) is grouped by the Fed under an **October 4 unscheduled meeting** and says the notation vote was completed October 11. Its title is **“Statement Regarding Monetary Policy Implementation,”** not “Federal Reserve issues FOMC statement.” The page calls the Treasury-bill purchases and repo operations purely technical measures and says they did not change the stance of monetary policy. Its directive restates the 1.75–2.00 percent target range effective October 15. It is an official statement-inventory row, not a target-range decision or directional rate signal.
- [2020-03-03](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200303a.htm) was released after the March 2 unscheduled meeting. It lowered the range to 1.00–1.25 percent at **10:00 a.m. EST**.
- [2020-03-15](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm) was an unscheduled Sunday decision. It lowered the range to 0–0.25 percent at **5:00 p.m. EDT**. The separate [implementation note](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a1.htm) says the relevant operating instructions and administered-rate settings were effective March 16.
- [2020-03-23](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200323a.htm) was an **8:00 a.m. EDT** notation-vote statement about securities purchases and market functioning. Its directive restates the 0–0.25 percent range; the page does not announce a new target range. Keep it in the statement inventory and outside the target-change sample.
- The scheduled March 17–18, 2020 meeting was cancelled. The March 19 and March 31 notation votes link to “Press Release,” not “Statement.” The August 27 item is a Statement on Longer-Run Goals and Monetary Policy Strategy. These are explicit non-rows for this narrowly defined inventory, not missing target statements.

## Release-clock evidence

All eight 2015 HTML pages say only **“For immediate release.”** They state no clock or timezone. A precise intraday timestamp for those pages is unavailable from this source and must not be inferred from later 2:00 p.m. practice.

The 2016–2024 ordinary meeting statements state **2:00 p.m.** and explicitly say EST or EDT. Preserve that literal source token and validate it against the date. The nonstandard clocks are:

| Release | Source-stated clock |
|---|---|
| 2019-10-11 implementation statement | 11:00 a.m. EDT |
| 2020-03-03 emergency statement | 10:00 a.m. EST |
| 2020-03-15 emergency statement | 5:00 p.m. EDT |
| 2020-03-23 notation-vote statement | 8:00 a.m. EDT |

A source-stated “For release at” line is a document property. It does not prove actual historical transmission, provider arrival, user receipt, or when a daily FX vendor incorporated the news.

## Announced target-range sequence

The statement body supports an **announced federal-funds target-range** observation. It does not provide the realised effective federal funds rate, an administered reserve rate, a futures expectation, an OIS or two-year yield, or a carry measure. Federal Reserve research on its [ample-reserves operating regime](https://www.federalreserve.gov/econres/notes/feds-notes/implementing-monetary-policy-in-an-ample-reserves-regime-the-basics-note-1-of-3-20200701.html) explains that the market-determined effective rate is steered within the target range using administered rates. Those are distinct quantities. Effective dates and operating settings require the separately linked implementation note.

There are 28 target-range changes in this inventory. The value after each change was:

| Year | Change date → announced target range, percent |
|---|---|
| 2015 | 12-16 → 0.25–0.50 |
| 2016 | 12-14 → 0.50–0.75 |
| 2017 | 03-15 → 0.75–1.00; 06-14 → 1.00–1.25; 12-13 → 1.25–1.50 |
| 2018 | 03-21 → 1.50–1.75; 06-13 → 1.75–2.00; 09-26 → 2.00–2.25; 12-19 → 2.25–2.50 |
| 2019 | 07-31 → 2.00–2.25; 09-18 → 1.75–2.00; 10-30 → 1.50–1.75 |
| 2020 | 03-03 → 1.00–1.25; 03-15 → 0–0.25 |
| 2021 | no target-range change |
| 2022 | 03-16 → 0.25–0.50; 05-04 → 0.75–1.00; 06-15 → 1.50–1.75; 07-27 → 2.25–2.50; 09-21 → 3.00–3.25; 11-02 → 3.75–4.00; 12-14 → 4.25–4.50 |
| 2023 | 02-01 → 4.50–4.75; 03-22 → 4.75–5.00; 05-03 → 5.00–5.25; 07-26 → 5.25–5.50 |
| 2024 | 09-18 → 4.75–5.00; 11-07 → 4.50–4.75; 12-18 → 4.25–4.50 |

Every other target-decision statement maintained the range. An unchanged range does not mean the statement contained no policy news: guidance, securities purchases, runoff, or implementation can change without a target move. Examples include September 20, 2017; October 11, 2019; March 23, 2020; and May 1, 2024.

A `change_from_prior_statement` field is valid only when the preceding target-decision statement has been captured and the official inventory proves that no intervening target decision is missing. A bounded 2015 sequence also needs the [2014-12-17 predecessor](https://www.federalreserve.gov/newsevents/pressreleases/monetary20141217a.htm) as a seed or must leave the first change comparison null. The October 2019 and March 23, 2020 restatements must not reset the target-decision predecessor. Even with a complete sequence, the result means “announced target-range change,” not monetary-policy surprise, implemented effective rate, or causal shock.

## Admission and completeness controls

1. Enumerate meeting and notation-vote headings from the correct official year page. Follow the link whose label is exactly “Statement” for the broad statement inventory. Record other named statements, implementation notes, minutes, SEP, and press releases separately.
2. Preserve `meeting_date_or_span` and `release_date` as separate fields. This catches October 4 → October 11, 2019 and March 2 → March 3, 2020.
3. Reconcile yearly counts to `8/8/8/8/9/10/8/8/8/8 = 83`. Preserve the cancelled meeting and headings with no Statement link as explicit audit exceptions.
4. Admit only a successful `federalreserve.gov` original whose visible release date matches the URL date. Store canonical URL, source title, stated clock and timezone when present, retrieval timestamp, content length, SHA-256, page `Last Update`, discovery-page URL, and document class.
5. Deduplicate by canonical URL and body hash. Fail closed on a missing body, ambiguous date, ambiguous range, or missing required clock. Do not manufacture a clock for 2015.
6. Classify `TARGET_DECISION`, `IMPLEMENTATION_ONLY_NO_STANCE_CHANGE`, and `OTHER_POLICY_STATEMENT`. Treat the March 23 directive as a target restatement, not a target change.
7. Extract a range only from an unambiguous decision sentence. Normalize published fraction typography only through tested, explicit mappings; retain the source text beside the numeric bounds.
8. Join implementation notes only as separate official documents. Do not copy their effective dates or administered rates into the announcement record without field-level provenance.

The current implementation is not yet a 2015–2024 history parser. A read-only replay of the 83 live HTML bodies through `pipeline/src/private_desk/releases.py` on 2026-10-02 admitted **33** and rejected **50** before any source rows were written: 25 for unsupported target-range wording, 24 for unsupported published fraction typography, and the October 2019 implementation statement for its different official title. The 2015 pages additionally lack the exact clock that the parser requires. These are parser-coverage findings, not reasons to discard official rows. Strict admission should be expanded only with page-specific fixtures and the classifications above.

## Archive and revision limit

The official HTML is a live archive, not a versioned point-in-time feed. A page has a release line and a `Last Update` line but no public byte-level revision history. The strongest concrete warning is [2019-10-11](https://www.federalreserve.gov/newsevents/pressreleases/monetary20191011a.htm): it says “For release at 11:00 a.m. EDT” on October 11 and “Last Update: October 15, 2019.” A body hash taken now makes the local capture immutable; it proves only which official bytes were retrieved now. It does not prove that those bytes, or the current calendar, were available at the historical release time.

Actual historical receipt therefore remains unavailable unless a separately preserved, timestamped capture or provider receipt is supplied. The same limitation applies to revision timing between initial release and the current page.

## Why a rate change is not a surprise

Official Federal Reserve research rejects the equation “target change = surprise.” Gürkaynak, Sack, and Swanson find that one target factor is insufficient and identify a separate expected-policy-path factor associated with the statement ([Federal Reserve FEDS paper](https://www.federalreserve.gov/econres/feds/do-actions-speak-louder-than-words-the-response-of-asset-prices-to-monetary-policy-actions-and-statements.htm)). The Fed's work on [federal-funds futures for policy analysis](https://www.federalreserve.gov/econres/feds/using-federal-funds-futures-contracts-for-monetary-policy-analysis.htm) defines the usual target surprise relative to a futures-implied expectation. A Fed note that uses the [60-minute change in the two-year Treasury yield](https://www.federalreserve.gov/econres/notes/feds-notes/monetary-policy-surprises-and-monetary-policy-uncertainty-20180518.html) says that measure captures both current-rate news and the expected path.

This archive supplies no pre-announcement expectation with a defensible timestamp. It therefore cannot support `surprise`, `expected component`, `unexpected component`, or causal-policy-impact fields. A separate, vintage-safe futures or intraday market source and an ex ante measurement rule would be required.

## Permitted daily-OHLC development sensitivity

A narrow descriptive test is supportable after the source history passes the controls above. It should be predeclared and labelled **MODELLED DAILY-OHLC DEVELOPMENT SENSITIVITY**:

- Use the seven conventional USD legs: EUR/USD, GBP/USD, AUD/USD, NZD/USD, USD/JPY, USD/CAD, and USD/CHF. This remains private research and does not widen the product's locked pair universe.
- Give every pair a fixed USD-return sign before viewing results: negate quote returns for EUR/USD, GBP/USD, AUD/USD, and NZD/USD; retain quote returns for USD/JPY, USD/CAD, and USD/CHF.
- If testing direction after a target move, map a higher range midpoint to USD-long and a lower midpoint to USD-short. Do not generate a directional row for an unchanged range, 2019-10-11, or 2020-03-23. Call this conditioning on an announced target change, never a surprise.
- Enter at the first canonical vendor daily open strictly after the source-stated release time. Predeclare the vendor's bar timezone and business-day calendar. Keep 2015 out of the timestamp-qualified cohort; any next-day, date-only result must be reported separately.
- Predeclare one 50/50 exit rule at the opens of business days 3 and 5. Preserve weekend/holiday gaps, missing bars, and incomplete exits; do not substitute a prior close or silently shorten a hold.
- Charge the fixed, documented development cost at entry and at each partial exit. Report gross and modelled net results separately. Generic spread/slippage/roll assumptions are stress inputs, not evidence of executable prices.
- Freeze event selection, signs, horizons, pair transforms, missing-data rules, and costs before inspecting outcomes. Do not tune ranking or event exclusions to the result.
- Treat an FOMC date as the sampling unit when reporting uncertainty. Seven correlated currency legs are not seven independent policy events. Report the small number of change events and clustered crisis observations plainly.

This design measures later daily drift conditional on a public announcement classification. It does not measure the immediate announcement return, isolate monetary-policy causality, establish a surprise, reproduce an executable order, qualify a forecast, or demonstrate strategy value. Source-timestamped expectations, intraday FX quotes with venue/provider receipt times, tradable spreads and slippage, financing/roll, and independent out-of-sample evaluation remain required for those claims.

## Bounded conclusion

The official 2015–2024 discovery manifest is usable, with 83 Statement-labelled pages and two statement-class exceptions that must remain explicit. The ordinary archive URL is reliable for this observed inventory but is not by itself a completeness proof. A target change can be computed only over a complete captured decision sequence, and it remains an announced policy level rather than a surprise or realised rate. Historical receipt, initial-release bytes, expectation vintages, and executable FX costs remain unavailable.
