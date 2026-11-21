# FX daily price-provider timing research

Prepared 27 September 2026 for repair gate `leaf-12.1`. This is a source contract for `pipeline/src/fetchers/fx_spot.py`, not proof that any currently returned bar is complete. No provider API key was used and no live market-data request was made.

## Decision

The three fallback feeds cannot be treated as one UTC daily-close series. They may all be represented with UTC retrieval timestamps, but the evidence does not establish a common observation window, cutoff, or finality rule.

The safe design is to archive each response as a **provider-session observation** and make it ineligible for validation until a provider-specific window and maturity rule are proved. A separate canonical UTC series is possible only if the project deliberately builds fixed UTC windows from timestamped intraday quotes. That would be a new derived series, not a relabeling of these daily bars.

| Provider path | What is established | What remains unknown | Safe status for the newest row |
|---|---|---|---|
| Massive/Polygon `/v2/aggs/.../range/1/day` | Quote-derived OHLC; epoch `t` is the aggregate-window start; response has request metadata; access may be end-of-day or real-time | FX daily window boundary is internally ambiguous in the published material; no completion flag or revision cutoff | `unknown` or `provisional`; archive, do not score |
| Alpha Vantage `FX_DAILY` | Date-keyed OHLC, `compact` is the latest 100 observations, endpoint is “updated realtime” | Daily cutoff/session, exact latest-row partial rule, contributor source, delay, correction and finality policy | `provisional` by conservative inference; archive, do not score |
| Yahoo through yfinance `download(..., period=..., auto_adjust=True)` | Yahoo chart timestamps are localized to Yahoo's `exchangeTimezoneName`; day-level `download` then removes the timezone by default | FX ticker session/cutoff, Yahoo source contributors, delay, correction and finality policy | `provisional`; yfinance source explicitly handles a live current-day row |

## Massive / Polygon

### What the provider documents

