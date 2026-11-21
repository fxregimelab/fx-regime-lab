# NSDL original FPI source evidence

Research date: 27 September 2026. Scope: leaf 21.1, source inspection only. This report is the only repository file owned by this work. No application provider ingestion, database access, model call, notification, service startup, commit, push or deployment was performed. Humanscope, Research, Agent Reach and the quality-first policy were applied. Docker and heavy Hermes services were not required; Hermes configuration was not changed.

**Original production HTML was obtained for both reports.** Ordinary PowerShell `Invoke-WebRequest` GET requests returned HTTP 200. The response-body byte streams were saved directly, without rendering or re-encoding. These captures resolve the original-table evidence gap in the [earlier source review](repair-fpi-source-research.md). They do not establish reliable scheduled acquisition, historical release times, production persistence or FPI activation.

## Evidence retained privately

All artifacts below are under `C:/Users/sakha/.agent-reach/fxregimelab-fpi-evidence/`, outside the repository. Filenames are relative to that directory. Each original HTML and Jina HTML capture has a corresponding receipt with source URL, method, request start and completion times. `manifest.json` records artifact sizes and SHA-256 hashes.

| Original response body | Retrieved at, UTC | Bytes | SHA-256 |
|---|---|---:|---|
| `latest-direct.html` | 2026-09-27T12:32:50.1044666Z | 59,129 | `5283f52784fd0cc9a7d41968cb6a34f69700923f4adb20ffe6d509a38ca8ca81` |
| `monthly-direct.html` | 2026-09-27T12:32:32.0884114Z | 291,533 | `632537a467a15ff386104b3fa7a4a6b983b062d752ac1757eb8974954cdcd752` |
| `fpi-note-direct.html` | 2026-09-27T12:34:47.4045370Z | 3,055 | `44702caf2cc7eed338396a39f2ee2541e616ef892bd98c0e2541ff626e6baa00` |

