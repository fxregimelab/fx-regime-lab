# FX Regime Lab: Master Implementation Plan

This document outlines the hyper-detailed, phase-by-phase execution plan to upgrade FX Regime Lab into a top-tier Institutional Research Context Engine. 

*Current Focus:* **Pillar 2 - Regime-Conditioned Event Risk Engine**

---

## 🏛️ Pillar 2: The Event Risk Radar & Asymmetry Trade

**Objective:** Replace the generic macro calendar with a predictive, regime-aware execution tool. It calculates the statistical probability of Directional Asymmetry (Beats vs. Misses) and Maximum Intraday Excursion (MIE) normalized by Realized Volatility, guiding traders on whether to front-run, fade, or avoid specific macroeconomic releases.

### Phase 2.1: The $0 Institutional Data Foundation (Python Backend)
**Goal:** Acquire 20 years of historical "Consensus vs. Actual" economic data and establish a live weekly feed for current forecasts without relying on expensive premium APIs.

*   **Task 2.1.1: Database Schema for Historical Surprises (`supabase/migrations/`)**
    *   *Action:* Create a new table: `historical_macro_surprises`.
    *   *Schema:* `id`, `event_name` (Standardized, e.g., 'US CPI YoY'), `date` (DATE), `time` (TEXT), `actual` (FLOAT), `consensus` (FLOAT), `previous` (FLOAT), `surprise_bps` (FLOAT: `actual - consensus`), `surprise_direction` (TEXT: `BEAT`, `MISS`, `IN-LINE`), `created_at`.
    *   *Security:* Enable RLS. Add explicit `FOR INSERT/UPDATE/DELETE TO anon USING (false)`.
*   **Task 2.1.2: One-Time Deep History Seeding (`pipeline/seed_macro_history.py`)**
    *   *Action:* Create a standalone script to ingest a massive, free CSV dump (e.g., from Kaggle or an Investing.com scrape provided locally).
    *   *Logic:* Map varying event names in the CSV to our standardized `_HIGH_MAP` names in `macro_calendar.py`. Calculate the `surprise_bps` and `surprise_direction`. Batch-insert the 20-year history into `historical_macro_surprises`.
