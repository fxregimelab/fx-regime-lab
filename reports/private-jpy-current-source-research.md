# Bank of Japan current policy and news sources

## Scope and result

This is a bounded, read-only source review for the private JPY current-fundamentals input. I inspected live original responses from the Bank of Japan (BOJ) on 2 October 2026 IST. The HTTP receipts below were recorded from 18:35:49 to 18:36:31 UTC on 1 October 2026.

The usable current policy marker is the BOJ homepage's item labelled **Guideline**: the Bank “will encourage the uncollateralized overnight call rate to remain at around 1.25 percent.” Admit this as a policy **guideline/target**, observed on the current page. Do not substitute the realised overnight call rate or the interest paid on eligible BOJ account balances.

The English “What's New” feed is usable for individual, attributed headlines with source-stated timestamps. It is not a complete policy-decision feed: the observed snapshot omits the main current decision even though that decision appears on the BOJ website. Absence from the feed must not mean “policy unchanged.”

## Current policy: exact source and meaning

Primary current route:

- Page: [BOJ English homepage](https://www.boj.or.jp/en/index.htm) (`https://www.boj.or.jp/en/` returned the same bytes).
- Live response: HTTP 200; `text/html; charset=UTF-8`; 64,171 bytes; SHA-256 `5dcdd87286d207642eb3df49c2adb3fbdd4fad498aefc3e8b582d7879316424d`.
- Exact source label: `Guideline`.
- Current assertion: `The Bank will encourage the uncollateralized overnight call rate to remain at around 1.25 percent.`
- Current state-page link: [Statements on Monetary Policy 2026](https://www.boj.or.jp/en/mopo/mpmdeci/state_2026/index.htm). Its live response was HTTP 200; `text/html; charset=UTF-8`; 38,068 bytes; SHA-256 `5dbeceffcec65b427ff1eb72520f64c291c3d78c61c0321e18a10aa6ce41d8f2`.

The homepage establishes only what was visible when fetched. Store its time as `current_page_observed_at = 2026-10-01T18:35:50.8895638Z` and retain the raw-body hash. The page does not give that guideline an update time, publication timestamp, or effective date. Do not copy a neighbouring card's “since” date onto it.

The linked controlling document supplies separate decision evidence:

- [Change in the Guideline for Money Market Operations](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918a.pdf)
- Live response: HTTP 200; `application/pdf`; 208,861 bytes; SHA-256 `36d7aa63ff283e25dcc07bc1f6e0caaad8e6764d30cf22433b5c2dd0b6bda391`; HTTP `Last-Modified: Fri, 18 Sep 2026 03:28:25 GMT`.
- The document is dated 18 September 2026. It says the 17–18 September meeting adopted an intermeeting guideline of around 1.25% and expressly makes the guideline effective on 24 September 2026.
- Its release schedule states 18 September at 11:54, but the document does not print a UTC offset beside that clock. Preserve it as a source-stated local clock unless another original source supplies an explicit offset. The file's HTTP `Last-Modified` is server metadata, not proof of first public availability.

Recommended normalized record:

| Field | Value | Basis |
|---|---:|---|
| source | Bank of Japan | Original BOJ page and document |
| source label | Guideline | Homepage label |
| instrument | Uncollateralized overnight call rate guideline | Exact target noun in the page and PDF |
| value | 1.25 | Numeric part of “around 1.25 percent” |
| unit | percent | Source wording |
| qualifier | around | Preserve; the value is not an exact realised rate |
| decision date | 2026-09-18 | Main decision PDF |
| effective date | 2026-09-24 | Main decision PDF, independently stated for the guideline |
| publication timestamp | unknown | No explicit offset for the main decision's 11:54 clock; the main item is absent from the RSS |
| current page observed at | 2026-10-01T18:35:50.8895638Z | This review's HTTP receipt |

This is a descriptive current policy observation. It is not a point-in-time historical vintage merely because the PDF has a decision and effective date.

## Do not merge the three rate objects

The homepage places three related but different observations near one another:

1. **Policy guideline:** around **1.25%** for the uncollateralized overnight call rate.
2. **Reserve remuneration:** `Interest Rate Applied to the Complementary Deposit Facility`, **1.25% since 24 September 2026**. The main decision says this applies to current-account balances at the BOJ excluding required reserve balances. It is a separate administered rate.
3. **Realised market rate:** `Uncollateralized Overnight Call Rate (average)`. The homepage discovers its current JSON through `#jf2[j-file]`; the filename rotates and must not be hard-coded.

The live homepage pointed to:

`https://www.boj.or.jp/statistics/market/short/mutan/d_release/mp/data/topm20261001_152242.json`

Its response was HTTP 200; `application/json`; 67 bytes; SHA-256 `fb404f53bc17869db7485b16ba4792b5134fa791dec452cbd4901ce5d9208fd7`; HTTP `Last-Modified: Thu, 01 Oct 2026 06:24:52 GMT`. Its complete schema is three small fields: `mutan_date`, `mutan_scallk`, and `mutan_soku`. The observed values were date `2026/10/01`, average `1.227`, and status flag `1`. BOJ's own [homepage rendering script](https://www.boj.or.jp/common2/js/en_top.js) prefixes `P ` when that flag is not `0`, so this is a **provisional realised average of 1.227% for 1 October 2026**. It is not the 1.25% guideline.

The stable landing page is [Call Money Market Data](https://www.boj.or.jp/en/statistics/market/short/mutan/index.htm). Its live response was HTTP 200; `text/html; charset=UTF-8`; 43,793 bytes; SHA-256 `1de629447724a4ed8e2634eb22c56230dc47bbc0a5ad661f466a606a4c1252e9`. BOJ says same-business-day provisional results normally update around 17:15 and prior-business-day final results around 10:00, with a different month-end provisional schedule. That page does not put an explicit timezone next to those approximate schedules. Do not turn them into exact availability timestamps.

## English RSS route and observed contract

The BOJ advertises the general English feed at [RSS Feeds](https://www.boj.or.jp/en/tips.htm). That discovery page returned HTTP 200; `text/html; charset=UTF-8`; 38,268 bytes; SHA-256 `70900e55a356e7df86701f7678fd9bf05076ad4054ee572a331f1dd91eb7f79f`.

`https://www.boj.or.jp/en/rss/whatsnew.xml`

Live response:

- HTTP 200; `application/xml; charset=UTF-8`; 17,267 bytes.
- SHA-256 `5117346484b14aa71fc798d57ad3d158b697353888573e78b793bc7bd342303f`.
- Receipt: `2026-10-01T18:35:52.3593446Z`.
- No observed `ETag`, HTTP `Last-Modified`, channel `pubDate`, or channel `lastBuildDate`.

This is **RSS 2.0**, not an Atom feed. The root is unnamespaced `<rss version="2.0">` and declares `xmlns:atom="http://www.w3.org/2005/Atom"`. The Atom namespace is used for the channel's self-link, whose declared type is `application/rss+xml`. Each of the 52 observed items had `title`, empty `description`, `pubDate`, `link`, and `guid`.

All 52 item links used the exact origin `http://www.boj.or.jp`. All 52 `pubDate` values included an explicit `+0900` offset and parsed to non-future instants. A limited example is:

```text
title: Summary of Opinions at the Monetary Policy Meeting on September 17 and 18, 2026
pubDate: Thu, 01 Oct 2026 08:50:00 +0900
link: http://www.boj.or.jp/en/mopo/mpmsche_minu/opinion_2026/opi260918.pdf
```

Eight observed items used `/en/mopo/` paths. Useful policy headlines included the Summary of Opinions, meeting minutes, bond-purchase schedules, the complementary-deposit amendment, and `(Reference) Change in the Guideline for Money Market Operations` at `Fri, 18 Sep 2026 11:54:00 +0900`.

The feed did **not** contain the main decision URL `k260918a.pdf`. The current [What's New page](https://www.boj.or.jp/en/whatsnew/index.htm) did contain it, but only with `<time datetime="2026-09-18">`; that is a calendar date, not a timestamp. The page response was HTTP 200; `text/html; charset=UTF-8`; 345,886 bytes; SHA-256 `862ef965e5fb9b86227d472d01e73ee00a8eecb62b687d64fefd5181eb285c07`.

Therefore:

- An RSS `pubDate` is a BOJ-asserted publication timestamp for that item, with an explicit offset. It is not proof of the first moment the URL became available.
- An HTML `datetime="YYYY-MM-DD"` remains date-only. Do not invent midnight, a clock, or a timezone.
- An HTTP receipt proves availability at retrieval time only. `Last-Modified` is not first-seen availability.
- The feed snapshot is mutable current state, not a historical availability archive.
- The reference item's 11:54 `+0900` timestamp must not be transferred to the absent main decision, even though their subject matter is related.
- A missing policy headline remains a coverage gap. Do not infer unchanged policy.

## Bounded admission and parser tests

Use original response bytes and fail closed. The following tests exercise content semantics, not only HTML layout.

### Current policy

1. Require HTTP 200, expected media type, no redirect, a size cap, receipt UTC, original byte length, and SHA-256 before parsing.
2. In the homepage body, require exactly one current `Guideline` assertion with all of: `uncollateralized overnight call rate`, `around`, one finite numeric value, and `percent`. Require its decision link to the exact BOJ host and `/en/mopo/mpmdeci/state_YYYY/` path family. Zero or multiple matches are unavailable.
3. Follow only a same-host decision link discovered from that page/state page. Require PDF media type and `%PDF` magic. Extract the target noun, value, decision date, and effective date from the main decision. If the page and decision disagree, do not choose one silently; mark current policy unavailable for review.
4. Keep `Guideline`, `Complementary Deposit Facility`, and realised `Uncollateralized Overnight Call Rate (average)` as separate instruments. A shared numeric value must not collapse them.
5. Discover the rotating actual-rate JSON from the current homepage each run. Require the exact BOJ host, expected path prefix, `.json`, at most 2 KiB, exactly the three observed keys, `YYYY/MM/DD`, a finite numeric average, and `mutan_soku` in `{0,1}`. Treat `1` as provisional and retain that status.
6. Store page observation time, decision date, effective date, source-stated publication time, and first-seen retrieval time in separate nullable fields. Never fill one from another.

Negative fixtures derived from the original bodies should cover a missing target phrase, duplicate guideline nodes, multiple numbers, changed unit, page/PDF mismatch, missing effective date, unexpected media type, redirect, malformed decimal, stale hard-coded JSON filename, unknown status flag, and oversized body.

### RSS headlines

1. Require HTTP 200, XML media type, no redirect, and a bounded raw body, such as 256 KiB. Hash and timestamp the original bytes before XML parsing.
2. Disable DTD and external-entity resolution. Require the unnamespaced RSS 2.0 root, the exact Atom namespace URI, and a same-source channel self-link.
3. Require non-empty `title`, `link`, `guid`, and `pubDate` for every admitted item. Parse only timestamps containing an explicit numeric offset; convert those instants to UTC. Missing-offset dates are unavailable rather than assumed to be Japan time.
4. Allow only the exact host `www.boj.or.jp`. The current original items use HTTP; retain the original URL for evidence, then canonicalize or fetch through HTTPS under a documented transport rule. Do not rewrite before hashing or treat a redirect as publication evidence.
5. De-duplicate on canonical GUID/link plus source timestamp. Reject conflicting duplicates, future timestamps, external hosts, malformed dates, item-count overflow, and oversized bodies.
6. Admit headlines as headlines only. Empty descriptions provide no article content. Fetch and parse the linked original PDF/page before deriving a policy value, instrument, decision date, or effective date.
7. Add a completeness control for the current decision route. The observed feed containing only `k260918b.pdf` must not satisfy the presence of `k260918a.pdf`. Preserve an explicit BOJ policy-news coverage warning when the main decision is absent.

## Availability limit and next evidence needed

This review supports a current descriptive JPY policy marker and individually timed BOJ headlines. It does not support historical point-in-time availability. Predictive fundamentals still require a polling archive that records, for every fetch, the request URL, receipt UTC, status, relevant headers, original bytes/hash, parser version, and whether the observation was provisional or final. The archive must demonstrate when each current page, decision, feed item, and realised-rate release was first seen.

It also does not turn the policy guideline into realised funding cost, carry, or a two-year yield spread. Those predictive inputs need their own official series, release/vintage rules, and lagged as-of tests. Until those exist, keep them nullable and do not backfill them from the 1.25% policy guideline, the 1.25% reserve-remuneration rate, or the 1.227% provisional market average.
