# Japan policy-marker source review

**Review date:** 1 October 2026  
**Scope:** official BIS `WS_CBPOL` and Bank of Japan source semantics for a bounded R2 extension  
**Status:** source recommendation only; no code change, full-history capture, forecast qualification, production write or release acceptance

## Finding

The official daily series is `BIS,WS_CBPOL,1.0/D.JP`, mapped to JPY. It is usable as a **retrospective history of the policy marker selected by BIS**, provided the implementation preserves the documented instrument changes and leaves three intervals unavailable. It is not one continuous Japanese policy rate.

The decisive gaps are 12 February 1999–10 August 2000, 19 March 2001–8 March 2006, and 4 April 2013–20 September 2016. In the last two intervals the Bank of Japan used a quantity target rather than a single interest-rate operating target. The BIS daily API returns no observation for the sampled 2013 QQE dates after 3 April 2013 and no result around the January–February 2016 introduction of the tiered negative reserve rate. A strict mapping must not fill those dates with zero, an observed call rate, the `-0.1%` reserve remuneration rate, or a carried-forward value.

From 21 September 2016 to 20 March 2024 the BIS figure is the Bank of Japan's `-0.1%` short-term policy interest rate applied to Policy-Rate Balances. It is not the realised uncollateralized overnight call rate. From 21 March 2024, the instrument changes to an uncollateralized overnight call-rate guideline. The Bank set a `0–0.1%` range effective that day; the BIS observation is `0.05`, the midpoint required by the BIS convention for target bands. This is a definition break, not a 15 basis-point tightening observation that may be compared mechanically with `-0.1%` across a five-day window.

## Official series identity

The exact v2 route is:

```text
https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.JP?format=csv&startPeriod={YYYY-MM-DD}&endPeriod={YYYY-MM-DD}
```

