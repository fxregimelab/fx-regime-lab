# FX Regime Lab: Bug & Vulnerability Report

This file logs all identified bugs, architectural flaws, and optimization opportunities discovered during the Deep System Audit. 
**Rule:** Do NOT implement fixes during the audit phase. Log, categorize, and define the solution blueprint here.

## 🔴 High Severity (Data Loss, Crash, Security)
| ID | Phase | Component/File | Bug Description | Root Cause | Proposed Solution | Status |
|---|---|---|---|---|---|---|
| 1.1 | P1 | `ai/client.py` | Model Fallback Exhaustion | `_call` loop iterates through models and raises `RuntimeError` immediately if all fail. Given OpenRouter 429s, this guarantees pipeline crash on busy days. | Implement an outer retry loop with exponential backoff (e.g., wait 5s, 15s) before completely failing. | OPEN |
| 1.2 | P1 | `fetchers/cot.py` | Hardcoded Year in Sources | The `sources` list hardcodes `fut_fin_txt_2025.zip` and `deacot2025.txt` alongside dynamic year. In 2026, if dynamic fails, fallback is stale data. | Change fallback year to use `date.today().year - 1` or remove static year references. | OPEN |
| 3.1 | P3 | `migrations/*` | RLS Leakage / Data Mutation Risk | RLS is enabled and `SELECT` is restricted, but there are no `INSERT`/`UPDATE`/`DELETE` policies explicitly blocking `anon` or `authenticated` roles from writing to the tables if keys are exposed. | Add explicit `FOR ALL TO anon, authenticated USING (false)` policies, or rely strictly on Service Role bypass. | OPEN |
| 4.1 | P4 | `web/src/app/` | Missing Error Boundaries | The Next.js `app/` router root lacks an `error.tsx` and `global-error.tsx`. | An uncaught client-side exception (like a null pointer in the Lightweight Charts mapping) will unmount the entire React tree and show a generic 500 overlay. | Create custom `error.tsx` shells that fit the terminal aesthetic. | OPEN |

## 🟡 Medium Severity (UI Breakage, Silent Fails, Inefficiencies)
| ID | Phase | Component/File | Bug Description | Root Cause | Proposed Solution | Status |
|---|---|---|---|---|---|---|
| 1.3 | P1 | `fetchers/macro_calendar.py` | Missing Non-US FRED Events | `_HIGH_MAP` only maps US events. `_fred_fetch` relies on this map. ECB/BoJ/RBI rely completely on static fallback `_cb_meetings`. | Expand `_HIGH_MAP` to include major EU, JP, IN macro keywords or rely entirely on static CB dates for all. | OPEN |
| 1.4 | P1 | `fetchers/cross_asset.py` | Potential `None` returned on empty arrays | `_latest_and_change_1d` returns `None` if `close_series` is empty. The caller does not handle `None` gracefully if dependent downstream. | Ensure robust `None` handling downstream or fallback to historical tables. | OPEN |
| 2.1 | P2 | `validation/backtest.py` | Validation Date Misalignment | `call_idx` fallback uses `len(bars_sorted) - 2` when `prior_call.date` is missing. | Find the closest following date instead of a hardcoded offset, or mark the call as un-validated until a match is found. | OPEN |
| 2.2 | P2 | `regime/composite.py` | Primary Driver Misattribution | `get_primary_driver` returns "Rate differential" even if all signals are `0.0`. | Add a minimum absolute threshold (e.g., `0.1`) before attributing dominance; otherwise, return "Mixed signals". | OPEN |
| 3.2 | P3 | `db/writer.py` | Race Condition in AI Usage Log | `get_ai_request_count_today` reads the count, and `write_ai_request` inserts a new row. If multiple AI requests fire concurrently, the limit check may pass erroneously. | Use a Supabase RPC function with an atomic increment/check, or accept slight limit overruns. | OPEN |
| 4.2 | P4 | `app/terminal/fx-regime/[pair]/page.tsx` | Mobile Viewport Trap | Terminal uses a hardcoded `calc(100vh - 66px)` lock. On mobile screens (`< xl`), the flex grid collapses vertically but remains locked inside this 100vh box. | This forces ugly nested scrolling inside panes. Use `md:h-[calc(100vh-...)]` and allow native scroll on mobile, or redesign the mobile terminal shell. | OPEN |
| 5.1 | P5 | `pyproject.toml` | CI Container Bloat | Development dependencies (`pytest`, `mypy`, `ruff`, `pre-commit`) are listed in the main `dependencies` block. | `pip install .` on the runner wastes time resolving/downloading megabytes of linting tools. Move them to `[project.optional-dependencies]`. | OPEN |

## 🔵 Low Severity / Optimization (Refactoring, Speed, UX)
| ID | Phase | Component/File | Bug Description | Root Cause | Proposed Solution | Status |
|---|---|---|---|---|---|---|
| 1.5 | P1 | `fetchers/yields.py` | Synchronous Sleep on YF | `_fetch_yf_legs` loops and sleeps 1.0s per ticker. | Batch download via `yf.download(list_of_tickers)` to save time. | OPEN |
| 1.6 | P1 | `fetchers/open_interest.py` | CME 403 Retry Logic | Only 1 retry (2 attempts) after a 2.0s sleep. Might not be enough for CME anti-bot systems. | Increase retry count or use a rotating user-agent strategy if 403s persist. | OPEN |
| 2.3 | P2 | `signals/rate.py` | Normalization Lookback Horizon | `normalize_rate_signal` calculates Z-score over the given array (typically 1y). This may not capture multi-year regime shifts. | Expand historical array fetched from the database to 3-5 years for a more robust structural mean/variance. | OPEN |
| 3.3 | P3 | `migrations/*` | Indexing Inefficiency | Indexes exist for `(pair, date DESC)`, but queries often filter by `pair` and a specific date range without `ORDER BY DESC` initially. | Ensure compound indexes precisely match the most frequent query patterns from `queries.ts`. | OPEN |
| 4.3 | P4 | `lib/queries.ts` | Massive Supabase Data Over-Fetching | `providers.tsx` sets global `staleTime: 60 * 1000`. If a user navigates between pairs, `useHistoricalData` (25k rows) will invalidate and refetch every minute. | Set `staleTime: 1000 * 60 * 60 * 24` (24h) or `Infinity` specifically for deep history hooks since historical archives don't change intra-day. | OPEN |
