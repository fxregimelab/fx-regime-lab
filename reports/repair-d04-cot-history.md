# D04 COT history correction — 30 September 2026

Status: **local correction ready for independent review**. D04 is not accepted or deployed. This packet changes only the four owned files. No production data, immutable ledger, or service was changed.

## Red control and cause

The review found that a failed 2025 archive could leave 156 EUR/USD reports in a 208-week fixture ending in December 2026. Those retained reports included a 371-day break, yet the downstream percentile returned 100.0. The count check in `fetch_cot` admitted old reports to fill a broken rolling window.

Before the correction, `python -m pytest tests/test_cot_fetcher_history.py -q` failed the new negative test: **1 failed, 7 passed**. The failed assertion found **156 returned rows** where an empty result was required; the captured log showed the 2025 archive failure. The existing January, duplicate, and current-year-fallback fixtures passed in that same red run.

## Coverage policy

The fetcher first deduplicates and applies the 156-distinct-report count, then checks **report dates within the selected 156 rows**. A consecutive gap over **21 calendar days** rejects that pair and logs the dates and gap. The full selected window must also span no more than **168 weeks**. A regular 156-report window spans 155 weeks, so this allows 13 additional weeks for isolated omissions or shifted dates but rejects persistently sparse coverage. The 2025 hole is thus unavailable to the acquisition caller; `compute_cot_percentile` receives no EUR/USD rows and returns `None`. A separate 14-day missing-week fixture remains usable; removing every fourth week is rejected even though no individual gap exceeds 14 days. Equal duplicates still count once, conflicting duplicates still exclude a pair, and a failed current-year archive can still be covered by the weekly file.

The CFTC describes COT as a weekly report generally based on Tuesday positions. Its [historical view](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/index.htm) says listed dates are report dates, while its [release schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm) documents holiday shifts. [Special announcements](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalSpecialAnnouncements/index.htm) show that exceptional interruptions and even non-Tuesday data dates can occur. **The 21-day and 168-week bounds are conservative local acceptance thresholds, not CFTC guarantees.** A longer legitimate interruption requires dated source evidence and a separately reviewed exception before the signal can be restored; this packet does not infer one from a failed archive. D05 separately owns release availability and publication timing.

## Scope and checks

GitNexus impact analysis before editing `fetch_cot` rated it **CRITICAL**: 63 direct graph links, 70 total impacted symbols, and seven affected flows. Broad import links contribute to that count; pipeline and backfill are among the affected paths. The code change is confined to selected-window coverage rejection.

Direct checks from `pipeline/`:

| Command | Result |
|---|---|
| `python -m pytest tests/test_cot_fetcher_history.py -q` | 9 passed in 1.92s |
| `python -m pytest tests/test_cot_fetcher_history.py tests/test_cot_signal.py tests/test_cot_category_history.py -q` | 41 passed in 1.69s |
| `python -m pytest -q` | 2050 passed in 62.01s |
| `python -m ruff check .` | All checks passed |
| `python -m mypy .` | No issues in 232 source files |

The Unlazy ledger now has five runnable `CHECK`/`EXPECT` gates and one manual report-review gate. The commands above were run directly. Automatic gate evidence is **not** claimed; the checker approval flow was not used. Gate lint and status were read without executing ledger commands.

## Owned-file SHA-256

| File | SHA-256 |
|---|---|
| `pipeline/src/fetchers/cot.py` | `63CBEF60F416E0AAB037ACDADC704D500675561F197BDAEF9246BD17DDF7751B` |
| `pipeline/tests/test_cot_fetcher_history.py` | `97931A2EAC65060353EA1AB3D29F3DCD36FAD0258DFABDF2F44BC8321769465D` |
| `.unlazy/d04/GATES.md` | `56C42347762322498A78DA4B6839ABEC13487B657C438F15495944BAEE4157AE` |
| `reports/repair-d04-cot-history.md` | Self-hash below, excluding its own hash line. |

REPORT_SELF_SHA256: F94253989C6D8D4770717A066BDB7BD6154C4D531E87AD1E52D8275EB3E6CB7C

## Remaining limits

- This is deterministic fixture evidence. No live CFTC download, archive audit, or historical completeness check was performed.
- The date bounds can reject a legitimate extended interruption. Such an exception needs dated source evidence and explicit review; it is not automatically accepted. The rule also cannot establish that the latest report is fresh for a given decision date.
- The fetcher controls rows it returns. It does not validate arbitrary rows passed directly to `compute_cot_percentile`, and it does not settle D05 publication timing.
- No commit, push, deploy, production write, or Docker/Hermes runtime startup occurred. Unrelated pre-existing workspace changes were left alone.