The path is a data query in `dataflow` context, agency `BIS`, dataflow `WS_CBPOL`, version `1.0`, key `D.JP`. The referenced data structure is `BIS:BIS_CBPOL(1.0)`. Its key dimensions are frequency then reference area; `TIME_PERIOD` is the observation dimension. The official portal identifier is [`BIS,WS_CBPOL,1.0/D.JP`](https://data.bis.org/topics/CBPOL/BIS%2CWS_CBPOL%2C1.0/D.JP). Query behavior and time filters are documented in the [BIS v2 API documentation](https://stats.bis.org/api-doc/v2/).

A bounded live query for 20–21 March 2024 returned HTTP 200 without a redirect and `Content-Type: text/csv; charset=UTF-8`. Its witnessed series metadata was:

| Field | Required value | Meaning |
|---|---|---|
| `FREQ` | `D` | Daily |
| `REF_AREA` | `JP` | Japan; map explicitly to JPY |
| `UNIT_MEASURE` | `368` | Per cent per year |
| `UNIT_MULT` | `0` | Units; do not rescale |
| `TIME_FORMAT` | blank | Preserve and validate the witnessed blank value |
| `DECIMALS` | `4` | Display precision metadata, not measurement accuracy |
| `SOURCE_REF` | `Bank of Japan` | First-party national source named by BIS |
| `TITLE` | `Central bank policy rates - Japan - Daily - End of period` | End-of-period policy-marker series |
| `OBS_STATUS` | `A` | Normal value in the bounded response |
| `OBS_CONF` | `F` | Free confidentiality status; it does not mean final or vintage-verified |

The current machine `COMPILATION` field is source metadata that should be pinned exactly for a capture and reviewed again when it changes. Its UTF-8 SHA-256 in that bounded response was `0475BC856E35136523426884CD40D364D369B0545F343A16F47A89A325A574B7`. It starts with the 24 September 2026 `1.25%` guideline and runs backwards to a shortened pre-30 October 2008 reference. The machine text uses abbreviations and contains editorial defects such as `31 July` without a year and `0.%` for the 19 December 2008 segment. Do not silently repair that field before hashing. Use the separately dated [BIS policy-rate documentation](https://www.bis.org/statistics/cbpol/cbpol_doc.pdf) for the complete reviewed segment registry.

The official BIS methodology says the series may splice targets, repo or discount rates; for a target band it normally publishes the midpoint. Daily observations are reported by member central banks and released by BIS around mid-week. Those general release statements do not supply an observation-specific publication time or a historical vintage. See the [BIS central-bank policy-rate overview and FAQ](https://data.bis.org/topics/CBPOL).

## Supported instrument registry

The dates and meanings below follow the current BIS documentation, with Bank of Japan decisions linked at the material framework changes. The identity column names the instrument and representation, while the dated percentage remains an annotation. A change from one point guideline to another, such as `0.25%` to `0.50%`, keeps the stable identity `BOJ_OVERNIGHT_CALL_TARGET` and remains a measurable policy-level change. Only a change of instrument, a change between point and midpoint representation, the special “effectively zero” qualifier, or an unavailable interval creates a registry boundary that blocks a cross-boundary change window.

| Inclusive dates | Strict identity | Treatment and official support |
|---|---|---|
| 1 January 1999–11 February 1999 | `BOJ_OVERNIGHT_CALL_TARGET` | Continuation of the uncollateralized overnight call-rate guideline introduced 9 September 1998; level annotation `0.25%`. The BIS documentation is the authoritative segment source. |
| 12 February 1999–10 August 2000 | **Unavailable: no quantitative target** | The Bank encouraged the call rate to move as low as possible, initially around `0.15%`, but did not set one stable quantitative target for this whole interval. Do not invent a zero-rate series. [BOJ decision, 12 February 1999](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_1999/k990212c.htm). |
| 11 August 2000–27 February 2001 | `BOJ_OVERNIGHT_CALL_TARGET` | Uncollateralized overnight call rate, average around `0.25%`. [BOJ decision, 11 August 2000](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2000/k000811.htm). |
| 28 February 2001–18 March 2001 | `BOJ_OVERNIGHT_CALL_TARGET` | Same point-guideline representation, with the level changed to average around `0.15%`. [BOJ decision, 28 February 2001](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2001/k010228a.htm). |
| 19 March 2001–8 March 2006 | **Unavailable: current-account-balance quantity target** | The operating target changed from the overnight call rate to outstanding current-account balances at the Bank. The call rate was market-determined below a lending-facility ceiling. [BOJ new procedures, 19 March 2001](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2001/k010319a.htm). |
| 9 March–13 July 2006 | `BOJ_OVERNIGHT_CALL_EFFECTIVELY_ZERO` | The Bank ended the quantity target and returned to the uncollateralized overnight call rate, initially under the distinct “effectively zero” qualifier. [BOJ decision, 9 March 2006](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2006/k060309.htm). |
| 14 July 2006–20 February 2007 | `BOJ_OVERNIGHT_CALL_TARGET` | Point guideline around `0.25%`. [BOJ decision, 14 July 2006](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2006/k060714.pdf). |
| 21 February 2007–30 October 2008 | `BOJ_OVERNIGHT_CALL_TARGET` | Same point-guideline representation, level around `0.5%`. [BOJ decision, 21 February 2007](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2007/k070221.pdf). |
| 31 October–18 December 2008 | `BOJ_OVERNIGHT_CALL_TARGET` | Same point-guideline representation, level around `0.3%`. [BOJ decision, 31 October 2008](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2008/k081031.pdf). |
| 19 December 2008–4 October 2010 | `BOJ_OVERNIGHT_CALL_TARGET` | Same point-guideline representation, level around `0.1%`. [BOJ decision, 19 December 2008](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2008/k081219.pdf). |
| 5 October 2010–3 April 2013 | `BOJ_OVERNIGHT_CALL_TARGET_MIDPOINT` | Guideline around `0–0.1%`; BIS represents the range by its `0.05%` midpoint. [BOJ comprehensive monetary easing decision, 5 October 2010](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2010/k101005.pdf). |
| 4 April 2013–20 September 2016 | **Unavailable: QQE, no single policy rate** | QQE changed the main operating target from the overnight call rate to the monetary base. The BIS documentation says “no policy rate adopted” and the API omits this interval. [BOJ QQE decision, 4 April 2013](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2013/k130404a.pdf). |
| 21 September 2016–20 March 2024 | `BOJ_SHORT_TERM_POLICY_RATE_YCC` | BIS publishes `-0.1%`, the short-term policy interest rate applied to Policy-Rate Balances under QQE with yield-curve control. The same framework targeted 10-year JGB yields around zero, but the BIS figure is the short-term balance rate. [BOJ YCC decision, 21 September 2016](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2016/k160921a.pdf). |
| 21 March–31 July 2024 | `BOJ_OVERNIGHT_CALL_TARGET_MIDPOINT` | The Bank ended negative-rate/YCC policy and made the short-term interest rate its primary tool. The guideline was `0–0.1%`, effective 21 March; BIS shows the midpoint `0.05%`. [BOJ framework change, 19 March 2024](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2024/k240319a.pdf). |
| 1 August 2024–26 January 2025 | `BOJ_OVERNIGHT_CALL_TARGET` | Point guideline around `0.25%`, effective 1 August. [BOJ decision, 31 July 2024](https://www.boj.or.jp/en/mopo/mpmdeci/state_2024/k240731a.htm). |
| 27 January–21 December 2025 | `BOJ_OVERNIGHT_CALL_TARGET` | Same point-guideline representation, level around `0.50%`. [BOJ decision, 24 January 2025](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k250124a.pdf). |
| 22 December 2025–16 June 2026 | `BOJ_OVERNIGHT_CALL_TARGET` | Same point-guideline representation, level around `0.75%`. [BOJ decision, 19 December 2025](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2025/k251219a.pdf). |
| 17 June–23 September 2026 | `BOJ_OVERNIGHT_CALL_TARGET` | Same point-guideline representation, level around `1.00%`. [BOJ decision, 16 June 2026](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260616a.pdf). |
| 24 September 2026 onward | `BOJ_OVERNIGHT_CALL_TARGET` | Same point-guideline representation, level around `1.25%` in the current BIS documentation. [BOJ decision, 18 September 2026](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918a.pdf). |

For a 1999-onward implementation, the known boundaries that suppress a cross-boundary change window are 12 February 1999, 11 August 2000, 19 March 2001, 9 March 2006, 14 July 2006, 5 October 2010, 4 April 2013, 21 September 2016, 21 March 2024 and 1 August 2024. The dated point-target changes on 28 February 2001, 21 February 2007, 31 October 2008, 19 December 2008, 27 January 2025, 22 December 2025, 17 June 2026 and 24 September 2026 are level changes within `BOJ_OVERNIGHT_CALL_TARGET`; they should remain eligible for measurement when the rest of the matched weekday window is complete.

The January 2016 decision needs separate handling. On 29 January the Bank adopted a three-tier reserve-remuneration system; `-0.1%` applied only to Policy-Rate Balances from the reserve-maintenance period beginning 16 February. Other balances earned zero or `+0.1%`, while the quantity guideline still targeted monetary-base growth. This did not create a continuous BIS policy-rate observation in the QQE gap. The BIS series begins showing `-0.1%` only when the September 2016 YCC framework explicitly names it as the short-term policy interest rate. [BOJ negative-rate decision](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2016/k160129a.pdf).

## What this marker is not

- It is not the realised uncollateralized overnight call rate. The Bank of Japan publishes that traded market statistic separately, with provisional results for the same business day and final results for the prior business day. See [BOJ Call Money Market Data](https://www.boj.or.jp/en/statistics/market/short/mutan/index.htm).
- It is not broker carry or a tradable USD/JPY roll. Carry depends on the two currencies' funding instruments, tenor, forward points, basis, broker convention, costs and trade direction.
- It is not the Japan two-year sovereign yield and therefore cannot replace the existing US–Japan two-year spread.
- It is not an announcement surprise. `TIME_PERIOD` is an end-of-period reference/effective date. For example, the 19 March 2024 decision became effective on 21 March, and the 31 July decision became effective on 1 August.
- It is not a stable economic object across the registry boundaries. A numerical change caused by moving from the Policy-Rate Balance rate to a target-band midpoint must not be treated as ordinary policy momentum.

The separate BOJ traded-rate publication confirms why this distinction matters: after the March 2024 change, actual overnight call rates traded around `0.075–0.080%`, while the BIS policy marker was the target-band midpoint `0.05%`. They answer different questions.

## Strict R2 mapping recommendation

1. Extend the existing seven-leg method as a new version. Preserve exact reproducibility of the original seven-currency v1 audit; do not silently change its cohort or method label when adding JPY.
2. Add only `JPY -> JP`, source `Bank of Japan`, and the exact daily key `D.JP`. Require the existing CSV header, `UNIT_MEASURE=368`, `UNIT_MULT=0`, `DECIMALS=4`, `OBS_CONF=F`, source and title values witnessed above.
3. Pin the raw `COMPILATION` value or its UTF-8 fingerprint per receipt. Treat a changed fingerprint as source-definition drift requiring review. Keep the dated BIS PDF segment registry as a separate semantic control.
4. Make unavailable intervals explicit with a nullable identity. The current “latest start wins” registry shape cannot represent a gap safely unless it can return `None`; otherwise it would carry the prior call-rate identity through quantity-target periods.
5. Block the five-FX-weekday change whenever either endpoint or any intervening weekday changes instrument or representation, lands in a nullable interval, lacks a same-date value, or uses a different stable identity. Do not forward-fill source gaps. Do not block a window solely because the level changed while `BOJ_OVERNIGHT_CALL_TARGET` remained the identity; that level change is the policy movement the feature is meant to measure.
6. For 21 March–31 July 2024, label the BIS value `BOJ_OVERNIGHT_CALL_TARGET_MIDPOINT`, not `BOJ_ACTUAL_UOCR`. Keep the target range `0–0.1%` in metadata so `0.05%` is not mistaken for an explicitly announced point target. Treat the 21 March 2024 switch from `BOJ_SHORT_TERM_POLICY_RATE_YCC` and the 1 August switch from midpoint to point-target representation as break windows.
7. Retain `RETROSPECTIVE_ONLY`, historical availability `UNKNOWN`, historical vintage `UNKNOWN`, and forecast qualification `UNQUALIFIED` on every JPY-derived value.

## Evidence still required before predictive use

This source review does not establish that the marker improves USD/JPY forecasts. A predictive fundamentals trial still needs:

- immutable point-in-time captures showing when each BIS value and metadata version actually arrived;
- decision announcement timestamps and effective dates aligned to the trading clock;
- a separately sourced, vintage-safe US leg on matched dates;
- actual overnight call rates if the research question concerns implementation or market transmission;
- point-in-time two-year JGB and Treasury yields if the feature is a two-year spread;
- executable forward points, funding/broker conventions, basis and costs if the claim concerns carry;
- a predeclared rule for gaps, definition breaks and policy-event windows;
- frozen out-of-sample evaluation against the two-to-five-day outcome contract, including abstentions, costs, overlapping observations and uncertainty.

Until that evidence exists, the JPY series can document policy regimes and retrospective policy-marker differences. It cannot support a calibrated probability, causal claim, ranking improvement or current trade conclusion.
