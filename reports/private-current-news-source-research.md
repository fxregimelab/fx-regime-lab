# Private current-news source review

Reviewed 1 October 2026. This is a bounded, read-only source review for the private current-context feature. It does not qualify historical availability, trading relevance, predictive value, or release readiness.

## Finding

The six configured central-bank feeds were reachable in one bounded run and carried publisher-attributed headlines, canonical URLs, and timezone-bearing dates. A direct run through the repository's current feed parser at `2026-10-01T14:55:24Z` captured records from all six. Their scope is uneven: some are narrow monetary-policy feeds, while the ECB, Bank of Canada, and Bank of England feeds include broader institutional material.

New Zealand remains a source-integration gap. I found no documented first-party RBNZ RSS feed or public news JSON API. The best supported official discovery route is the [RBNZ homepage](https://www.rbnz.govt.nz/), which exposes recent news cards with a displayed date, headline, summary, and canonical RBNZ article URL. The [news archive](https://www.rbnz.govt.nz/news-and-events/news) is the official full listing, but it did not expose its rows through the bounded reader request, and direct requests from this host met a Cloudflare challenge. The homepage is therefore a valid human-readable discovery source, but not a verified drop-in feed contract.

## RBNZ: supported route and limits

RBNZ's own [release guidance](https://www.rbnz.govt.nz/news-and-events/how-we-release-information) says news releases appear in its news section and on its homepage, with links also distributed through social media and email. It also warns that information can take a few minutes to appear on the website. The page does not document RSS or a public news API.

At `2026-10-01T14:52:46Z`, a Jina reader request for the official homepage returned five current cards. The card schema visible in the rendered official page was:

```text
displayed publication date | headline | summary | canonical rbnz.govt.nz URL
```

Representative records were:

- `01 October 2026` — [Consultation finds strong support for access to cash services](https://www.rbnz.govt.nz/news-and-events/news/2026/10/consultation-finds-strong-support-for-access-to-cash)
- `25 September 2026` — [New Monetary Policy Committee member appointed](https://www.rbnz.govt.nz/news-and-events/news/2026/09/new-monetary-policy-committee-member-appointed)
- `25 September 2026` — [Reserve Bank requests TSB to commission independent report](https://www.rbnz.govt.nz/news-and-events/news/2026/09/reserve-bank-requests-tsb-to-commission-independent-report)
- two further cards dated `22 September 2026`

The cards provide a calendar date only. They do not witness a publication clock or timezone. An adapter must preserve that as a date and must not manufacture midnight, local time, or UTC.

The official [RBNZ sitemap](https://www.rbnz.govt.nz/sitemap.xml) can provide a fallback inventory of canonical news URLs. Its fields are effectively `loc` and `lastmod`; it does not supply the headline or publication timestamp needed by the current contract. The distinction is material: the sitemap listed the 1 October cash-access release with `lastmod=2026-09-30`. `lastmod` is modification metadata, not the displayed release date.

Direct `GET` requests from this host to the news archive and sitemap returned HTTP 403 Cloudflare challenge pages. Jina returned readable HTTP 200 representations of the homepage, sitemap, release guidance, and individual article pages. This verifies the official route and its visible metadata through an intermediary, but does not establish reliable unattended access from the pipeline host. Until an RBNZ adapter has a repeatable first-party retrieval path and a captured response, RBNZ automated news availability should remain `UNAVAILABLE`, not inferred from discovery success.

## Configured central-bank feeds

The table reports one bounded retrieval and the repository parser's output. “14-day records” uses the current review contract's calendar-date window as of 1 October 2026; it is not a statement about market relevance.

| Source | Official endpoint and observed format | Parser result | Recent example | Scope and limitation |
|---|---|---:|---|---|
| Federal Reserve | [`/feeds/press_monetary.xml`](https://www.federalreserve.gov/feeds/press_monetary.xml), HTTP 200, `text/xml`, RSS 2.0 | 15 captured; 0 within 14 calendar days | [FOMC statement, 16 Sep 2026 18:00 GMT](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm) | Monetary-policy press releases only. It is appropriately narrow, but the latest item was outside this review's 14-day window. The feed includes a UTF-8 BOM; the current loader explicitly handles it. |
| European Central Bank | [`/rss/press.html`](https://www.ecb.europa.eu/rss/press.html), HTTP 200, `application/rss+xml`, RSS 2.0 | 15 captured; 15 within 14 days | [Where AI risks meet, 1 Oct 2026 15:30 +0200](https://www.ecb.europa.eu//press/key/date/2026/html/ecb.sp261001~cf3c630379.en.html) | The official channel describes its scope as press releases, speeches, interviews, and press conferences. This is broader than policy decisions. Item URLs currently contain a double slash after the host; a bounded HEAD request returned HTTP 200 without redirect, so this is odd formatting rather than a broken link. |
| Reserve Bank of Australia | [`/rss/rss-cb-media-releases.xml`](https://www.rba.gov.au/rss/rss-cb-media-releases.xml), HTTP 200, `text/xml`, RSS 1.0/RDF | 1 captured; 1 within 14 days | [Financial Stability Review release, 1 Oct 2026 11:30 +1000](https://www.rba.gov.au/media-releases/2026/mr-26-28.html) | Media releases, not a monetary-policy-only feed. The observed document contained only one item, so it is a shallow discovery window. One repeated request received an Akamai “Access Denied” page while later requests and the project parser succeeded; provider access can vary by request path or client. |
| Swiss National Bank | [`/public/rss/en/mopo`](https://www.snb.ch/public/rss/en/mopo), HTTP 200, `application/xml`, RSS 2.0 | 15 captured; 2 within 14 days | [Monetary policy assessment, 24 Sep 2026 07:30Z](https://www.snb.ch/en/publications/communication/press-releases-restricted/pre_20260924) | Monetary-policy material, including policy assessments and quarterly bulletins. The channel's own changing date is feed metadata; use each item's date for the headline. The sampled article returned HTTP 200 despite `press-releases-restricted` appearing in its path. |
| Bank of Canada | [`/content_type/press-releases/feed/`](https://www.bankofcanada.ca/content_type/press-releases/feed/), HTTP 200, `application/rss+xml`, RSS 1.0/RDF | 10 captured; 0 within 14 days | [Board recruitment release, 10 Sep 2026 11:00:09Z](https://www.bankofcanada.ca/2026/09/bank-canada-board-launches-process-fill-external-deputy-governor-position/) | Broad press releases. The feed contained a policy decision, bank-note news, governance, and other institutional releases. The latest item was outside the 14-day window. |
| Bank of England | [`/rss/news`](https://www.bankofengland.co.uk/rss/news), HTTP 200, `text/xml; charset=utf-8`, RSS 2.0 | Feed returned 50 items; current parser examines the first 20 and captured 20, with 13 within 14 days | [Court minutes, 1 Oct 2026 14:00 +0100](https://www.bankofengland.co.uk/minutes/2026/july/court-minutes-16-july-2026) | Broad institutional news. Recent items included Court minutes, a Financial Policy Committee record, and market-participant minutes. The current 20-entry parser cap is an implementation limit, not a source limit. |

All six sampled item URLs returned HTTP 200 without redirect in bounded HEAD requests. That check establishes link reachability at the review time only. It does not prove uninterrupted provider availability.

## Source evidence versus captured implementation evidence

The source finding is that the six configured endpoints currently expose dated, attributed headline records with canonical publisher URLs. Their dates include a timezone, so they can be normalized to UTC without inventing one. The RBNZ homepage instead exposes date-only cards and needs separate handling.

The captured implementation finding comes from [`pipeline/src/private_desk/data.py`](../pipeline/src/private_desk/data.py):

- `_FEEDS` contains Fed, ECB, RBA, SNB, Bank of Canada, and Bank of England endpoints, but no RBNZ source.
- `_parse_feed` handles RSS/Atom entries by stripping XML namespaces, so the RBA and Bank of Canada RDF feeds are supported despite their different root schema.
- `_published` accepts RFC 2822 or ISO dates only when a timezone is present. That is correct for these six feeds, but it intentionally cannot turn RBNZ's displayed date into a timestamp.
- `_parse_feed` inspects at most 20 entries. The Bank of England source returned 50, so current capture is intentionally narrower than the feed.
- `fetch_news` silently skips an unavailable or malformed feed. The next review layer must therefore record central-bank coverage gaps explicitly rather than infer full coverage from a nonempty combined list.

At `2026-10-01T14:55:24Z`, a direct call through `_get_text` and `_parse_feed` captured `15 Fed + 15 ECB + 1 RBA + 15 SNB + 10 BoC + 20 BoE` records. This is a local current capture result. It is not an immutable receipt, production observation, or historical availability proof.

## Time meaning and use boundary

An item date is publisher-supplied metadata. It is not proof of the first instant when the page became public or market participants could retrieve it. HTTP `Last-Modified`, an RSS channel build date, RBNZ sitemap `lastmod`, and Jina's `Published Time` response metadata are transport or document-maintenance signals; none should replace the article's publication field.

The retrieval clock is separate. The bounded feed request was made between `2026-10-01T14:49:01Z` and `2026-10-01T14:55:24Z`. A later current-context review needs its own UTC receipt and must apply the 48-hour retrieval-age gate. It must also reject future publication dates and items older than 14 calendar days. Source discovery alone does not meet either gate.

The feeds support headline-only current context. They do not establish article-body rights, historical point-in-time completeness, correction history, causal relevance, or suitability for a 2–5-day trade. The safe RBNZ outcome is: official dated headline discovery exists, but unattended first-party feed availability is not yet verified.