*   **Task 2.1.3: Live Weekly XML Scraper (`pipeline/src/fetchers/macro_calendar.py`)**
    *   *Action:* Overhaul `fetch_macro_events` to abandon FRED for high-impact events. Implement a robust XML/JSON parser for a free tier provider (e.g., ForexFactory's weekly XML feed or a similar reliable free source).
    *   *Logic:* Fetch the upcoming week's events, including the `consensus` (Forecast) and `previous` values. Normalize the event names to our standard mapping.

### Phase 2.2: The Vol-Adjusted Asymmetry Engine (Python Pipeline)
**Goal:** Mathematically process the historical surprises against the active regime to discover executable asymmetric trades.

*   **Task 2.2.1: Database Schema for Pre-Computed Risk Matrices**
    *   *Action:* Create `event_risk_matrices` table (`date`, `pair`, `event_name`, `active_regime`, `sample_size` (INT), `median_mie_multiplier` (FLOAT), `beat_median_return` (FLOAT), `miss_median_return` (FLOAT), `asymmetry_ratio` (FLOAT), `asymmetry_direction` (TEXT), `ai_context` (TEXT)).
    *   *Action:* [Security] Enforce strict RLS policies blocking anon writes.
*   **Task 2.2.2: Maximum Intraday Excursion (MIE) Calculation (`pipeline/src/analysis/event_risk.py`)**
    *   *Action:* Create the new batch processing module.
    *   *Logic:* For a given historical date, fetch the `High`, `Low`, and `Open` of the daily spot bar. Calculate `MIE = max(abs(High - Open), abs(Low - Open))`.
    *   *Vol-Adjustment:* Divide the `MIE` by the `realized_vol_20d` *on that specific historical date*. Output the `MIE_Multiplier` (e.g., 2.5x RV20).
*   **Task 2.2.3: Regime-Conditioned Asymmetry Math (`pipeline/src/analysis/event_risk.py`)**
    *   *Action:* For an upcoming event (e.g., US CPI) and today's active regime (e.g., `USD_STRENGTH`), scan `historical_macro_surprises`.
    *   *Logic:* Filter for past CPI releases that occurred *only* during `USD_STRENGTH`. Split the results into `BEAT` and `MISS` buckets.
    *   *Math:* Calculate the median T+1 return for `BEAT` and `MISS`. Calculate the `Asymmetry_Ratio = abs(Median_Beat_Return) / abs(Median_Miss_Return)`.
*   **Task 2.2.4: [CRO Requirement] Sample Size Failsafe (`pipeline/src/analysis/event_risk.py`)**
    *   *Action:* If the total sample size (`N`) for the specific Regime + Event combination is `< 5`, set `beat_median_return`, `miss_median_return`, and `asymmetry_ratio` to `NULL`. The engine must only output the Unconditional Volatility Profile (`median_mie_multiplier`).

### Phase 2.3: Weekend Batch Processing & AI Context (Orchestration)
**Goal:** Calculate the matrices offline to protect daily pipeline latency and generate institutional execution notes.

*   **Task 2.3.1: The Weekly Orchestrator Update (`pipeline/src/scheduler/orchestrator.py`)**
    *   *Action:* Integrate `event_risk.py` into the `run_weekly()` execution path.
    *   *Logic:* Every Sunday, fetch the live upcoming week's calendar (Task 2.1.3). For every `HIGH` impact event, run the Vol-Adjusted Asymmetry Math (Task 2.2.3) against all 3 pairs and their *current* active regimes.
*   **Task 2.3.2: Execution-Oriented AI Briefs (`pipeline/src/ai/client.py`)**
    *   *Action:* Refactor `generate_event_brief` to consume the calculated `event_risk_matrices`.
    *   *Prompt:* Force a strict JSON output: `{"volatility_profile": str, "asymmetric_setup": str, "execution_note": str}`.
    *   *Constraints:* Instruct the LLM: "If sample size is < 5, state 'Insufficient historical regime data. Expect X multiplier volatility expansion.' Do not invent directional bias."

### Phase 2.4: The Institutional Interface (Next.js)
**Goal:** Replace the standard calendar with the "Event Risk Radar," visually highlighting asymmetric execution setups and suppressing low-sample-size noise.

*   **Task 2.4.1: Database Query Layer (`web/src/lib/queries.ts`)**
    *   *Action:* Add `useEventRiskMatrices(pair)` fetching the pre-computed week's data from `event_risk_matrices`. Use `staleTime: Infinity` (it's a weekly batch job).
*   **Task 2.4.2: The Event Risk Radar Component (`web/src/app/calendar/page.tsx` & `web/src/components/ui/event-radar.tsx`)**
    *   *Action:* Completely re-architect the Calendar tab.
    *   *Visual Hierarchy:* Display the upcoming events as a dense table. Instead of generic "High Impact" flags, display the `MIE_Multiplier` (e.g., `[ 2.4x RV20 ]`).
*   **Task 2.4.3: The Asymmetry Badge UI**
    *   *Action:* If `asymmetry_ratio > 2.0` AND `sample_size >= 5`, render a glowing, high-contrast badge next to the event: `[ ASYMMETRIC RISK: {asymmetry_direction} ]`.
*   **Task 2.4.4: The Institutional Tear Sheet Modal**
    *   *Action:* Clicking an event row opens a sliding modal (or expandable row) detailing the exact math.
    *   *Content:* Display the Median Beat Return vs. Median Miss Return. Display the AI `execution_note`. If `sample_size < 5`, prominently display a `[ LOW CONFIDENCE SAMPLE (N={sample_size}) ]` warning to prevent cognitive bias.

---
*End of Pillar 2 Plan.*