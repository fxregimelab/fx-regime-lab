# Fixed-UTC FX reference acquisition contract

Prepared 27 September 2026 for repair gate `leaf-13.1`. This report specifies how to acquire a new reference series from timestamped intraday observations. It does not qualify the existing daily Polygon/Massive, Alpha Vantage or Yahoo bars, and it does not establish that any provider value is final. No authenticated market request, credential, paid endpoint, database, deployment or installation was used.

## Decision

Build a separate series called `massive-fx-bbo-mid-utc-v1` from Massive historical quote events when the required entitlement is available. Each observation must contain both bid and ask plus the provider's nanosecond timestamp. Define the observation value as the midpoint, `(bid + ask) / 2`, and derive each daily bar over the half-open UTC interval `[00:00:00Z, 24:00:00Z)`. This makes the price rule and time boundary project-owned and reproducible.

Massive one-minute aggregates are a viable acquisition fallback, but they must form a different series, for example `massive-fx-minute-utc-v1`. Massive says those bars come from bid/ask quotes, but does not say whether OHLC uses bid, ask, midpoint or another rule. They cannot be represented as midpoint quotes or as executable prices. Alpha Vantage intraday OHLC has the same price-definition problem and weaker evidence about gaps and corrections. yfinance 1.3.0 does not expose the complete Yahoo chart response through its documented public history API, so it cannot meet the durable raw-response requirement without a separate, explicitly governed Yahoo client.

The derived series remains provisional until an authorized capture proves access, symbols, response shapes, coverage and an operational revision rule for all three locked pairs. A response fetched one day after its window, or two identical pulls, can support a project maturity rule. Neither proves provider finality.

## What Massive actually exposes

### Historical quotes: preferred input

Massive's [Forex Quotes endpoint](https://massive.com/docs/rest/forex/quotes/quotes) returns historical best bid and offer events. Each row can carry `bid_price`, `ask_price`, bid and ask exchange identifiers, and `participant_timestamp`, documented as an exchange-generated Unix timestamp in nanoseconds. The request can be ordered by `timestamp`. Its page size defaults to 1,000 and has a 50,000 maximum. A response may contain `next_url`; when present, that is the next page. The cursor is opaque and must be followed rather than reconstructed.

