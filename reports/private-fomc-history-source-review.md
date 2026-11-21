# Independent source review: implemented FOMC history

**Review date:** 2026-10-02  
**Decision:** **PASS — BOUNDED SOURCE RECONSTRUCTION**  
**Continuing hold:** original-release vintage, historical receipt, expectations, surprise, causal impact, execution, forecast qualification, and strategy qualification remain unavailable.

This review is read-only. It covers the official-source inventory and its saved reconstruction. It does not review the later FX outcome study or qualify a trading result.

## Bound evidence

| Artifact | SHA-256 | Bytes |
|---|---:|---:|
| `docs/PRIVATE_FOMC_HISTORY_CONTRACT.md` | `c9446460881dc0c3ab109df32696e2cc161df6cbc0dc7aa3355584cc4a28e50d` | 6,278 |
| `pipeline/src/private_desk/fomc_history.py` | `f2fe049afdee0c3e2a11149a19a429bda9bf38c5da36e314490264b904d8d745` | 19,297 |
| `.private-fx/fomc-history/evidence.json` | `d1522ba96513670ed80169c171cf7303775bc03a60eb677330e6c244956ae24b` | 273,118 |

I decoded and hashed every referenced receipt and original body. All **8 index receipts** and **84 statement receipts** equal their manifest records; all 92 body files match their saved byte lengths and SHA-256 values, report HTTP 200, complete bodies, and HTML media. Two deterministic set bindings provide a compact check over those originals:

- sorted `index URL|body SHA-256` set: `6d250c4cbae534186a6270aca235b01f286b87cf64ad40d8d028dc35d8150593`
- sorted `statement URL|body SHA-256` set: `f2e8a684e8536cfb55b26f783390cfe08a49588c3cd7e0955f2fc5db0df65b7d`

The saved 83-row event semantics—date, class, source clock, bounds, predecessor, change, and body hash—have aggregate SHA-256 `eb77cd1905dfea92b6bb8785543a7f5980e5168ff28f8d2fccc7878712e3cd5e`.

## Independent inventory result

I enumerated the links again from the captured official index HTML rather than trusting `evidence.json`'s saved discovery list. Exact visible `Statement` links reproduce **83 statements for 2015–2024**, with yearly counts:

```text
2015  8    2016  8    2017  8    2018  8    2019  9
2020 10    2021  8    2022  8    2023  8    2024  8
```

