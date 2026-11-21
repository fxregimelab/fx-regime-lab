# Private release-source research: BLS CPI and FOMC statements

**Scope.** Read-only source review for the private FX desk. This report establishes what the named first-party pages state. It does not establish when a vendor, browser, data feed, ALFRED, or the desk actually received the information. It makes no claim about forecast quality, strategy improvement, or trading profitability.

## Decision

The three BLS archive pages state an exact embargo clock and exact headline CPI percentage changes. They do **not** state the seasonally adjusted CPI-U index level needed to identify `CPIAUCSL=300.536` or its later `300.356` revision. The archive instead gives rounded one-decimal percentage changes and an exact **unadjusted** CPI-U index level. A parser may use the archived release for a source-stated event clock and headline percentage identity, but it must use a separate, versioned vintage source for the seasonally adjusted index level.

The Federal Reserve FOMC statement pages are a stronger machine-capture source in this environment: bounded direct requests returned the original official HTML with HTTP 200. Each page states its own release clock, including `EST` or `EDT`, and the decided target range. That proves the source-stated clock and announced range. It does not prove actual network transmission time, receipt time, the effective federal funds rate, a two-year market yield, or the market's prior expectation.

## BLS CPI archive findings

| Observation covered | Official archived release | Source-stated embargo | Headline all-items CPI-U | Exact level actually present |
|---|---|---|---|---|
| January 2023 | [HTML](https://www.bls.gov/news.release/archives/cpi_02142023.htm) · [PDF](https://www.bls.gov/news.release/archives/cpi_02142023.pdf) | `8:30 a.m. (ET) Tuesday, February 14, 2023`; release ID `USDL-23-0277` | `+0.5 percent` from December, **seasonally adjusted**; `+6.4 percent` over 12 months, **before seasonal adjustment** | `299.170`, CPI-U, **not seasonally adjusted**, base `1982-84=100` |
| March 2023 (daylight-saving sample) | [HTML](https://www.bls.gov/news.release/archives/cpi_04122023.htm) · [PDF](https://www.bls.gov/news.release/archives/cpi_04122023.pdf) | `8:30 a.m. (ET) Wednesday, April 12, 2023`; release ID `USDL-23-0674` | `+0.1 percent` from February, **seasonally adjusted**; `+5.0 percent` over 12 months, **before seasonal adjustment** | `301.836`, CPI-U, **not seasonally adjusted**, base `1982-84=100` |
| January 2024 | [HTML](https://www.bls.gov/news.release/archives/cpi_02132024.htm) · [PDF](https://www.bls.gov/news.release/archives/cpi_02132024.pdf) | `8:30 a.m. (ET) Tuesday, February 13, 2024`; release ID `USDL-24-0265` | `+0.3 percent` from December, **seasonally adjusted**; `+3.1 percent` over 12 months, **before seasonal adjustment** | `308.417`, CPI-U, **not seasonally adjusted**, base `1982-84=100` |

The first paragraphs and Table A make the units and periods unambiguous: the monthly number is a percent change from the preceding month on a seasonally adjusted basis; the 12-month number is the all-items percent change for the 12 months ending in the named observation month before seasonal adjustment. The exact source wording and tables are on the [January 2023 archive](https://www.bls.gov/news.release/archives/cpi_02142023.htm), [March 2023 archive](https://www.bls.gov/news.release/archives/cpi_04122023.htm), and [January 2024 archive](https://www.bls.gov/news.release/archives/cpi_02132024.htm).

### The `300.536` / `300.356` identity question

The January 2023 archived HTML contains neither `300.536` nor `300.356`. Its table publishes unadjusted index levels and seasonally adjusted percentage changes; its exact all-items index level is the unadjusted `299.170`. The [ALFRED release-date page for 14 February 2023](https://alfred.stlouisfed.org/release?ob=pv&od=desc&rd=2023-02-14&rid=10&t=all+items) separately identifies `CPIAUCSL`, monthly and seasonally adjusted, as `300.536` for January 2023. A later BLS first-party table in the [January 2024 Real Earnings release](https://www.bls.gov/news.release/archives/realer_02132024.htm) shows the seasonally adjusted January 2023 CPI-U level as `300.356`. Those are different vintage identities; neither value may be extracted from the February 2023 CPI archive itself.

This difference is expected under BLS's stated revision policy. BLS says seasonally adjusted data, including the U.S. city average all-items index, are revised annually for up to five years. The current [seasonal-adjustment page](https://www.bls.gov/cpi/seasonal-adjustment/) and [guidance on adjusted versus unadjusted data](https://www.bls.gov/cpi/seasonal-adjustment/using-seasonally-adjusted-data.htm) describe that policy. The archived January 2023 release itself also says that February's annual recalculation revises the previous five years of seasonally adjusted indexes. Therefore:

- retain `release_value`, `release_date`, `source_url`, and `source_retrieved_at` separately from any later revised value;
- do not overwrite the release vintage with `300.356` or with the current series value;
- do not infer an ALFRED ingestion timestamp from the BLS embargo line or from ALFRED's release-date label.

### Archive, schedule, and retrieval limits

BLS maintains a first-party [CPI archived-news-release index](https://www.bls.gov/bls/news-release/cpi.htm) linking archive copies. That supports treating these as official archive routes. It is evidence of present archival availability, not a legal or technical guarantee of permanent future hosting.

The future schedule shown at the foot of an archived release is part of that historical document: January 2023 pointed to 14 March 2023, March 2023 pointed to 10 May 2023, and January 2024 pointed to 12 March 2024, all at 8:30 a.m. ET. A current schedule must instead come from BLS's live [CPI release schedule](https://www.bls.gov/schedule/news_release/cpi.htm). Never use a historical release's next-release sentence as the current calendar.

Retrieval observations on 1 October 2026:

- bounded direct requests from this host to all three BLS archive HTML, `.txt`, and `.pdf` variants returned HTTP 403 and the same 1,323-byte BLS access-denied HTML body;
- Agent Reach search and the web reader could resolve the official HTML/PDF contents, and a hidden in-app browser opened the official January 2023 PDF URL, but this is not evidence that the desk captured an original HTTP 200 response;
- the `.txt` variants were guessed alternate routes and were not accepted: they returned the denial body and were not independently indexed as working release artifacts;
- HTML and PDF are the official alternate routes supported by the archive/search evidence. For production capture, fail closed unless the response itself is HTTP 200, has the expected media type, and passes the content-identity checks below.

## Federal Reserve FOMC findings

Direct retrieval of all six official statement and implementation-note pages below returned HTTP 200 from this host.

| Decision date | Official statement | Source-stated release clock | Announced target range | Effective implementation |
|---|---|---|---|---|
| 1 February 2023 | [Statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230201a.htm) | `For release at 2:00 p.m. EST` | `4-1/2 to 4-3/4 percent` | [Implementation note](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230201a1.htm): effective 2 February 2023; IORB 4.65%; Desk directed to maintain the same target range |
| 22 March 2023 | [Statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230322a.htm) | `For release at 2:00 p.m. EDT` | `4-3/4 to 5 percent` | [Implementation note](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230322a1.htm): effective 23 March 2023; IORB 4.90%; Desk directed to maintain the same target range |
| 26 July 2023 | [Statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230726a.htm) | `For release at 2:00 p.m. EDT` | `5-1/4 to 5-1/2 percent` | [Implementation note](https://www.federalreserve.gov/newsevents/pressreleases/monetary20230726a1.htm): effective 27 July 2023; IORB 5.40%; Desk directed to maintain the same target range |

The FOMC statement's target range is a policy decision for the **overnight** federal funds market. It is not the effective federal funds rate (EFFR). The [New York Fed's implementation description](https://www.newyorkfed.org/markets/domestic-market-operations/monetary-policy-implementation) says the FOMC announces a target range and uses administered rates to keep the market rate within it. The [EFFR page](https://www.newyorkfed.org/markets/reference-rates/effr.html) defines EFFR as a volume-weighted median of reported overnight transactions and says it is published for the prior business day at about 9:00 a.m. The announcement and the realized transaction statistic require different fields and sources.

The target range is also not a two-year yield or a complete expectations measure. The Federal Reserve's [H.15 description](https://www.federalreserve.gov/releases/h15/current/h15.htm) says the two-year Treasury constant-maturity yield is interpolated from the daily Treasury yield curve using closing market bid yields. It embeds expected policy, term premium, and market conditions; it cannot be replaced by the FOMC range midpoint. A matched two-year cross-country spread needs same-definition, same-observation-date yields for both currencies, with their own publication and vintage evidence. “Surprise” or expectation fields need a separately timestamped pre-announcement source, such as a properly licensed futures/OIS snapshot; the statement alone contains no prior consensus.

## Supported parser contract

### Shared event envelope

Required fields:

```text
source_owner
source_document_id
source_url
observation_period or decision_date
source_clock_raw
source_timezone_raw
source_datetime_resolved
retrieved_at
http_status
content_type
content_hash
parser_version
```

`source_datetime_resolved` must be derived from the date plus the source's own zone token. Preserve the raw clock as evidence. BLS uses `ET`, so a timezone-aware `America/New_York` resolution is needed to distinguish winter UTC−05:00 from daylight-saving UTC−04:00. The Federal Reserve pages are stronger: they explicitly say `EST` on 1 February and `EDT` on 22 March and 26 July. The resolved timestamp is the **scheduled/embargo release instant**, not receipt.

Keep these additional times separate when available:

```text
source_stated_release_at
first_byte_received_at
document_complete_at
feed_vendor_timestamp
database_ingested_at
```

No field may be backfilled from another one. A source-stated embargo clock establishes when publication was authorized, not when any particular feed or process received it.

### BLS CPI payload

Require all of the following before accepting a release:

```text
release_id                 # e.g. USDL-23-0277
series_scope               # CPI-U, all items, U.S. city average
observation_month
mom_percent
mom_adjustment = seasonally_adjusted
mom_period = preceding_month
yoy_percent
yoy_adjustment = not_seasonally_adjusted
yoy_period = 12_months_ending_observation_month
```

Parse the first paragraph and cross-check Table A's `All items` row. Reject a mismatch, missing sign/direction, missing adjustment label, wrong observation month, access-denied body, or unexpected media type. Treat the exact unadjusted index level as an optional separate field with base `1982-84=100`. Do not emit a seasonally adjusted index level from these archive pages.

### FOMC payload

Require:

```text
decision_date
release_clock_raw          # includes EST or EDT
target_lower_percent
target_upper_percent
statement_identity
implementation_effective_date
```

Cross-check the range in the statement against the linked implementation note. Store IORB, ON RRP, primary credit, and EFFR only as separately named measures. Do not label the target midpoint as an observed rate. Do not infer expectation, surprise, two-year spread, or actual receipt latency from the statement.

## What remains unproved

- The BLS archive establishes a source-stated `8:30 a.m. (ET)` clock and exact headline percentage identity through readable official archive content, but this host did not obtain an original HTTP 200 capture. It is therefore research evidence, not production-fetch acceptance.
- The BLS source-stated clock can be resolved deterministically by date, but the archived source itself says only `ET`, not `EST`/`EDT` or UTC offset.
- Neither BLS archive nor ALFRED release date proves the precise instant ALFRED ingested the value.
- None of the pages proves first-byte or complete-document receipt by the desk. That requires contemporaneous capture logs from a qualified fetch path.
- The FOMC pages prove source-stated clocks and announced ranges, with original HTTP 200 retrieval in this review. They do not prove actual release transport time, market receipt, EFFR, two-year yields, or expectations.
- Present archive availability does not establish a contractual permanence guarantee. Preserve qualified captures with URL, bytes, media type, hash, retrieval time, and parser version.