The official Python client documents automatic pagination for `list_quotes`, with `limit` acting as the page size when pagination is enabled. It also documents `.gt`, `.gte`, `.lt` and `.lte` filter operators. The acquisition request should use `timestamp.gte = window_start_ns`, `timestamp.lt = window_end_ns`, `sort=timestamp`, `order=asc`, and `limit=50000`. Following an exclusive upper bound prevents an event at exactly midnight from entering both days. See the [official client pagination and filter documentation](https://github.com/massive-com/client-python#pagination-behavior).

Use endpoint-specific symbols. Massive's Custom Bars example uses `C:EURUSD`, while the Quotes example uses `C:EUR-USD`. The quote symbols for EUR/USD, USD/JPY and USD/INR must be confirmed by an authorized metadata lookup or quote capture. Do not generate the quote symbol by reusing the current aggregate ticker function.

Historical Quotes are not included in the current Currencies Basic plan shown on the endpoint page. The page describes them as available on selected plans, with Currencies Starter providing real-time recency and history back to 25 September 2009. Current entitlement, rate limits, permitted storage and redistribution must be recorded from the actual account contract; a successful response must not be used to infer them.

### Minute aggregates: lower-cost fallback with a narrower claim

Massive's [Forex Custom Bars endpoint](https://massive.com/docs/rest/forex/aggregates/custom-bars) supports one-minute OHLC and states that FX aggregates are generated from quoted bid/ask prices rather than trades. It emits no bar when no new quote occurs in an interval. `t` is the aggregate-window start in Unix milliseconds. `sort=asc|desc` is explicit. `limit` defaults to 5,000 and has a 50,000 maximum, but it limits the number of base aggregates queried, not necessarily the number of returned bars.

The endpoint's current response schema does not document `next_url`. The defensible retrieval pattern is explicit bounded requests. One UTC day of minute slots has only 1,440 possible starts, so request one day at a time with millisecond `from` and `to`, `timespan=minute`, `multiplier=1`, `sort=asc` and `limit=50000`, then apply the project-owned half-open UTC membership check to every returned `t`. This avoids relying on date strings described as Eastern Time and avoids hidden truncation across long ranges. Massive's [aggregate API note](https://www.massive.com/blog/aggs-api-updates) explains that the limit is measured in base bars and that a roll-up made partial by the limit is omitted; “full bar” there does not mean immune from a later correction.

The Custom Bars page describes aggregate `v` as trading volume and `n` as transactions even though the same page says FX bars are quote-derived. Massive separately explains that FX has no consolidated tape and its [currency data comes from institutional-bank quotes](https://massive.com/knowledge-base/article/where-does-massives-currencies-data-come-from). Treat `v`, `n` and `vw` as provider fields with unresolved FX semantics. They are not executed volume and must not become the canonical series' market-volume evidence.

Massive also offers [daily flat files of minute aggregates](https://massive.com/docs/flat-files/forex/minute-aggregates), described as available at 11:00 ET for the previous day on an eligible plan. This is a useful independent delivery channel to compare against REST, but publication timing is not a correction deadline or finality guarantee.

### Gaps, corrections and completion

Massive documents that a missing minute aggregate means no new quote occurred in that interval. That interpretation applies only after the client has proved that it retrieved the complete requested response. A timestamp absent from a truncated, failed or otherwise incomplete acquisition is only a client-observed gap; it cannot be labeled “no new quote.” Neither kind of gap is a zero-price bar, and neither may be forward-filled silently. Historical quote events likewise record updates, not guaranteed evenly spaced samples. A constructed daily bar is therefore an **event-time midpoint bar**: open is the first valid midpoint event in the UTC window, high and low are extrema across valid events, and close is the last valid midpoint event. It is not a simultaneous executable close at midnight.

Record `first_event_offset_ms` and `last_event_age_ms` for each window. Pair-specific maximum boundary ages may be frozen only after observing normal coverage across weekdays, weekends, holidays and daylight-saving changes. Until those limits exist and pass, the daily result remains ineligible. A window with no event produces no daily bar. Weekend or market-closure classification must be explicit; absence alone cannot distinguish a normal closure from failed acquisition.

The public Massive material reviewed here exposes no `is_final` field, correction cutoff or immutable-completion SLA for FX quotes or minute aggregates. Massive's [data-discrepancy guidance](https://massive.com/knowledge-base/article/how-should-i-go-about-reporting-a-possible-massive-data-discrepancy) says a stored live bar can be superseded and that REST holds the current corrected version. It asks users to preserve `request_id` or `x-request-id` and to check whether the same request still returns the same value. The project must therefore append new versions and never overwrite an earlier response or derived bar.

Use two separate states:

- `provider_finality`: always `unknown` unless Massive publishes and the project captures a specific finality contract.
- `project_maturity`: `provisional`, `accepted_as_of` or `superseded`. This status is derived from append-only acceptance events; it is not an update to an older observation or derived-bar record. An acceptance event must record `acceptance_as_of_utc`, `acceptance_rule_version` and the exact accepted input hash. Acceptance means only that the frozen project rule passed on the evidence available at that time.

No one-day lag or equality check changes `provider_finality` from `unknown`. A candidate operational rule should capture once after the UTC window ends, repeat after a frozen interval, append both response versions, and append an acceptance event only if the derived-value hash and acquisition checks agree. The interval and any later audit pull, such as seven days later, remain proposed parameters until live capture evidence supports them.

## Daily construction rule

For `massive-fx-bbo-mid-utc-v1`:

1. Convert `participant_timestamp` from integer nanoseconds to an aware UTC instant without passing through local time.
2. Accept a row only when bid and ask are finite and positive, `bid <= ask`, and its timestamp satisfies `window_start <= t < window_end`.
3. Preserve every returned occurrence with its acquisition-snapshot ID, page ID, page ordinal and row hash. The public schema exposes no event ID or sequence, and Massive's own sample contains distinct prices at the same `participant_timestamp`. Never infer that one quote supersedes another from timestamp, timestamp plus exchange, or page order. Identical occurrences may be collapsed only inside the versioned OHLC calculation where multiplicity cannot change the result; the evidence remains occurrence-complete.
4. Sort by provider timestamp for calculation only. If distinct prices share the earliest or latest timestamp, mark open or close ambiguous; page order is not a documented sequence and must not break the tie. High and low remain order-independent. Across two captures, describe row-level differences as multiset additions/removals. Do not claim event-level correction or supersession when the provider supplies no stable identity for that match.
5. Compute midpoint per accepted row, then `open=first`, `high=max`, `low=min`, `close=last`. Do not mix bid, ask or aggregate OHLC into this series.
6. Record source-occurrence count, distinct canonical-row count, unique-timestamp count, duplicate count, crossed/invalid count, first and last event time, boundary ages, page count and any observed timestamp gaps. Do not impute a price for a missing interval.
7. Hash the ordered input row hashes plus the algorithm/version manifest. The derived record points to every input response manifest and the prior derived version, if any.

For `massive-fx-minute-utc-v1`, use the same UTC membership and version rules, with open from the first minute bar, high as the maximum minute high, low as the minimum minute low and close from the last minute bar. Preserve the provider OHLC fields verbatim. Label its price basis `provider_quote_aggregate_unspecified`; never call it midpoint.

## Durable evidence contract

The evidence store needs append-only page manifests, acquisition snapshots with source occurrences, derived bar versions, and separate acceptance events.

### 1. Request and response page manifest

| Group | Required fields |
|---|---|
| Identity | `acquisition_run_id`, `provider`, endpoint path, endpoint-specific instrument, pair, series ID and version, client name/version, code revision |
| Request | UTC window start/end, literal nonsecret path and query parameters, page number, prior-page link, requested/received times |
| Access | configured entitlement name and observed HTTP outcome kept separate; applicable terms/contract version when known |
| Response | HTTP status, provider status, body `request_id`, allowlisted `x-request-id`, content type, byte length, result count, first/last raw timestamp |
| Pagination | sanitized `next_url`, opaque cursor hash, termination reason, total page and row counts after traversal |
| Integrity | SHA-256 of original response bytes, SHA-256 and durable pointer for the sanitized retained body, sanitizer version |
| Qualification | schema check result, count/order/range errors, throttle/access error, retrieval completion status |

Store request parameters as a structured allowlist. Never store `apiKey`, `Authorization`, cookies, session tokens, environment values or a URL containing them. Retain only allowlisted response headers. Sanitize `next_url` defensively even when a sample omits the API key. Hash the original bytes before sanitizing; retain the original body only when a reviewed storage policy establishes that the body contains no secret. The sanitized payload must still contain all provider observations and response identity fields.

Every quote page must be archived before following its `next_url`. A failed later page leaves a visible incomplete acquisition run; it must not publish a daily bar from the prefix already downloaded.

### 2. Acquisition snapshot and source occurrences

Append one immutable acquisition snapshot per complete or failed retrieval attempt. Preserve every response occurrence with raw timestamp integer and unit, decoded UTC instant, bid, ask and exchange IDs for quotes, or raw OHLC/`v`/`vw`/`n` for minute aggregates. Include snapshot ID, response-page ID, ordinal within the page and canonical row hash.

`first_seen_at` and `last_seen_at` are query results for an exact canonical row signature, derived from the append-only occurrence history; they are not fields updated on an old row and do not identify a provider event. Because the quote schema has no unique event ID or sequence, timestamp or timestamp-plus-exchange is not a safe provider observation key. Reconciliation may state that complete snapshot hashes differ and show deterministic multiset additions/removals. It must mark event-level lineage `ambiguous` when no stable provider identity proves which occurrence was corrected or replaced.

### 3. Derived UTC bar version

Store pair, series ID/version, `[window_start, window_end)`, OHLC, price rule, algorithm version, input-manifest IDs and aggregate input hash. Add the coverage and timestamp-tie counters, `provider_finality`, exclusion reasons, derived time and prior-derived-version link. A later source difference appends a new derived version and snapshot-level reconciliation; it never edits the earlier evidence or immutable scoring ledger.

Record project acceptance in a separate append-only event containing derived-bar version, `project_maturity`, `acceptance_as_of_utc`, `acceptance_rule_version`, accepted input hash and `validation_eligible`. A later acceptance, withdrawal or supersession appends another event. A consumer derives current status from that event stream and must select the latest accepted version available **as of the evaluation cutoff**, rather than the newest value visible today.

## Other provider boundaries

### yfinance 1.3.0

The installed package is 1.3.0. Its documented `download()` and `Ticker.history()` paths return pandas DataFrames. In the [1.3.0 history implementation](https://github.com/ranaroussi/yfinance/blob/1.3.0/yfinance/scrapers/history.py#L183-L315), the Yahoo `/v8/finance/chart/{ticker}` response is parsed into a local dictionary, only the response `meta` object is retained as history metadata, quote arrays are transformed, and the public history call ultimately returns a DataFrame. `get_history_metadata()` returns that metadata dictionary, not the complete chart envelope.

For day-level `download`, [1.3.0 defaults `ignore_tz=True`](https://github.com/ranaroussi/yfinance/blob/1.3.0/yfinance/multi.py#L200-L230) and later removes the timezone from each returned frame. The repository's current call does not specify `interval`, so it requests the `1d` default and receives the transformed frame only. A custom session does not provide a documented response hook. Accessing `_data` would depend on private internals; it is not a supported raw-response contract.

Consequently, yfinance may remain a visibly separate provisional convenience source, but its public API cannot satisfy the full-response evidence contract. If Yahoo is selected later, use a separately reviewed direct chart client, archive its request and raw sanitized response, and treat that as a new source adapter rather than implying yfinance supplied the envelope. Yahoo's source, correction and finality policies would still be unresolved.

### Alpha Vantage

Alpha Vantage's [FX_INTRADAY documentation](https://www.alphavantage.co/documentation/#fx-intraday) describes timestamped OHLC at 1, 5, 15, 30 or 60-minute intervals, updated in real time. `compact` returns the latest 100 points and `full` returns the full intraday series. The endpoint is marked premium. It does not document bid/ask, volume, quote contributors, missing-interval meaning, a completion flag or a correction deadline.

If used, it must have its own `alphavantage-fx-intraday-utc-v1` series and raw response manifest. `outputsize=full` must be explicit for complete-window acquisition; a 1-minute day cannot fit in `compact`. Its timestamp timezone must come from the captured response metadata and be converted with that named timezone, not assumed. It is not a fallback page for a partially acquired Massive series.

## Current adapter pitfalls

`pipeline/src/fetchers/fx_spot.py` cannot be extended by treating its current output as the new reference:

- Polygon/Massive requests `/range/1/day`, includes the current date and sends neither explicit `sort` nor `limit`. It never acquires timestamped intraday observations.
- `_polygon_ticker()` creates aggregate symbols such as `C:EURUSD`; the historical Quotes endpoint documents a hyphenated form such as `C:EUR-USD`.
- The parser keeps selected top-level fields but drops `queryCount`, `resultsCount`, `n`, `vw`, response headers, the request manifest, the full body and its hash. One response's metadata is copied into each transformed `SpotBar`.
- `v` is currently assigned as spot volume even though executed FX volume is not established by the provider contract.
- The Alpha Vantage path requests `FX_DAILY outputsize=compact`, not `FX_INTRADAY`, and keeps only selected metadata.
- The Yahoo path calls `download(..., auto_adjust=True)` with the day-level default, receives a transformed DataFrame and never obtains the raw Yahoo response or history metadata. For day-level downloads yfinance removes the timezone by default.
- The fallback chain substitutes whole daily provider series. Partial pages, missing intervals or a failed correction pull must instead fail the chosen reference-series run; another provider cannot fill holes under the same series ID.

These are acquisition-contract gaps, not evidence that the current adapters returned wrong numbers.

## Falsifiable acceptance scenarios

| Scenario | Required result |
|---|---|
| UTC boundary | Events at `23:59:59.999999999Z` and `00:00:00Z` enter different half-open windows on every host timezone. |
| Quote pagination | A fixture with two `next_url` pages archives both manifests and all rows in order. A missing, repeated or failing second page makes the run incomplete and publishes no bar. |
| Secret removal | Fixtures place a key in the initial URL, headers and `next_url`; none appears in retained manifests or payloads. Original and sanitized hashes remain distinct and reproducible. |
| Aggregate limit | A one-day minute request uses explicit epoch bounds, `sort=asc`, `limit=50000`; every `t` is in range. A response outside the range or with inconsistent counts fails qualification. |
| Missing minute | In a proved-complete provider response, removing a minute aggregate records a provider-documented no-new-quote interval and creates no zero or forward-filled row. The same absence in an incomplete client run is labeled acquisition gap, not no-new-quote. |
| Empty window | An empty response creates an archived acquisition outcome and no price bar. Weekend status or acquisition failure remains explicit rather than inferred from emptiness. |
| Midpoint rule | For bid 1.1000 and ask 1.1002, the stored reference value is 1.1001. A missing side, nonpositive price or crossed quote is rejected and counted. |
| Timestamp tie | Two distinct midpoints at the earliest or latest identical nanosecond timestamp make open or close ambiguous and `validation_eligible=false`. Page order does not decide the price. |
| Duplicate page row | An identical row repeated across page boundaries preserves both occurrences and page ordinals. A versioned OHLC calculation may collapse identical values, but it does not claim they are the same provider event. |
| Same timestamp, different quote | Two prices with the same `participant_timestamp`, including the same exchange IDs, remain separate occurrences. No supersession is inferred; a boundary tie makes open or close ambiguous. |
| Later snapshot differs | The old snapshot, occurrences and derived bar remain. The new snapshot and bar are appended. Reconciliation reports snapshot hashes and multiset additions/removals; event-level lineage is marked ambiguous unless a stable provider ID exists. |
| Append-only acceptance | Accepting, withdrawing or superseding a derived bar appends an acceptance event. Earlier observations, first/last-seen evidence and acceptance records are byte-identical afterward. |
| False finality guard | A pull one day after the window and an identical repeat may satisfy the frozen project rule and record its exact `acceptance_as_of_utc`, but `provider_finality` remains `unknown`. A later change supersedes the maturity result without rewriting history or changing what was accepted at the earlier cutoff. |
| Pair coverage | Authorized captures confirm endpoint-specific symbols and nonempty normal-session coverage separately for EUR/USD, USD/JPY and USD/INR. Success for one pair cannot qualify the other two. |
| Entitlement or throttle | HTTP 401/403/429 or a provider error body creates a failed manifest and no bar. The system does not silently continue the same series through Alpha Vantage or Yahoo. |
| yfinance envelope | A DataFrame plus `history_metadata` without the complete chart response fails the raw-response acceptance check. Private `_data` access is also rejected as an unsupported contract. |
| Alpha Vantage compact | A `compact` 1-minute response cannot qualify a full UTC day. A full response still remains provisional until timezone, coverage and revision checks pass. |

## Evidence still required

- Authorized, non-production capture for all three endpoint-specific Massive quote symbols, including response schema, page behavior, timestamps, plan/rate-limit headers and coverage. USD/INR availability must not be inferred from EUR/USD.
- Account terms that permit durable storage and the intended public research use. Public plan labels are not the account contract.
- Empirical coverage profiles by pair across ordinary weekdays, weekend transitions, holidays and daylight-saving changes, followed by frozen boundary-age and missing-data rules.
- Repeat pulls and later audit pulls to measure observed corrections. They can justify a project maturity interval, not provider finality.
- Verification of whether raw quote pages ever return sensitive response content before original bodies are retained.
- An actual PostgreSQL archive/replay test, integration with the immutable evaluation versions, and record-by-record reconciliation. None is established by this research.

The GitNexus query for the current acquisition flow could not run because the local index database was created by a newer storage version than the available reader. The relevant adapter was inspected directly instead; no index rebuild was attempted because this packet owns only the report.
