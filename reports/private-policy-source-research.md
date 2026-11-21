# BIS policy-history source review

**Review date:** 1 October 2026  
**Scope:** first-party source review for the private seven-pair desk  
**Status:** bounded source finding for coordinator manual review; not checker certification, forecast qualification, migration authority or release acceptance

## Verdict

`BIS/WS_CBPOL/1.0` is a suitable source for a **current retrospective history of published policy markers** for USD, EUR, GBP, AUD, NZD, CAD and CHF, provided that the parser validates the SDMX dimensions and preserves the instrument segments below. It is not a historical-vintage source. A file retrieved now does not establish what values or revisions were available on an earlier trading date.

The main implementation risk is hidden splicing. The Euro-area, UK, New Zealand and Swiss histories contain named instrument changes inside the requested 1999-onward window. The US series keeps one BIS definition, “mid-point of the Federal Reserve target rate”, but the FOMC moved from a point target to a target range on 16 December 2008. Australia and Canada keep one instrument identity throughout this window. Canada changed how the overnight target was defined within its operating band in February 1999, but BIS still classifies both sides as the same target-overnight-rate series.

Do not infer breaks from `OBS_PRE_BREAK`: it was empty in every row of all seven full-window responses reviewed here. The segment registry must come from the current `COMPILATION` metadata and the dated BIS documentation. A five-FX-weekday change must be unavailable if either leg crosses a registry boundary, enters an unknown-definition interval, or contains a missing weekday observation.

## Official BIS source identity and route

The reviewed route is:

```text
https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.{REF_AREA}?format=csv&startPeriod=1999-01-01&endPeriod=2026-09-30
```