The [Forex Custom Bars documentation](https://massive.com/docs/rest/forex/aggregates/custom-bars) says the endpoint returns OHLC aggregates over a requested interval in Eastern Time. Forex bars are built from quoted bid/ask prices, not executions, and an interval with no new quote produces no bar. It defines `results[].t` as the Unix-millisecond timestamp for the **start** of the aggregate window. It also lists plan recency as either end-of-day or real-time, so endpoint shape alone does not reveal freshness.

Massive says its forex quotes come from institutional bank feeds, that there is no central FX tape, and that different providers may legitimately show different rates because they aggregate different contributors. It also states that aggregate `volume` is not trade volume. The ticker metadata identifies `market: fx`, base currency and quote currency, but no per-ticker `source_feed`. See [Where does Massive's currencies data come from?](https://massive.com/knowledge-base/article/where-does-massives-currencies-data-come-from).

Massive's [timestamp guidance](https://massive.com/knowledge-base/article/what-timezone-are-massives-timestamps-in) describes its Unix epoch timestamps as UTC instants. That answers how to decode `t`; it does not, by itself, define the economic window that the instant starts.

The [FX market-hours article](https://massive.com/knowledge-base/article/what-are-the-forex-market-hours) says FX runs continuously from Sunday evening to Friday evening Eastern and expressly says there is no daily open or close. The named Sydney, Tokyo, London and New York sessions are activity conventions, not enforced market boundaries. A 17:00 New York cutoff must therefore not be inferred from market hours.

### Published inconsistency that prevents a stronger contract

The Custom Bars page says the intervals are in ET, but its own `C:EURUSD` example gives `t = 1626912000000`. That instant is `2021-07-22T00:00:00Z`, or `2021-07-21T20:00:00-04:00`, not Eastern midnight. The [single-ticker FX snapshot documentation](https://massive.com/docs/rest/forex/snapshots/single-ticker-snapshot) separately says snapshot state is cleared at `12:00 AM EST` and then updates in real time; that is a snapshot lifecycle statement, not evidence that Custom Bars uses the same boundary. The example and prose do not support choosing ET midnight, UTC midnight, or 17:00 New York as the historical FX daily cutoff.

Consequently, preserve `t` as an aware UTC instant and preserve the request's literal `from`, `to`, `timespan` and `multiplier`. Do not derive the provider's session date from host-local time, and do not overwrite the raw instant with an assumed ET label.

### Completion, delay and revision

Custom Bars exposes no `is_final` or `complete` field. Real-time entitlement means a request can cover the current aggregate window. The snapshot page confirms that a current `day` object updates as new information arrives. These facts are enough to reject “returned means complete”; they do not establish the exact Custom Bars completion time.

Massive also warns that a stored live bar can later be superseded and that a fresh REST pull holds the current corrected version. Its discrepancy procedure asks whether the same request still returns the same value and asks users to retain `request_id` or the `x-request-id` header. See [How to report a data discrepancy](https://massive.com/knowledge-base/article/how-should-i-go-about-reporting-a-possible-massive-data-discrepancy). No provider-wide revision deadline is stated there, so elapsed window end alone would still need a project-owned correction grace or a stability re-pull.

Archive at least: provider name, endpoint, ticker, request parameters, `retrieved_at_utc`, raw `t`, decoded UTC instant, OHLC, `v`, `vw`, `n`, response `ticker`, `adjusted`, `status`, `queryCount`, `resultsCount`, body `request_id`, response `x-request-id`, known plan/recency if configured, raw-payload hash and payload location. Do not record a guessed `session_date` as fact.

## Alpha Vantage `FX_DAILY`

The current [Alpha Vantage API documentation](https://www.alphavantage.co/documentation/#fx-daily) says `FX_DAILY` returns date/timestamp plus open, high, low and close and is **updated realtime**. `outputsize=compact` returns the latest 100 daily points. The same official page explicitly calls the latest weekly and monthly rows partial, but it does not publish the equivalent daily cutoff, session timezone, contributor source, delay, completion flag, or correction policy. Alpha Vantage's [official MCP implementation](https://github.com/alphavantage/alpha_vantage_mcp/blob/95eeb1d51f0a0a185c6f26ecaae6edec2f33d934/api/src/av_api/tools/forex.py) repeats “updated realtime” and provides no extra timing contract.

“Updated realtime” makes it unsafe to assume the newest date-keyed row is fixed. Calling it partial is a conservative inference, not a quoted provider guarantee. The exact moment it becomes complete is unknown. A returned timezone or “last refreshed” value, if present in JSON metadata, would describe the response's clock; it still would not prove a daily cutoff or finality unless Alpha Vantage documents that link.

The repository parser currently reads only `Time Series FX (Daily)` and discards every other top-level field. The archive should therefore preserve the complete top-level response or, at minimum, every metadata key verbatim, including information, pair legs, output size, last-refreshed value and timezone when supplied. It should add `retrieved_at_utc`, request parameters, response hash, first-seen and last-seen times, and a value hash for each date. Provider source, session start/end, delay and revision SLA must remain `unknown` rather than being filled from convention.

For eligibility, the newest Alpha Vantage date stays out of validation. Older dates can move beyond `provisional` only after the project adopts one of these evidence-backed controls: Alpha Vantage publishes a daily boundary/finality contract; an authorized empirical capture proves the boundary across DST and weekends and a documented grace is applied; or repeated pulls show a chosen stability interval, with later changes versioned rather than overwritten. Repeated equality is an operational safeguard, not proof that the vendor will never revise the row.

## Yahoo Finance through yfinance

The installed package is yfinance `1.3.0`. The project calls `download` with a relative `period`, `auto_adjust=True` and no explicit `interval`, so yfinance uses its `1d` default. The [1.3.0 `download` source](https://github.com/ranaroussi/yfinance/blob/1.3.0/yfinance/multi.py#L40-L94) documents that day-level downloads default `ignore_tz=True`. The implementation removes the timezone from each returned frame before concatenation.

Underneath, yfinance calls Yahoo's chart endpoint. The [1.3.0 history implementation](https://github.com/ranaroussi/yfinance/blob/1.3.0/yfinance/scrapers/history.py#L294-L314) reads `exchangeTimezoneName` from Yahoo metadata, parses the chart timestamps, and notes that Yahoo can append the latest price. For non-intraday data it rebuilds each index at midnight in that exchange timezone before `download` later strips the timezone ([same source](https://github.com/ranaroussi/yfinance/blob/1.3.0/yfinance/scrapers/history.py#L409-L418)). The [yfinance utility code](https://github.com/ranaroussi/yfinance/blob/1.3.0/yfinance/utils.py#L640-L665) explicitly handles the case where the market is open and Yahoo returns today's/live data, including duplicate daily rows. This proves the newest row is not inherently final.

No live query was made, so this report does not assert which `exchangeTimezoneName` Yahoo currently assigns to `EURUSD=X`, `JPY=X` or `INR=X`. A named timezone, even when captured, would establish how yfinance labels the date; it would not by itself establish the FX session's start, end or close convention.

`download` returns a DataFrame, not the raw chart response, and the project then takes `idx.date()`. The current path therefore discards Yahoo's raw epoch timestamps, `exchangeTimezoneName`, `regularMarketTime`, current trading-period metadata, chart interval, retrieval time and any provider freshness fields. It also requests `auto_adjust=True` and leaves `repair=False`; neither setting supplies a completion or revision guarantee.

yfinance itself states that it is an open-source client, is not affiliated with or vetted by Yahoo, uses Yahoo's public APIs, and is intended for research and educational use; it directs users to Yahoo's terms and says the API is for personal use. See the [project README](https://github.com/ranaroussi/yfinance#readme). This is relevant to source governance and licensing, independent of timing correctness.

The safer integration would use a single-ticker history call that exposes history metadata, record the installed yfinance version, capture the ticker, interval, raw localized index, timezone, metadata, request/retrieval times and response/value hashes, and then archive the latest row as provisional. The raw Yahoo response should be retained when permitted. No row should become validation-eligible merely because yfinance returned a timezone-naive `Date` index.

## Repository gap

`SpotBar` currently carries only `date`, pair, OHLC and volume. All three parsers collapse their upstream evidence into that shape:

- Massive uses `date.fromtimestamp(t / 1000)`, which depends on the machine's local timezone, then drops `t`, response IDs, status and entitlement context.
- Alpha Vantage parses the first ten characters of each date key and drops top-level metadata.
- yfinance takes `idx.date()` after day-level `download` has defaulted to timezone removal; it drops the exchange timezone and Yahoo metadata.
- None of the paths records retrieval time, source version, window bounds, partial/final status, revision history or a raw-response hash. All request windows can include the current date/current daily row.

The result is suitable as an in-memory numerical observation but cannot establish a completed bar for an immutable validation record.

## Safe archive and projection contract

The archive should be append-only at the observation/version level. A practical record needs these fields:

| Field group | Required values |
|---|---|
| Identity | `provider`, endpoint, pair, provider symbol, provider observation key, schema/client version |
| Request | literal parameters, requested start/end, entitlement or plan recency when known |
| Time | `retrieved_at_utc`, raw timestamp/date key, decoded UTC instant when available, provider timezone when supplied, asserted window start/end only with a cited rule |
| Values | raw OHLC and provider volume/count/VWAP fields, raw row hash |
| Response evidence | status, request IDs, last-refreshed metadata, full-response hash and durable payload pointer |
| Revision chain | `first_seen_at`, `last_seen_at`, observation version, prior value hash/supersedes link |
| Qualification | `completion_status = unknown | provisional | mature`, rule version, rule evidence, `validation_eligible`, exclusion reason |

The ingestion step may archive unknown or partial observations. The validation projection must fail closed:

1. Reject any observation whose raw window start is at or after retrieval time. If the source supplies only a date key and no verified boundary, do not manufacture a window start.
2. Exclude the newest provider row while its boundary is unknown. A date later than the retrieval date in the provider's documented timezone is an additional hard rejection, but the absence of such a future date does not prove completion.
3. Require a provider-specific rule with cited session/window bounds, a post-window grace, and a revision policy before setting `validation_eligible=true`.
4. Re-fetch mature candidates and append a new version if the value changes. Never edit the prior observation or the immutable scoring ledger.
5. Keep source-session series separate. Do not fill a missing Massive row with an Alpha Vantage or Yahoo row under the same canonical-close label.

Two implementation choices are defensible:

- **Provider observation archive:** keep all three feeds as distinct source/session series. Choose one provider-specific mature series for scoring only after its boundary contract is established; fallbacks may preserve continuity but remain visibly different sources.
- **Canonical UTC bar:** aggregate timestamped intraday quotes into fixed `[00:00Z, 24:00Z)` windows, record the quote source and construction rule, wait through a defined correction grace, and version late changes. This yields uniform UTC windows by construction, but it is a new project-derived bar and will not necessarily equal any provider's daily OHLC.

Using a provider timezone name, a date label, the word “daily,” or a successful HTTP response as evidence of cutoff or finality is not defensible on the sources above.

## Evidence limits

- No authenticated response was fetched, so current entitlements, current ticker metadata and response fields were not observed.
- Massive's public Custom Bars prose and sample disagree on the apparent FX day anchor. The raw timestamp is reliable evidence; a session label is not resolved.
- Alpha Vantage publishes no daily session boundary or revision SLA in the reviewed official material.
- Yahoo does not publish a stable FX daily-bar contract through yfinance. The yfinance source explains its transformation, not Yahoo's contributor or finality policy.
- Provider documentation can change. Store the cited contract version or retrieval date beside any implemented eligibility rule.

No Docker or Hermes gateway component was needed for this read-only source investigation, and none was started.