The source URLs are [Latest.aspx](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx), [Monthly.aspx](https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx), and [FIINote.htm](https://www.fpi.nsdl.co.in/web/Reports/FIINote.htm). The note URL was discovered in the report's actual `fiiNote()` JavaScript, then retrieved normally. The recorded timestamps are this research retrieval's times, not publication times or durable production first-seen times.

The direct requests supplied no cookies, credentials, custom user agent or proxy override. Earlier web-tool retrieval still returned 502. The public in-app browser independently loaded both report pages and exposed their real cell spans. This is one observed successful access method, not proof that a Python application fetcher or its deployment network can acquire them.

Separate `latest-jina-dom.html` and `monthly-jina-dom.html` captures used Agent Reach's documented Jina route, with the vendor-documented `X-Respond-With: html` option. [Jina documents that format](https://github.com/jina-ai/reader#using-request-headers) as browser-serialized `documentElement.outerHTML`. Those are real serialized DOM captures, **not original HTTP response bytes**. All investment data-cell text matched the later original-body captures in a local comparison. The earlier `latest-jina.txt` is Markdown research output and is not a parser fixture. None of these routes used a login or bypassed a challenge.

The visible Excel control is a link with ID `btnExcel`, invoking the ASP.NET `__doPostBack('btnExcel','')` action. One ordinary browser click produced NSDL's Request Rejected page, support ID `18072527208360906171`; no download arrived. The rejected export was not retried or bypassed. No Excel workbook, export MIME type or export-cell layout was verified.

## Verified original table structure

Both original pages place two `table.tbls01` elements inside `div#rpt`; neither table has an ID. The first contains investment data. The second is explicitly headed as derivative trades and is a different dataset. A parser can use these observed selectors to find candidates, then must verify the heading and eight logical column labels. Table position alone is insufficient. [Production report](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx)

The investment columns are reporting date, asset category, investment route, gross purchases in INR crore, gross sales in INR crore, net investment in INR crore, net investment in USD million, and INR per USD conversion. The printed category heading omits several categories that actually occur. Validate the seven row labels below rather than treating that heading as an exhaustive list.

| Category label | Physical span | Detail route labels before `Sub-total` |
|---|---:|---|
| Equity | 3 | Stock Exchange; Primary market & others |
| Debt-General Limit | 3 | Stock Exchange; Primary market & others |
| Debt-VRR | 3 | Stock Exchange; Primary market & others |
| Debt-FAR | 3 | Stock Exchange; Primary market & others |
| Hybrid | 3 | Stock Exchange; Primary market & others |
| Mutual Funds | 6 | Equity schemes; Debt schemes; Hybrid schemes; Solution oriented schemes; Other schemes |
| AIFs | **4** | Stock Exchange; Primary market & others |

Each reporting date and conversion cell has `rowspan='25'`. The first row of a date has eight physical cells. Subsequent route rows generally have five physical cells because date, category and conversion are inherited. Each ordinary category's first row has six physical cells when the date and conversion already span it. The 25 rows consist of 17 detail rows, seven category subtotals and one grand total. [Monthly report](https://www.fpi.nsdl.co.in/web/Reports/Monthly.aspx)

**AIFs spans its three category rows and the grand-total row.** The latter is `<tr class='total' ...>` with `Total` followed by four amounts. Generic span expansion therefore assigns an inherited AIFs category to the grand total. Recognize the total row before category aggregation; do not include it in the AIF subtotal. The inspection artifact intentionally retains this raw inherited label so the source quirk remains auditable.

Other details that matter for a real parser:

- The explanatory row on each page uses `colspan='9'`, although the data has eight columns. The Latest report title also spans nine; the Monthly title spans eight. Validate header and data widths separately; do not impose the decorative title width on data rows.
- The original HTML omits closing `</td></tr>` between the blank footer row and the Note row. Python's `html.parser` retains a nested footer row; the browser repairs it into sibling rows. This is an observed source defect, not fabricated malformed-fixture evidence. Exclude footer content semantically and test the chosen parser against the preserved original bytes.
- Latest has 30 investment `tr` elements: three introductory/header rows, 25 data rows and two footer rows. Monthly has 455: three introductory/header rows, 18 date blocks of 25 and two footer rows. Direct-child row counts differ under `html.parser` because of the malformed footer. Derivatives have 14 and 167 rows respectively.
- Monthly has one investment column-header row, not a repeated header for each date. Every date starts with fresh date/category/conversion spans. Its headline refers to 25 September but the first block is 1 September. Do not assign the headline date to every row.
- The observed September dates are 1, 2, 3, 4, 7, 8, 9, 10, 11, 15, 16, 17, 18, 21, 22, 23, 24 and 25. This is a captured set, not an independently verified reporting calendar. There is no separate month-total investment row in this capture.

These facts were checked in original HTML and against the direct browser DOM. Serialized DOM conveniently repairs the footer; it must not replace the original bytes when testing parser behavior.

## Amounts, reconciliation and conversion

`inspect-source.py` is a private, read-only inspection script. It expands the observed spans and uses decimal arithmetic. `source-analysis.json` preserves physical cells and expanded rows; `arithmetic-summary.json` preserves the results. These are research derivatives, not application ingestion records or a production parser.

Across all 450 Monthly investment rows, every numeric cell was present. Amounts used two decimal places, negatives used parentheses, and genuine zeros were `0.00`. No blank, dash, comma-formatted amount or leading-minus example occurred in this capture. Supporting commas or leading minus signs would be a deliberate parser extension requiring its own validation; replacing blanks with zero is not justified. The conversion strings use `Rs.` and four decimal places.

All tested INR row identities, detail-to-subtotal sums and seven-subtotal-to-grand-total sums reconciled **exactly** at displayed precision on all 18 dates. USD detail/subtotal/grand-total sums also reconciled exactly. Latest's 25 data rows matched Monthly's final date block, including the USD and conversion columns. The 25 September published net grand total was -6,552.71 crore. These are offline source checks, not accepted live observations.

Recomputing USD aggregates from the rounded INR aggregate and displayed rate does not always match the published USD aggregate to 0.005 million. On 25 September, mutual funds report INR 198.94 crore and USD 20.75 million; direct conversion at 95.9099 gives about 20.74238 million. The grand total converts to about -683.21518 million, while the published USD aggregate is -683.20 million. On 21 September, the total conversion difference is about 0.02582 million. Even the 18 September equity Stock Exchange row differs by about 0.00570 million. Do not reject an otherwise reconciled INR observation solely because it fails a universal half-cent USD conversion check, or overwrite the published USD field with a recomputation.

The [official note](https://www.fpi.nsdl.co.in/web/Reports/FIINote.htm) attributes possible total discrepancies to rounding. It describes the conversion convention as the trading day's RBI reference rate, using the preceding reference rate for a bank holiday. That is verified wording of the linked source note; this investigation did not independently validate those rates or the note's current upstream rate provider.

**Proposed engineering rule, not source fact:** reconcile INR using decimal arithmetic with a written precision policy. If all inputs and outputs independently round to 0.01 crore, a row purchases-minus-sales-minus-net bound is 0.015 crore, and the sum of `k` displayed components against one displayed total has a half-unit bound of `(k+1)*0.005` crore. These bounds depend on the assumed rounding model; the capture itself needed no tolerance. Preserve USD and the printed rate in raw evidence separately from the canonical INR amounts.

## Coverage and use limits

The linked note describes securities activity beyond cash purchases and sales, including corporate actions such as bonus issues and conversions, and places REITs/InvITs in Hybrid. That strengthens the existing caution: the amounts are neither directly measured cross-border cash movements nor observed USD/INR conversion demand. Do not label the confirmed report as a pure cash-flow series. [Official report note](https://www.fpi.nsdl.co.in/web/Reports/FIINote.htm)

The original report contains source terms restricting reproduction, redistribution and transmission and retaining NSDL's proprietary rights. Public access is not an open-data licence. Raw tables and full source terms remain in the private evidence directory; this report is an inspection record. Permission for public fixtures, redistributed tables or a production publication policy was not established. This is a source-term finding, not a legal ruling. [Terms embedded in the production report](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx)

The next parser can now be tested against actual original production captures, including the AIF total overlap and malformed footer. Remaining work includes the parser itself, dated immutable storage, release/first-seen eligibility, calendar and age policy, live/staged/replay agreement, operational acquisition checks and frozen evaluation. None is completed by this report. No official release timestamp, revision archive or historical first-release record was discovered. The Excel path remains unverified after rejection. Agent Reach's optional CLI update check was unavailable because `agent-reach` was not found in this shell.

