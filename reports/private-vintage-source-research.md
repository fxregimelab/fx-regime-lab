# Private historical macro vintage evidence: FRED and ALFRED

**Research date:** 2026-10-01  
**Scope:** read-only source qualification for the private seven-pair desk (EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF and EURGBP; 2–5-day holds)

## Bounded finding

FRED's ordinary current series is not historical point-in-time evidence. ALFRED can return the values that were recorded as known on a specified calendar date, but its vintage dates are day-level and do not establish an intraday publication time or timezone. A daily backtest needs separately verified source-release and availability evidence before assigning a value to a decision cutoff. A next-trading-day delay could be tested as an explicit assumption; it does not establish exact availability or qualify a value by itself. The implemented private-desk audit keeps release timing UNKNOWN and decision qualification UNQUALIFIED.

This source work does not qualify the current private-desk baseline, establish historical macro coverage, or show a profitable strategy. Actual releases also do not contain market expectations, so they cannot by themselves produce an "expectation surprise" feature.

## What the first-party contract establishes

The official `fred/series/observations` endpoint accepts `series_id`, `realtime_start`, `realtime_end`, `observation_start`, `observation_end`, `units`, optional lower-frequency aggregation, `output_type`, and `vintage_dates`. API v1 requires a registered 32-character API key. The official examples show a JSON envelope containing the requested real-time and observation boundaries, transformation (`units`), output type, ordering, pagination fields, and an `observations` array. For the default `output_type=1`, each row contains `realtime_start`, `realtime_end`, `date`, and string `value`. The per-request observation limit is 100,000; the service documents a rate limit of 120 requests per minute. [Series observations](https://fred.stlouisfed.org/docs/api/fred/series_observations.html) · [API key](https://fred.stlouisfed.org/docs/api/api_key.html) · [errors and rate limit](https://fred.stlouisfed.org/docs/api/fred/errors.html)

The four output types mean:

| `output_type` | Official meaning | Safe interpretation |
|---:|---|---|
| 1 | Observations by real-time period | Revision records whose validity interval intersects the requested closed day range. |
| 2 | Observations by vintage date, all observations | A cross-tab: observation dates down rows, selected vintage dates across columns, with every value available on each selected date. |
| 3 | Observations by vintage date, new and revised observations only | The same cross-tab, but unchanged values are omitted; cells contain only values first available or revised on that vintage date. |
| 4 | Observations, initial release only | One first-published value per observation date. The initial release date is the row's real-time start date. |

Sources: [series-observation output types](https://fred.stlouisfed.org/docs/api/fred/series_observations.html#output_type) and [ALFRED download-format definitions](https://alfred.stlouisfed.org/help/downloaddata#outputformats).

For output types 2 and 3, the ALFRED help page defines the semantic table exactly, and the API page warns that XML value-field names are based on the series ID. The public API documentation does **not** publish a JSON example for types 2, 3, or 4. Their exact JSON row keys must be captured and schema-tested using an authorized API key before implementation; this report does not invent them.

`realtime_start` and `realtime_end` are inclusive (`closed, closed`) `YYYY-MM-DD` dates. They mark when a fact was considered true or known until it changed. Both default to today's date on almost all endpoints. `vintage_dates` is an alternative comma-separated list of dates on which to ask what the latest available data were, even if no revision occurred on that date. [Real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) · [vintage-date parameter](https://fred.stlouisfed.org/docs/api/fred/series_observations.html#vintage_dates)

Vintage requests are bounded. The documented maximum is 2,000 selected vintage dates for JSON or XML. CSV/XLSX limits are normally 1,000, but output type 2 is lower for a daily series (450 CSV/225 XLSX) and for `USRECD` (110 CSV/55 XLSX). The observation row limit remains 100,000 and pagination uses `offset`. These limits make one series/one as-of date the safer auditable unit than a broad multi-vintage pull. [Vintage-date limits](https://fred.stlouisfed.org/docs/api/fred/series_observations.html#vintage_dates)

## Missing values, revisions and metadata

- For output type 3, a blank cell means “not new or revised on this vintage,” not necessarily “economic observation missing.” Type 2 is required to reconstruct the complete as-of panel.
- In ALFRED's text downloads, an unknown current `realtime_end_date` is represented by `.`; Excel uses `#NA`. This is an open-ended validity interval, not a missing observation value. [ALFRED real-time-period format](https://alfred.stlouisfed.org/help/downloaddata#obsbyvalidperiod)
- The current API examples also use `.` as a missing observation value. Any parser must keep this distinct from numeric zero. [FRED v2 observation example](https://fred.stlouisfed.org/docs/api/fred/v2/release_observations.html)
- `fred/series` supplies title, observation span, frequency, units, seasonal adjustment, `last_updated`, and notes as they were valid in the requested real-time period. `fred/series/release` maps the series to its release. These metadata must be queried with the same as-of boundary as the values because series titles, units, seasonal adjustment and notes can change through time. [series metadata](https://fred.stlouisfed.org/docs/api/fred/series.html) · [series release](https://fred.stlouisfed.org/docs/api/fred/series_release.html)
- `units` on `series/observations` is a transformation request (`lin`, changes, percent changes, annualized changes, log), not the source series' measurement unit. Frequency can only be aggregated downward, with average, sum, or end-of-period. Preserve the source units/frequency from series metadata and request `units=lin` unless a transformation is explicitly part of the feature definition. [units and frequency](https://fred.stlouisfed.org/docs/api/fred/series_observations.html#units)

## Day-level availability is not intraday availability

Neither observation dates nor ALFRED vintage dates contain a clock time or timezone. `fred/release/dates` returns calendar dates published by the source and explicitly warns that these dates do not necessarily say when the data became available on FRED or ALFRED. A series page's `last_updated` timestamp describes a FRED update and cannot be substituted for the original market release time without separate proof. [release dates](https://fred.stlouisfed.org/docs/api/fred/release_dates.html) · [series metadata](https://fred.stlouisfed.org/docs/api/fred/series.html)

ALFRED's own help page sharpens this limitation. It says a release date is the date new data first became available from the source, but the date may fall back from the source's date to a data provider's date and finally to the date the series first appeared in FRED. It also says ALFRED normally adds new/revised values “typically within one business day.” Thus an ALFRED vintage date is neither an ingestion timestamp nor proof that FRED carried the value at a specific clock time. [ALFRED help: release dates, ingestion and verification](https://alfred.stlouisfed.org/help)

For a 2–5-day strategy, store at least `observation_date`, `vintage_date`, `source_release_timestamp`, `decision_at`, source timezone, series ID, units/frequency/seasonal adjustment, raw value, and retrieval evidence. If a first-party source does not establish the release time, keep that field unknown. A next-trading-day delay is an assumption for sensitivity research, not verified timing. Same-day use is not defensible from ALFRED alone.

## Genuine archived observations: current bounded route

The first-party, key-backed route is `fred/series/observations` with `file_type=json`, `units=lin`, an exact `series_id`, and either one `vintage_dates=YYYY-MM-DD` or `realtime_start=realtime_end=YYYY-MM-DD`. Start with one series, one as-of date, and the smallest needed observation window; retain the raw response and hash. Use `fred/series/vintagedates` to learn dates on which that series changed, but do not treat the list as complete source-release history: the endpoint excludes release dates when the series did not change. [series vintage dates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html)

The smallest justified full as-of request is output type 2 with one vintage date:

```text
GET https://api.stlouisfed.org/fred/series/observations
  ?series_id=CPIAUCSL
  &file_type=json
  &output_type=2
  &vintage_dates=YYYY-MM-DD
  &observation_start=YYYY-MM-DD
  &observation_end=YYYY-MM-DD
  &units=lin
  &limit=<bounded row count>
  &api_key=<registered key>
```

Choose `vintage_dates` from the strategy's decision cutoff, not from the observation period. Separately verify the release timestamp, source identity and which value was available before that cutoff. A source-release timestamp alone does not prove when an archived provider carried the same value. If only a release/vintage date is known, retain a calendar-date audit and leave exact decision-time use unqualified. Any previous-trading-day lag remains an explicit sensitivity assumption. Output type 3 is a change log, not a complete feature panel. Output type 4 is useful for studying first estimates, but it does not answer what the full information set contained on a later decision date.

Two directly verified examples:

- `CPIAUCSL` is monthly, seasonally adjusted US CPI. Its ALFRED page exposes revisions and historical metadata, including an explicit warning that some old vintages contain only the final 1.5 years because complete history is unavailable. It is therefore usable only inside the series page's stated vintage/observation coverage, never by assuming that a modern full history existed in an old vintage. [CPIAUCSL in ALFRED](https://alfred.stlouisfed.org/series?seid=CPIAUCSL)
- `DGS2` is the daily US 2-year constant-maturity Treasury yield in percent. Its ALFRED page shows vintage-aware records, but a daily market yield's observation date still does not establish when that value was available during the day. [DGS2 in ALFRED](https://alfred.stlouisfed.org/series?seid=DGS2)

For euro-area, UK, Australia, New Zealand, Canada and Switzerland CPI or rate candidates, qualify each exact FRED series separately. A country label is not enough: verify instrument identity, source, original frequency, units, seasonal adjustment, earliest vintage date, per-vintage observation coverage, and release-time evidence. Do not silently substitute a current FRED history for an absent ALFRED vintage, and do not substitute a policy rate, short-term money-market rate or 10-year yield for a required 2-year sovereign yield.

The following first-party pages are useful candidates for a qualification queue, not accepted sources yet:

| Currency area | Candidate series verified on FRED/ALFRED | What is known | Why it remains unqualified |
|---|---|---|---|
| United States | [`CPIAUCSL`](https://alfred.stlouisfed.org/series?seid=CPIAUCSL) | Monthly, seasonally adjusted CPI index; archived metadata reaches 1972. | ALFRED warns that vintages from 1972-07-21 through 1994-02-16 show only the last 1.5 years of observations. |
| United States | [`DGS2`](https://alfred.stlouisfed.org/series?seid=DGS2) | Daily 2-year Treasury constant-maturity yield, percent; ALFRED metadata intervals shown from 2005-06-28. | The current observation series starts earlier, but that does not prove full vintage coverage before the archive's shown real-time metadata. It still has no intraday timestamp. |
| Euro area | [`CP00MI15EA20M086NEST`](https://alfred.stlouisfed.org/series?seid=CP00MI15EA20M086NEST) | Monthly, not seasonally adjusted HICP index for the current 20-country composition. | Membership/base changes and the page's recent archived metadata must be reconciled; it is not a long stable EUR inflation identity without splicing rules. |
| United Kingdom | [`GBRCPALTT01IXNBM`](https://alfred.stlouisfed.org/series?seid=GBRCPALTT01IXNBM) | Monthly, not seasonally adjusted CPI index from OECD. | Page is stale at 2023 and the release/metadata interval is recent; no complete vintage coverage is established. |
| Australia | [`AUSCPIALLQINMEI`](https://alfred.stlouisfed.org/series?seid=AUSCPIALLQINMEI) | Quarterly, not seasonally adjusted CPI index from OECD. | Quarterly frequency and finite OECD vintage history may be too sparse for a 2–5-day feature. |
| New Zealand | [`NZLCPIALLQINMEI`](https://alfred.stlouisfed.org/series?seid=NZLCPIALLQINMEI) | Quarterly, not seasonally adjusted CPI index from OECD. | Same sparsity and vintage-coverage issue as Australia. |
| Canada | [`CANCPIALLMINMEI`](https://alfred.stlouisfed.org/series?seid=CANCPIALLMINMEI) | Monthly, not seasonally adjusted CPI index from OECD. | Page is stale at 2025; release time and complete vintage coverage are unverified. |
| Switzerland | [`CHECPIALLMINMEI`](https://alfred.stlouisfed.org/series?seid=CHECPIALLMINMEI) | Monthly, not seasonally adjusted CPI index from OECD. | Page is stale at 2025; release time and complete vintage coverage are unverified. |
| Euro area rate | [`ECBDFR`](https://alfred.stlouisfed.org/series?seid=ECBDFR) | Daily ECB deposit-facility policy rate, percent. | It is an overnight policy rate, not a 2-year sovereign yield. Archived metadata on the page begins in 2021. |

These examples also expose a provenance problem for retroactive archives. ALFRED says it verifies vintages against the original source when possible, but may use third-party data services when sources did not retain old estimates. Its published population workflow describes loading pre-FRED archive files and adjusting archive dates to release dates. A vintage date can therefore be a reconstructed historical release date added later, rather than proof of contemporaneous capture. Keep the series-specific source/notes and coverage caveats with every value. [ALFRED help](https://alfred.stlouisfed.org/help) · [Populating an ALFRED-type Database](https://alfred.stlouisfed.org/docs/populating_alfred.pdf)

## API-key-free route: bounded status

ALFRED officially documents an interactive **Download Data** form on each series page. It supports selected/entered vintage dates and zipped Excel or zipped tab-delimited text; the archive includes a README with title, source, release, units, frequency, seasonal adjustment, notes, and the selected vintage dates. This is a genuine key-free first-party route suitable for a small manual evidence sample. [ALFRED Download Data help](https://alfred.stlouisfed.org/help/downloaddata)

ALFRED's live graph UI exposed a same-origin `alfredgraph.csv` download link, so this is first-party UI evidence rather than a route inferred from third-party code. A bounded [CPIAUCSL request for the 2020-01-01 vintage](https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=CPIAUCSL&vintage_date=2020-01-01&cosd=2019-01-01&coed=2020-01-01) returned the header `observation_date,CPIAUCSL_20200101`, 244 bytes, and SHA-256 `e9bff197d3e384c0406f5738e0b970409614ad39c96395846ef2d55ac2e520a1`. A bounded [DGS2 request as of 2020-01-02](https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=DGS2&vintage_date=2020-01-02&cosd=2019-12-20&coed=2020-01-02) returned `observation_date,DGS2_20200102`, 155 bytes, and SHA-256 `3a059c51b694e16adf020bc6b7880ff9e1740ee2a0ccb095e0fcdec0e7277e70`. The last included observation was 2019-12-31; the as-of date was not treated as an observation date.

That graph-CSV parameter contract is not described in the ALFRED Download Data help page, and its download control is rendered dynamically. Treat these two responses as reproducible first-party evidence, not as a stable documented API. The qualified key-free route is the visible **Download Data** form; production automation should use the documented keyed API or first capture the exact generated graph download link through the official UI and add a contract test. A `fred.stlouisfed.org/graph/fredgraph.csv` request with the same `vintage_date` parameter returned current values in this check, so it must not be used as an ALFRED substitute.

## Remaining boundaries before implementation

1. Capture one authorized JSON response for each output type 2, 3 and 4 and lock the exact row schema with fixtures.
2. Through the first-party ALFRED series UI, download one single-vintage sample for `CPIAUCSL` and `DGS2`; retain the archive, README, data header and SHA-256.
3. Build a series qualification table for each candidate country/leg. Reject candidates with insufficient vintage coverage or wrong instrument identity.
4. Add first-party source-release timestamps independently. ALFRED dates alone remain daily audit evidence.
5. Keep expectations/consensus from a separately licensed, point-in-time source. Actual minus later-added consensus would create look-ahead bias.

## Sources checked

All technical claims above use first-party Federal Reserve Bank of St. Louis documentation or ALFRED pages: [FRED API](https://fred.stlouisfed.org/docs/api/fred), [ALFRED definition](https://fred.stlouisfed.org/docs/api/fred/alfred.html), [FRED versus ALFRED](https://fred.stlouisfed.org/docs/api/fred/fred_vs_alfred.html), [real-time periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html), [series observations](https://fred.stlouisfed.org/docs/api/fred/series_observations.html), [series vintage dates](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html), [series metadata](https://fred.stlouisfed.org/docs/api/fred/series.html), [series release](https://fred.stlouisfed.org/docs/api/fred/series_release.html), [release dates](https://fred.stlouisfed.org/docs/api/fred/release_dates.html), [API keys](https://fred.stlouisfed.org/docs/api/api_key.html), [errors](https://fred.stlouisfed.org/docs/api/fred/errors.html), and [ALFRED Download Data help](https://alfred.stlouisfed.org/help/downloaddata).
