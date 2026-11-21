# D04 independent review — 30 September 2026

Verdict: **partial local repair; D04 remains IN PROGRESS**. The revised fetcher combines four yearly financial-futures archives with the weekly file, deduplicates equal pair/report dates, rejects conflicting duplicates, and requires at least 156 distinct dates per pair. The January fixture and direct checks pass. Sampled source, test, gate, and report hashes match the D04 packet.

Independent checks: 38 focused tests passed, 2,047 full pipeline tests passed, Ruff passed, MyPy passed on 232 source files. No live CFTC request or production write was made. The five Unlazy gates have manual checkmarks and no runnable `CHECK:` lines; `gate-lint` warns that 0/5 gates are runnable. Their status is not automatic test evidence.

**Blocking counterexample:** Reuse the D04 fixture with 208 weekly EUR/USD dates from 2023 through December 2026, but make the entire 2025 archive unavailable. `fetch_cot(year=2026)` still returns 156 dates, with a **371-day gap** between consecutive reports and the oldest returned date in January 2023. `compute_cot_percentile` then returns `100.0`. The count gate therefore does not prove that the 156 reports form the intended recent rolling window. The fetcher logs partial coverage but still treats this broken sequence as usable.

Repair the coverage rule with an explicit, source-supported policy for weekly report continuity and permitted exceptions. Add a missing-middle-year negative fixture that makes both acquisition and the signal unavailable, while retaining the passing January, duplicate, and partial-current-year controls. Keep Tuesday report dates separate from D05 publication timing. D04 must not be marked VERIFIED LOCAL until this counterexample is rejected.