The path means data query → `dataflow` context → agency `BIS` → dataflow `WS_CBPOL` → version `1.0` → key `D.{REF_AREA}`. In this data structure, the key dimensions are `FREQ` and `REF_AREA`; `TIME_PERIOD` is the time dimension. The v2 API documentation describes `startPeriod` and `endPeriod` as time filters and returns SDMX 2.1 data. The witnessed successful responses were HTTP 200 with `Content-Type: text/csv;charset=UTF-8`. See the [BIS v2 API documentation](https://stats.bis.org/api-doc/v2/) and the [CBPOL topic page](https://data.bis.org/topics/CBPOL).

The accompanying structure query was:

```text
https://stats.bis.org/api/v2/structure/dataflow/BIS/WS_CBPOL/1.0?references=all
```

It returned the referenced data structure `BIS:BIS_CBPOL(1.0)` and the official codelists. The response was prepared at `2026-10-01T13:34:23Z`, was 305,650 bytes, and had SHA-256 `141B5E7E317658980A9C1D504B174CCB168965F9AECCF85A63FE0BDAA87383FC`.

The codelist meanings relevant to the captured rows are:

| Field/code | Official meaning | Required treatment |
|---|---|---|
| `FREQ=D` | Daily | Require exactly `D`. |
| `REF_AREA` | `US` United States; `XM` Euro area; `GB` United Kingdom; `AU` Australia; `NZ` New Zealand; `CA` Canada; `CH` Switzerland | Map explicitly to USD, EUR, GBP, AUD, NZD, CAD and CHF. |
| `UNIT_MEASURE=368` | Per cent per year | Require exactly `368`; values are annual percentage rates. |
| `UNIT_MULT=0` | Units | Require exactly `0`; do not rescale. |
| `OBS_STATUS=A` | Normal value | Eligible after the remaining validation checks. |
| `OBS_STATUS=M` | Missing value; data cannot exist | Preserve as missing. In these files the literal value is `NaN`; it is not numeric input. |
| `OBS_CONF=F` | Free | Confidentiality status only. It does not mean “final”, vintage-verified or forecast-qualified. |

The full witnessed CSV header was:

```text
FREQ,REF_AREA,UNIT_MEASURE,UNIT_MULT,TIME_FORMAT,COMPILATION,DECIMALS,SOURCE_REF,SUPP_INFO_BREAKS,TITLE,TIME_PERIOD,OBS_VALUE,OBS_STATUS,OBS_CONF,OBS_PRE_BREAK
```

All seven captures used `DECIMALS=4`, `UNIT_MEASURE=368`, `UNIT_MULT=0` and `OBS_CONF=F`. `TIME_FORMAT` was blank. The title identified each series as daily, end of period. These are current source facts, not a promise that future snapshots will keep identical metadata.

## Exact 1999-onward instrument segments

The dates below come from the BIS document [Central bank policy rates – data documentation](https://www.bis.org/statistics/cbpol/cbpol_doc.pdf), last updated 24 September 2026. The downloaded PDF was 339,623 bytes with SHA-256 `66919C739F2393E854D81000EE02AA8814DFB12EE92A7731F37D43DF064B69C8`.

| Currency / area | Inclusive segment | Instrument identity | Compatibility decision |
|---|---|---|---|
| USD / `US` | 1999-01-01 onward | Midpoint of the Federal Reserve target rate | One BIS identity. On 2008-12-16 the FOMC established a 0–0.25% target range and the BIS value became its 0.125% midpoint. Preserve that target-form event as metadata; do not relabel the series as the effective federal funds rate. |
| EUR / `XM` | 1999-01-01 to 1999-01-04 | **Unknown under the dated BIS definition.** The rows contain 3%, but the documentation starts the ECB MRO segment on 1999-01-05. | Fail closed for these four dates. Do not invent an identity from the repeated value. |
| EUR / `XM` | 1999-01-05 to 2000-06-27 | Main refinancing operations, fixed rate | Stable only within the segment. |
| EUR / `XM` | 2000-06-28 to 2008-10-14 | Main refinancing operations, minimum bid rate | New instrument representation; block crossing the boundary. |
| EUR / `XM` | 2008-10-15 to 2024-09-17 | Main refinancing operations, fixed rate | New representation; block crossing the boundary. |
| EUR / `XM` | 2024-09-18 onward | Deposit facility rate, fixed rate; official steering rate | New steering-rate identity; block crossing the boundary. |
| GBP / `GB` | 1999-01-01 to 2006-08-02 | Repo rate | Stable only within the segment. The first normal-value row in this capture is 1999-01-04. |
| GBP / `GB` | 2006-08-03 onward | Official Bank Rate | Treat the BIS name change as a registry boundary. The BoE described the 3 August 2006 decision as the official Bank rate paid on commercial-bank reserves. |
| AUD / `AU` | 1999-01-01 onward | Cash rate target | Stable BIS identity throughout the window. The first returned row is 1999-01-04. |
| NZD / `NZ` | 1999-01-01 to 1999-03-16 | Overnight cash rate | Pre-OCR segment; sparse/missing rows still fail the weekday completeness rule. |
| NZD / `NZ` | 1999-03-17 onward | Official cash rate; official market-intervention representative rate | The OCR starts on 17 March 1999. Block crossing the boundary. |
| CAD / `CA` | 1999-01-01 onward | Central-bank target, overnight rate | Stable BIS instrument identity throughout the window. On 4 February 1999 the new LVTS framework fixed the target at the midpoint of the operating band; retain this as an operating-convention event, not a splice to another instrument. |
| CHF / `CH` | 1999-01-01 to 1999-12-31 | Discount rate | Stable only within the segment. The 1999-12-31 observation is missing. |
| CHF / `CH` | 2000-01-01 to 2019-06-12 | Midpoint of the SNB target range | New instrument representation; block crossing the boundary. The first normal row after the boundary is 2000-01-03. |
| CHF / `CH` | 2019-06-13 onward | SNB policy rate | New policy marker; block crossing the boundary even though the value stayed at −0.75% on the switch date. |

First-party central-bank records corroborate the important transitions:

- The ECB decided in March 2024 to steer the monetary-policy stance through the deposit facility rate and reduce the MRO–DFR spread from 18 September 2024. Its 12 September statement again said that the operational changes would take effect on 18 September. This is a concrete example of an announcement date differing from the effective date used in the BIS segment. [ECB operational-framework decision](https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.pr240313~807e240020.en.html); [ECB monetary-policy statement of 12 September 2024](https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2024/html/ecb.is240912~4f7b17040c.en.html).
- The SNB said on 13 June 2019 that its new policy rate replaced the former target range for three-month Libor. [SNB monetary-policy assessment](https://www.snb.ch/en/publications/communication/press-releases/2019/pre_20190613).
- The RBNZ set its first OCR at 4.50% on 17 March 1999. [RBNZ March 1999 Monetary Policy Statement](https://www.rbnz.govt.nz/hub/publications/monetary-policy-statement/monetary-policy-statement-march-1999).
- The Bank of England described its 3 August 2006 action as a change in the official Bank rate paid on commercial-bank reserves. [BoE August 2006 decision](https://www.bankofengland.co.uk/news/2006/august/mpc-august-2006); [BoE Bank Rate history](https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp).
- The Federal Reserve established the 0–0.25% target range on 16 December 2008. The BIS series shows 0.125% on that date because its documented representation is the midpoint. [FOMC statement](https://www.federalreserve.gov/newsevents/press/monetary/20081216b.htm).
- The RBA’s official history shows the cash-rate target as a single target from 2 August 1990, before this review window. [RBA cash-rate history](https://www.rba.gov.au/statistics/cash-rate/).
- The Bank of Canada records the June 1994 move to the overnight-rate target and the February 1999 definition of that target as the operating-band midpoint. Its LVTS history dates the new framework to 4 February 1999. [BoC key-rate history](https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/history-key-interest-rate/).

## Exact current `COMPILATION` allowlist

The following strings were independently read from the 1 October 2026 CSV responses. Matching should be exact after the CSV parser has decoded quoting; a difference should fail closed for review rather than being silently accepted.

### `US`

```text
From 19 Dec 1985 onwards: mid-point of the Federal Reserve target rate; from 1 Jul 1954 to 18 Dec 1985: US Fed Funds effective rate.
```

### `XM`

```text
From 18 Sep 2024 onwards: official central bank steering rate is the deposit facility rate, fixed rate; from 15 Oct 2008 to 17 Sep 2024: official central bank liquidity providing, main refinancing operations, fixed rate; from 28 Jun 2000 to 14 Oct 2008: official central bank liquidity providing, main refinancing operations, minimum bid rate; from 5 Jan 1999 to 27 Jun 2000: official central bank liquidity providing, main refinancing operations, fixed rate.
```

### `GB`

```text
From 3 Aug 2006 onwards: official bank rate; from 6 May 1997 to 2 Aug 2006: repo rate; from 20 Aug 1981 to 5 May 1997: minimum Bank of England Band 1 dealing rate; from 16 Oct 1972 to 19 Aug 1981: minimum lending rate; from 1 Jan 1946 to 15 Oct 1972: bank rate.
```

### `AU`

```text
From 2 Aug 1990 onwards: cash rate target; from 23 Jan 1990 to 1 Aug 1990: middle of the cash rate target range; from 7 Apr 1976 to 22 Jan 1990: interbank overnight cash rate.
```

### `NZ`

```text
From 17 Mar 1999 onwards: Official market intervention representative rate, official cash rate; from Jan 1985 to 16 Mar 1999: overnight cash rate.
```

### `CA`

```text
From 1 Jun 1994 onwards: Central Bank target, overnight rate; from 27 Jul 1960 to 31 May 1994: official bank rate.
```

### `CH`

```text
From 13 June 2019 onwards SNB Policy rate; From 1 Jan 2000 to 12 June 2019 mid-point of the SNB target range; from 1 Jan 1946 to 31 Dec 1999: discount rate.
```

Capitalisation and punctuation above reflect the current CSV, including the missing colon after “onwards” in the Swiss text. The PDF uses slightly different editorial capitalisation. The allowlist should follow the machine response, while the segment registry should follow the dated substance of the official documentation.

## Current-snapshot evidence

These are retrieval summaries, not preserved source bodies. The temporary response bodies were kept outside the project during review. The requested end date was 30 September 2026, but the latest returned reference date differs by source series. That is expected in a current snapshot and must not be overwritten by a requested date.

| Area | Bytes | Rows | Normal / missing | First normal | Last normal | SHA-256 |
|---|---:|---:|---:|---|---|---|
| `US` | 2,657,315 | 10,132 | 10,132 / 0 | 1999-01-01 | 2026-09-28 | `95926D9D842DFC692DAA76B0D626FF8F5C383B0E8AAAABC57489D563F5938D04` |
| `XM` | 5,890,534 | 10,134 | 10,102 / 32 | 1999-01-01 | 2026-09-29 | `551FD43690CC0A523D32BD78E3FB0105C5221D6D15981D0FF6AAD7879F55BFE1` |
| `GB` | 2,760,828 | 7,246 | 7,014 / 232 | 1999-01-04 | 2026-09-28 | `6B57B5B9059C0482C2AA4476576171BFE9E4C1678A330B4349AD75BF3E21F8D5` |
| `AU` | 4,860,927 | 7,022 | 7,022 / 0 | 1999-01-04 | 2026-09-24 | `C7330E4E62DE22A2B540AD910BBFD655CAD68C3100B7A14675C3EF874D9D5EEA` |
| `NZ` | 3,549,545 | 10,108 | 8,859 / 1,249 | 1999-01-05 | 2026-09-25 | `40D1F18AC85E0EDD065B4FB15ECBF918FC7CDA1833DE36003C56B5F8CF76B6CB` |
| `CA` | 5,687,048 | 9,115 | 7,217 / 1,898 | 1999-01-04 | 2026-09-28 | `3D848E802A53DFC3254024CFAE41AC0839545F72F7F2D96B21C082A3AE70005C` |
| `CH` | 2,013,035 | 7,238 | 7,232 / 6 | 1999-01-04 | 2026-09-29 | `63480CDB9E35724340A245EADBA9725B8C9310DA67A9F61D8A2D6E53AA7C5286` |

All missing rows had `OBS_STATUS=M`, `OBS_VALUE=NaN` and `OBS_CONF=F`. A validator should accept the `NaN` token only with status `M`, store it as missing, and prohibit it from arithmetic. It should reject a finite value paired with `M`, a `NaN` paired with `A`, or any unreviewed status.

`OBS_PRE_BREAK` was blank on all 60,995 reviewed rows. It cannot substitute for the segment registry. `SUPP_INFO_BREAKS` contains useful series-level prose for AU, NZ and CA, but it is repeated metadata, not a row-specific event marker.

The first-party source labels were exactly: `US Federal Reserve System`, `European Central Bank`, `Bank of England`, `Reserve Bank of Australia`, `Reserve Bank of New Zealand`, `Bank of Canada`, and `Swiss National Bank`.

## Date meaning, publication timing and vintage limits

The BIS documentation says daily data are released around mid-week. It also says the metadata contain, where possible, information on the lag between announcement and effective date. This does **not** make each `TIME_PERIOD` an announcement timestamp or an observation-specific availability timestamp.

Three separate clocks must remain separate:

1. **Decision or announcement time:** when the central bank communicated the decision. This can include an intraday time that the CSV does not carry.
2. **Effective/reference date:** the day represented by `TIME_PERIOD`. The ECB’s September 2024 change was announced on 12 September and effective on 18 September; the BIS switch occurs on 18 September.
3. **BIS publication/receipt time:** when a particular snapshot became available from BIS. The API response and HTTP receipt establish only the current retrieval. They do not reconstruct the original weekly publication time for every historical observation.

The witnessed schema has no `available_at`, release timestamp, revision sequence or vintage date. The API’s `updatedAfter` facility is a filter for data changed after a query time; it is not a point-in-time archive of what an earlier user would have received. Therefore:

- `TIME_PERIOD` must not be used as an announcement clock.
- A current 2026 snapshot must not be admitted to historical price calibration as if its values and metadata were known on each reference day.
- `OBS_CONF=F` must not be read as final-vintage evidence.
- `historical_publication_time`, `historical_receipt_time` and `historical_vintage` remain `UNKNOWN` unless a separate immutable capture supplies them.
- Any predictive trial needs a separate timing/vintage contract and independent out-of-sample evaluation.

## Feature meaning and fail-closed rules

For the private desk, the policy differential is a **difference between published policy markers** in percentage points:

| Pair | Level definition |
|---|---|
| EUR/USD | EUR marker − USD marker |
| GBP/USD | GBP marker − USD marker |
| AUD/USD | AUD marker − USD marker |
| NZD/USD | NZD marker − USD marker |
| USD/CAD | USD marker − CAD marker |
| USD/CHF | USD marker − CHF marker |
| EUR/GBP | EUR marker − GBP marker |

It is not a two-year sovereign-yield spread, broker carry, an interest-rate surprise, an announcement reaction, or evidence of a profitable directional bias. A difference can be arithmetically correct while remaining economically discontinuous at an instrument splice.

For a fixed five-FX-weekday differential-change feature:

- require a normal, finite observation for every weekday used in both legs;
- match the two legs on the same reference dates;
- do not fill a holiday, missing row or `M/NaN` row from the prior day;
- do not count weekend observations as FX weekdays even when the source supplies them;
- require one stable instrument identity in each leg across the full window;
- suppress the output when the window crosses any EUR, GBP, NZD or CHF segment boundary above, or the unknown EUR interval of 1–4 January 1999;
- retain observation dates, source hashes and both instrument identities with every output;
- label every derived value `RETROSPECTIVE_ONLY`, with historical availability and forecast qualification unknown.

The exact `COMPILATION` allowlist and the reviewed segment registry serve different controls. The allowlist detects source-definition drift at capture time. The registry prevents arithmetic across definitions already disclosed within an accepted long series. Both are required.

## Bounded acceptance statement

This review supports a source contract that captures seven current BIS policy histories, validates the official SDMX meanings, preserves `M/NaN` as missing, records the exact source metadata, and blocks every known or unknown definition crossing. It does not establish historical vintage, point-in-time availability, predictive validity, production readiness, database acceptance, checker certification or release acceptance.