The captured [2014 historical index](https://www.federalreserve.gov/monetarypolicy/fomchistorical2014.htm) independently supplies the required [2014-12-17 predecessor](https://www.federalreserve.gov/newsevents/pressreleases/monetary20141217a.htm). Its captured body hash is `2f219e22e84b240ad257098e758c8e6a70421568c8a983c511b84cff631e49db`; it states a 0–0.25 percent target range and is date-only. It is used as the seed and correctly omitted from the 83 in-scope events.

The index originals preserve the important calendar distinctions:

- [2019-10-11](https://www.federalreserve.gov/newsevents/pressreleases/monetary20191011a.htm) belongs to the **October 4 unscheduled** meeting heading.
- [2020-03-03](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200303a.htm) belongs to the **March 2 unscheduled** meeting. The implementation preserves meeting date and publication date separately.
- [2020-03-15](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm) is the Sunday unscheduled decision.
- [2020-03-23](https://www.federalreserve.gov/newsevents/pressreleases/monetary20200323a.htm) is a notation-vote statement.
- The March 17–18, 2020 heading says **cancelled** and has no Statement link. It remains an index exception rather than an invented event.

No expected link is absent, no extra link enters the bounded period, and `failures` is empty.

## Body, authority, and target findings

I inspected all 83 captured statement bodies against their saved events. Every saved title and decision paragraph is present in its bound original body. The classes are:

| Class | Count | Review finding |
|---|---:|---|
| `TARGET_DECISION` | 81 | Committee decision or reaffirmation paragraph supplies the target range. |
| `IMPLEMENTATION_ONLY_NO_STANCE_CHANGE` | 1 | 2019-10-11; no target decision is emitted. |
| `OTHER_POLICY_STATEMENT` | 1 | 2020-03-23; no target decision is emitted. |

Twenty captured bodies include dissent language. The stored range always comes from the Committee's own decision paragraph, which is retained verbatim as an original-body paragraph. None of those stored decision paragraphs contains `Voting against` or `directs the Desk`. This matters on March 15, 2020: the Committee's 0–0.25 percent decision is retained, while the dissent's preferred 0.50–0.75 percent range is not selected.

The two non-target rows also fail safely:

- The October 11, 2019 page restates 1.75–2.00 percent inside an operating directive and explicitly says its measures do not change the stance. Its target fields and change remain null.
- The March 23, 2020 page restates 0–0.25 percent in a Desk directive while announcing asset-purchase action. Its target fields and change remain null.

Recomputing adjacent midpoint differences from the 81 target decisions and the seed gives **28 announced target-range changes**, on:

```text
2015-12-16
2016-12-14
2017-03-15  2017-06-14  2017-12-13
2018-03-21  2018-06-13  2018-09-26  2018-12-19
2019-07-31  2019-09-18  2019-10-30
2020-03-03  2020-03-15
2022-03-16  2022-05-04  2022-06-15  2022-07-27
2022-09-21  2022-11-02  2022-12-14
2023-02-01  2023-03-22  2023-05-03  2023-07-26
2024-09-18  2024-11-07  2024-12-18
```

This is an announced midpoint-change count. It is not a count of unexpected decisions or causal shocks.

## Clock review

The 83 events contain **75 exact source-stated clocks** and **8 date-only observations**. All eight date-only rows are the 2015 statements, whose captured pages say `For immediate release` and do not state a clock or timezone. Their `source_stated_release_at` values are correctly null. The 2014 seed is also date-only but is outside the count.

The nonstandard exact clocks and UTC conversions match the original pages:

| Release | Source line | Stored UTC |
|---|---|---|
| 2019-10-11 | 11:00 a.m. EDT | 15:00 |
| 2020-03-03 | 10:00 a.m. EST | 15:00 |
| 2020-03-15 | 5:00 p.m. EDT | 21:00 |
| 2020-03-23 | 8:00 a.m. EDT | 12:00 |

The March 15 event is correctly retained as a Sunday release. The code uses the literal EST/EDT token and rejects a token that conflicts with New York daylight-saving time.

The saved `source_release_line` includes the adjacent page control word `Share` after the policy text. This does not alter the strict clock match, UTC value, or date-only classification. It should not be described as a byte-exact reproduction of the visual line.

## Predecessor and failure behavior

The successful evidence chain is exact:

- 2015-01-28 points to the 2014-12-17 seed.
- 2019-10-11 does not reset the target predecessor; 2019-10-30 points to 2019-09-18.
- 2020-03-23 does not reset it; 2020-04-29 points to 2020-03-15.
- Every other target decision points to the immediately preceding captured target decision.

The implementation also fails closed when a target decision is missing or cannot be parsed. In `audit_history`, any such exception records a failure, clears `previous`, and skips the row. The next successfully parsed target decision therefore has no predecessor and no change. Once that row is admitted, later targets may use it as the new baseline. The two known non-target dates are the only exceptions to clearing `previous`, which matches their fixed source classification. Current evidence contains no failed capture, so this last conclusion is a code-path review rather than an observed failure in this source set.

## Claims that remain unavailable

The implementation does not convert the current archive into historical point-in-time evidence. All 83 rows have:

- `historical_receipt_at = null`
- `actual_transmission_at = null`
- `effective_policy_date = null`
- `archival_revision_status = UNKNOWN`
- `consensus = null`
- `surprise = null`
- `forecast_qualification = UNQUALIFIED`

The top-level evidence repeats `historical_availability = UNKNOWN` and `forecast_qualification = UNQUALIFIED`. Capture receipt times are from 2026-10-01 and prove only when these current official archive bytes were saved. They do not prove the original-release bytes or their historical arrival. The target midpoint is kept separate from an effective overnight rate, funding cost, yield, carry measure, prior expectation, and causal effect.

## Decision

**PASS — BOUNDED SOURCE RECONSTRUCTION.** The saved evidence is complete and internally immutable for the captured official archive state: 83 independently reproduced statements, one separately captured seed, 28 target changes, 75 exact clocks, eight date-only events, correct Committee authority, and correct non-target handling.

**HOLD** any claim of original-vintage text, historical receipt, market surprise, expectation error, causal impact, executable timing, predictive validity, current forecast, or strategy qualification. Those claims require evidence that is deliberately absent here.
