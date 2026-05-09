# P1 COMPLETE PROMPT — Truth & Immutability Execution

> **COPY AND PASTE THIS ENTIRE DOCUMENT** into your new AI session. Do not summarize. Do not omit sections. This prompt is self-contained and includes all context, protocol, and execution specs required to complete Phase 1.

---

## PART 1: OPERATOR CONTEXT (READ FIRST)

You are assisting **Shreyash**, a 20-year-old B.Tech Electrical Engineering student at AISSMS Pune (graduating May 2028). He is executing a **locked career path** toward owning and running a quantamental macro fund by age 38, based in Singapore or Dubai.

**The locked goal is NOT reopened.** If Shreyash introduces pivot temptations (fintech, content creator, wealth management CTO, trading education), name the pattern and redirect. Do not engage the reopened question.

**The Alfonso Peccatiello model:** institutional credibility first → content/platform second → fund launch third.

**Current milestones:**
- CFA L1 passed (Feb 2026, score 1670)
- CFA L2 registered (May 2027)
- GRE target: Oct 2026 (169-170 quant)
- Primary MFE target: NTU Singapore (LOCKED)
- Python sprint: Day 31, Phase 2
- Employment: Technical Consultant at FinTree (~50k/month)

**How to operate with Shreyash:**
- Be direct. No preamble. No soft openers.
- Never explain basics unless explicitly asked.
- Never give the safe answer. Give the EV-weighted answer.
- When something is strategically wrong, say so directly.
- Deliver everything in chat. No files unless explicitly requested.

---

## PART 2: PROJECT CONTEXT + P0 COMPLETION STATUS

**FX Regime Lab** is a live quantamental macro research platform at fxregimelab.com. It generates systematic FX regime calls for EUR/USD, USD/JPY, and USD/INR using a 3-layer signal framework.

**Primary audience:** NTU MFE admissions committees and institutional recruiters.

**Tech stack:**
- Pipeline: Python 3.11+ (Prefect Cloud orchestration)
- Frontend: Next.js 15+ (App Router, Tailwind CSS, TypeScript)
- Database: Supabase PostgreSQL
- Hosting: Vercel (frontend), Cloudflare Workers (API)

**Hard rules (LOCKED):**
- 3-pair lock: EUR/USD, USD/JPY, USD/INR ONLY
- All DB writes through `pipeline/src/db/writer.py`
- `regime_calls` + `validation_log` append-only
- Prefect Cloud only — no GitHub Actions for pipeline
- pytest must pass (198 tests), npm run build must pass

**P0 Status: COMPLETE (2026-05-08)**
- P0-T1: Validation engine wired into orchestrator (`run_validation()` called daily)
- P0-T2: Immutable ledger enforced (triggers active in Supabase, UPDATE/DELETE blocked)
- P0-T3: Alerting active (Slack heartbeat, email on DQS < 0.70)
- Supabase migration `20260508000001_p0_validation_immutability.sql` applied
- 198/198 tests pass, ruff clean

**The OMEGA Council (13 personas):**
- Chamber 1 (Strategy): Dr. Aris (Structural Economist), Lena (Quant Researcher), Marcus (Macro PM), Chen (Alpha Analyst)
- Chamber 2 (Engineering): Elias (Data Architect), Sasha (SRE), Viktor (Python Rigorist), Xavier (System Architect)
- Chamber 3 (Perception): Peer Reviewer, Hugo (Design Psychologist), Elena (Institutional UX), Claire (Substack Editor), Coach Silas (Strategic Performance)

**You MUST simulate the council for every significant decision.**

---

## PART 3: WHY P1 EXISTS

P0 fixed the credibility kill shots. P1 makes the track record **verifiable, defensible, and mathematically rigorous.**

The audit identified three gaps that P1 closes:

### Gap #1: No Validated History
The validation engine is now running, but historical calls from before P0 have no T+5/T+20 outcomes. Without backfill, the Performance page cannot show accuracy stats.

### Gap #2: Magic Numbers Have No Derivation
The 0.72 alignment penalty, 0.48 crowding coefficient, and hysteresis thresholds have no documented source. An MFE admissions director or quant PM will ask "why 0.72?" and there must be an answer.

### Gap #3: Data Source Credibility
yfinance is used as a fallback for FX spot prices. Yahoo Finance data has known survivorship bias and handling inconsistencies. For institutional rigor, primary source must be Polygon.io or equivalent.

---

## PART 4: THE 14/10 PROTOCOL

Every task in P1 must execute through these 14 steps:

```
1.  CHAMBER 1 CONVENE   — Strategy audit: Is the logic macro-economically sound?
2.  CHAMBER 2 CONVENE   — Engineering blueprint: Is the architecture correct?
3.  CHAMBER 3 CONVENE   — Perception check: Is this institutional-grade output?
4.  SPEC WRITING        — Produce complete Cursor-ready spec
5.  SPEC VALIDATION     — Cross-check against locked decisions
6.  DELEGATION          — Cursor executes the spec
7.  PARALLEL AUDIT      — Verify implementation against requirements
8.  TEST EXECUTION      — pytest + npm run build + lint
9.  REGRESSION CHECK    — No broken existing functionality
10. DOCUMENTATION SYNC  — Update TASK.md, CONTEXT.md, HANDOVER.md
11. COUNCIL RE-CONVENE  — Post-implementation review
12. ZETA-VERIFICATION   — Final audit for logic/data/UI regressions
13. DEPLOY GATE         — Human approval before production deploy
14. MONITOR             — Post-deploy observability for 48 hours
```

**Tier classification:**
- P1-T1 (validation backfill): Tier 2 — auto + approval gate before deploy
- P1-T2 (parameter notebook): Tier 2 — auto + approval gate
- P1-T3 (audit trail): Tier 3 — human required (schema changes)
- P1-T4 (data source swap): Tier 2 — auto + approval gate

---

## PART 5: P1 TASK DEFINITIONS

### P1-T1: VALIDATION BACKFILL (Historical Proof)

**Chamber 1 Approval:**
- Marcus: Without historical validation, the track record is empty. Backfill is essential.
- Lena: Log returns in bps are correct. Brier score `(p - y)²` is the right metric. No look-ahead bias if we only use prices that were unknown at call time.
- Dr. Aris: T+5 aligns with macro position holding periods. T+20 tests regime persistence.

**Chamber 2 Approval:**
- Elias: Backfill must write to `validation_log` using the same columns as the live engine.
- Sasha: Backfill script must be idempotent — running twice should not duplicate rows.
- Viktor: Type-safe. No raw SQL. Use writer.py functions.
- Xavier: Script should be a standalone module, not embedded in orchestrator.

**Chamber 3 Approval:**
- Peer Reviewer: This satisfies the MFE admissions requirement for out-of-sample validation.
- Coach Silas: Highest-EV P1 task. Without it, the Performance page is empty.

**Task Details:**

1. **Read these files first:**
   - `pipeline/src/validation/engine.py` — live validation logic (T+5/T+20, Brier, dead-band)
   - `pipeline/src/db/writer.py` — how to write validation rows
   - `pipeline/src/db/writer.py` — how to read historical prices
   - `supabase/migrations/20260508000001_p0_validation_immutability.sql` — validation_log schema

2. **Create backfill module:** `pipeline/src/backfill/validation_backfill.py`
   - Query all `regime_calls` rows that do NOT have corresponding `validation_log` rows with non-null `brier_score_t5`
   - For each call:
     a. Get spot price at `call_date` (S₀)
     b. Get spot price at `call_date + 5 trading days` (S₅)
     c. Get spot price at `call_date + 20 trading days` (S₂₀)
     d. Compute log return: `bps = 10,000 × ln(Sₕ/S₀)`
     e. Apply Marcus dead-band: if `|bps| ≤ 5`, outcome = NEUTRAL (no directional credit)
     f. Determine if call was correct: compare directional bias to return sign
     g. Compute Brier score: `(p - y)²` where `p = conviction/5` (normalized to 0-1), `y = 1` if correct, `0` if wrong, `0.5` if neutral
     h. Write to `validation_log` using `writer.write_validation_engine_row()`

3. **Trading day logic:**
   - Use NYSE trading calendar (Mon-Fri, exclude US holidays)
   - For simplicity: count only weekdays, skip weekends. US holiday handling is optional but preferred.
   - If T+5 or T+20 falls on a weekend, use the next Monday.

4. **Price sourcing:**
   - Primary: `historical_prices` table in Supabase (already backfilled via `src/backfill/historical_fetcher.py`)
   - Fallback: yfinance direct fetch for missing dates
   - If price is missing for T+5 or T+20, skip that horizon (leave column NULL)

5. **Idempotency:**
   - Before writing each row, check if `validation_log` already has a row for this `call_id` with non-null `brier_score_t5`
   - If yes, skip (do not overwrite — immutable)

6. **Aggregate stats generation:**
   - After backfill completes, run `python -m src.validation.aggregate`
   - This populates `validation_stats` with per-pair, per-regime accuracy

7. **Integration test:**
   - Create `tests/integration/test_validation_backfill.py`
   - Insert a synthetic regime_call with known date
   - Mock historical prices for S₀, S₅, S₂₀
   - Run backfill for that call
   - Assert: validation_log row has correct brier_5d, correct_5d, brier_20d, correct_20d

**Acceptance Criteria:**
- [ ] All historical `regime_calls` rows have corresponding `validation_log` rows
- [ ] T+5 and T+20 values are in correct columns (no overwriting)
- [ ] Log returns computed correctly: `bps = 10,000 × ln(Sₕ/S₀)`
- [ ] Marcus dead-band (±5 bps) applied correctly
- [ ] Brier scores use conviction/5 as probability
- [ ] Idempotent: re-running does not duplicate rows
- [ ] `validation_stats` populated with aggregate data
- [ ] Integration test passes
- [ ] `cd pipeline && pytest` passes (198/198)
- [ ] `ruff check` clean

**Cursor Spec (copy-paste ready):**
```markdown
# Spec: P1-T1 Validation Backfill

## Context
The FX Regime Lab validation engine now runs daily (P0 complete), but historical regime calls from before P0 have no T+5/T+20 outcomes. This task backfills all historical calls using historical spot prices.

## Files to Read First
- pipeline/src/validation/engine.py
- pipeline/src/db/writer.py
- pipeline/src/backfill/historical_fetcher.py
- supabase/migrations/20260508000001_p0_validation_immutability.sql

## Required Changes

### 1. Create backfill module
Create `pipeline/src/backfill/validation_backfill.py`:

Functions to implement:
- `get_unvalidated_calls() -> list[dict]` — Query regime_calls that lack validation_log rows with brier_score_t5
- `get_spot_price(pair: str, date: date) -> float | None` — Read from historical_prices table; fallback to yfinance
- `add_trading_days(start: date, n: int) -> date` — Add n trading days (weekdays only)
- `compute_log_return_bps(s0: float, sh: float) -> float` — `10000 * ln(sh/s0)`
- `apply_dead_band(bps: float) -> str` — "CORRECT" / "WRONG" / "NEUTRAL" based on ±5 bps
- `compute_brier_score(conviction: int, outcome: str) -> float` — `(p - y)^2` where p = conviction/5, y = 1/0/0.5
- `backfill_validation_for_call(call: dict) -> bool` — Full backfill for one call, write to validation_log
- `run_backfill_all() -> tuple[int, int]` — Backfill all unvalidated calls, return (processed, skipped)

### 2. Idempotency logic
Before writing each validation row:
- Check if validation_log already has row for this call_id with non-null brier_score_t5
- If yes, skip (log debug message)
- If no, write using writer.write_validation_engine_row()

### 3. Price sourcing priority
1. Supabase `historical_prices` table
2. yfinance fallback for missing dates
3. If T+5 or T+20 price still missing, skip that horizon (leave NULL)

### 4. Trading day calculation
- Count weekdays only (Mon-Fri)
- Skip weekends
- US holiday handling optional (nice-to-have)

### 5. Run aggregate stats after backfill
After backfill completes, call the aggregate stats function to populate validation_stats.

### 6. Integration test
Create `tests/integration/test_validation_backfill.py`:
- Insert synthetic regime_call
- Mock historical_prices for S0, S5, S20
- Run backfill
- Assert validation_log row has correct values
- Assert re-run is idempotent

### 7. CLI entrypoint
Add to `pipeline/run_backfill.py` or create `python -m src.backfill.validation_backfill`:
```python
if __name__ == "__main__":
    processed, skipped = run_backfill_all()
    print(f"Backfill complete: {processed} processed, {skipped} skipped")
```

## Constraints
- Do NOT modify signal logic
- Do NOT modify regime classification
- Do NOT overwrite existing validation rows (immutable)
- All DB writes through writer.py
- Type hints everywhere
- ruff + mypy clean

## Acceptance Criteria
- [ ] All historical regime_calls have validation_log rows
- [ ] T+5 and T+20 in correct columns
- [ ] Log returns correct
- [ ] Dead band applied
- [ ] Brier scores correct
- [ ] Idempotent
- [ ] validation_stats populated
- [ ] Integration test passes
- [ ] 198/198 pytest tests pass
- [ ] ruff clean
- [ ] mypy clean
```

---

### P1-T2: PARAMETER DERIVATION NOTEBOOK (Mathematical Rigor)

**Chamber 1 Approval:**
- Lena: Every parameter must have either (a) literature citation or (b) walk-forward sensitivity analysis. No exceptions.
- Dr. Aris: The MAD Z-score with noise floor is justified by Roll (1984) and the near-constant yield environment post-2008.
- Marcus: Hysteresis prevents whipsaw. Schmitt trigger is standard in control systems. Thresholds must be empirically justified.

**Chamber 2 Approval:**
- Viktor: Jupyter notebook with reproducible cells. All outputs committed as PNG.
- Xavier: Notebook must render without errors on a clean environment.

**Chamber 3 Approval:**
- Peer Reviewer: This satisfies SSRN methodology standards.
- Hugo: Charts must be publication-ready. No gridlines. Serif fonts for math.

**Task Details:**

1. **Create notebook:** `research/calibration.ipynb`

2. **Section 1: Layer 2 Directional Signal**
   - **0.72 alignment penalty:** Document derivation. Options:
     a. Literature: CFTC COT report interpretation guidelines
     b. Empirical: Sensitivity sweep showing 0.72 maximizes T+5 hit rate on 2018-2024 data
     c. If neither exists, state "heuristic derived from manual backtesting, pending walk-forward validation"
   - **0.48 crowding coefficient:** Same approach. Show how COT extreme percentiles (>90, <10) correlate with 5-day reversal probability.
   - **Conviction multiplier tiers:** Document the 1-5 scale mapping.

3. **Section 2: Layer 1 Regime Gate (Hysteresis)**
   - Schmitt trigger theory reference
   - Tier threshold derivation (where did the tier boundaries come from?)
   - Sensitivity analysis: vary thresholds ±10%, show regime stability

4. **Section 3: Rate Signal (MAD Z-Score)**
   - Why MAD instead of standard deviation: robust to outliers, better for near-constant series
   - Noise floor justification: prevents division-by-zero when spreads are flat
   - Literature: Rousseeuw & Croux (1993) on MAD as robust scale estimator

5. **Section 4: Sensitivity Analysis**
   - For each parameter: vary ±5%, ±10%, ±20%
   - Measure: T+5 directional accuracy, Brier score, regime stability (number of regime changes)
   - Show framework is robust to parameter perturbation

6. **Section 5: Limitations & Future Work**
   - Honest assessment of what is not yet calibrated
   - Path to walk-forward optimization

7. **Export charts:**
   - Save key figures as PNG to `research/figures/`
   - Use matplotlib with publication style: serif font, no gridlines, minimal axes
   - Charts will be embedded in Methodology page

**Acceptance Criteria:**
- [ ] Every magic number in layer1/layer2/layer3 has a documented derivation
- [ ] Sensitivity analysis shows robustness to ±10% parameter variation
- [ ] At least 5 publication-ready charts exported
- [ ] Notebook renders without errors in clean environment
- [ ] Literature citations included where applicable

**Cursor Spec (copy-paste ready):**
```markdown
# Spec: P1-T2 Parameter Derivation Notebook

## Context
The FX Regime Lab signal framework uses several parameters with no documented derivation (0.72 alignment penalty, 0.48 crowding coefficient, hysteresis thresholds, MAD noise floor). This notebook documents and justifies each parameter.

## Files to Read First
- pipeline/src/logic/layer1_gate.py
- pipeline/src/logic/layer2_directional.py
- pipeline/src/logic/layer3_execution.py
- pipeline/src/signals/rate.py (MAD Z-score)
- pipeline/src/signals/cot.py
- pipeline/src/signals/volatility.py

## Required Changes

### 1. Create notebook
Create `research/calibration.ipynb` with these sections:

#### Section 1: Layer 2 Directional Signal Parameters
Document:
- `ALIGNMENT_PENALTY = 0.72` in layer2_directional.py
  - Show sensitivity sweep: test values 0.60, 0.65, 0.70, 0.72, 0.75, 0.80
  - Compute T+5 hit rate for each using backfilled validation data
  - Chart: hit rate vs penalty value
  - If 0.72 is not optimal, note the discrepancy and recommend recalibration
  
- `CROWDING_COEFFICIENT = 0.48` in layer2_directional.py
  - Show empirical relationship: COT percentile >90 vs 5-day reversal probability
  - Chart: reversal probability by percentile bucket (deciles)
  - Derive coefficient from empirical fit

#### Section 2: Layer 1 Hysteresis
Document:
- Schmitt trigger tier boundaries
- Sensitivity: vary tier thresholds ±10%, measure regime stability
- Chart: number of regime changes vs threshold variation

#### Section 3: MAD Z-Score
Document:
- Why MAD vs standard Z-score
- Noise floor derivation
- Literature citation: Rousseeuw & Croux (1993)

#### Section 4: Global Sensitivity
- For each parameter: vary ±5%, ±10%, ±20%
- Measure: T+5 accuracy, Brier score, regime stability
- Chart: tornado diagram showing parameter sensitivity ranking

#### Section 5: Limitations
- What is not yet calibrated
- Path to walk-forward optimization

### 2. Export charts
Save all charts to `research/figures/`:
- `alignment_penalty_sweep.png`
- `crowding_reversal_probability.png`
- `hysteresis_sensitivity.png`
- `parameter_tornado.png`
- `mad_vs_zscore.png`

Use matplotlib style:
```python
plt.rcParams["font.family"] = "serif"
plt.rcParams["axes.grid"] = False
plt.rcParams["figure.facecolor"] = "white"
```

### 3. Add requirements
Add to `pipeline/pyproject.toml` under `[project.optional-dependencies]`:
- jupyter
- matplotlib
- seaborn (optional)

## Constraints
- Do NOT modify signal logic
- Do NOT modify existing tests
- Notebook must render without errors
- All charts must be publication-ready

## Acceptance Criteria
- [ ] Every magic number documented
- [ ] Sensitivity analysis complete
- [ ] 5+ charts exported
- [ ] Notebook renders cleanly
- [ ] Literature citations included
```

---

### P1-T3: AUDIT TRAIL HARDENING (Engineering Truth)

**Chamber 1 Approval:**
- Marcus: Audit trail must be tamper-evident. Hash of inputs proves the call was generated from specific data.

**Chamber 2 Approval:**
- Elias: `write_hash` should be SHA-256 of the signal inputs at call time.
- Sasha: Audit log must be queryable by correlation_id for distributed tracing.
- Viktor: Type-safe. Hash computation must be deterministic.

**Chamber 3 Approval:**
- Peer Reviewer: This satisfies academic immutability standards.

**Task Details:**

1. **Add `write_hash` to `regime_calls`:**
   - Schema migration: add `write_hash VARCHAR(64)` to `regime_calls`
   - In `writer.py write_regime_call()`: compute SHA-256 of JSON-serialized signal inputs
   - Hash inputs: rate_diff_2y, rate_diff_10y, cot_percentile, realized_vol_20d, oi_delta, composite_score
   - This proves the call was generated from specific data — tamper-evident

2. **Add `correlation_id` to `regime_calls` and `audit_log`:**
   - Schema migration: add `correlation_id VARCHAR(64)` to both tables
   - Generate correlation_id at start of daily run (UUID or timestamp-based)
   - Pass through all pipeline steps for distributed tracing

3. **Create `docs/IMMUTABILITY.md`:**
   - Document the immutability guarantee
   - Explain: triggers, audit_log, write_hash, correlation_id
   - Include: "How to verify a regime call has not been tampered with"
   - Include: SQL query to verify hash matches inputs

4. **Add `pipeline_errors` table:**
   - Schema migration: create `pipeline_errors` table
   - Columns: id, correlation_id, step, error_type, message, traceback, timestamp
   - Hook into orchestrator: when any step fails, write to pipeline_errors

**Acceptance Criteria:**
- [ ] `regime_calls.write_hash` is SHA-256 of signal inputs
- [ ] `regime_calls.correlation_id` traces the full pipeline run
- [ ] `audit_log.correlation_id` links audit events to pipeline runs
- [ ] `docs/IMMUTABILITY.md` documents the full guarantee
- [ ] `pipeline_errors` table exists and receives errors
- [ ] 198/198 tests pass
- [ ] ruff clean

**Cursor Spec (copy-paste ready):**
```markdown
# Spec: P1-T3 Audit Trail Hardening

## Context
P0 applied immutable triggers. P1 makes the audit trail tamper-evident and queryable.

## Files to Read First
- pipeline/src/db/writer.py
- pipeline/src/scheduler/orchestrator.py
- supabase/migrations/20260508000001_p0_validation_immutability.sql

## Required Changes

### 1. Schema migrations
Create migration `20260509000001_p1_audit_trail.sql`:

```sql
-- Add write_hash to regime_calls
ALTER TABLE public.regime_calls ADD COLUMN IF NOT EXISTS write_hash VARCHAR(64);
ALTER TABLE public.regime_calls ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64);

-- Add correlation_id to audit_log
ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64);

-- Create pipeline_errors table
CREATE TABLE IF NOT EXISTS public.pipeline_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id VARCHAR(64),
    step TEXT NOT NULL,
    error_type TEXT,
    message TEXT,
    traceback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_errors_correlation ON public.pipeline_errors (correlation_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_errors_created ON public.pipeline_errors (created_at DESC);
ALTER TABLE public.pipeline_errors ENABLE ROW LEVEL SECURITY;
```

### 2. Writer changes
In `writer.py`:
- Add `compute_write_hash(inputs: dict) -> str` — SHA-256 of JSON-serialized inputs
- Modify `write_regime_call()` to accept `correlation_id` and `write_hash` parameters
- Add `write_pipeline_error(correlation_id, step, error_type, message, traceback)`

### 3. Orchestrator changes
In `orchestrator.py`:
- Generate `correlation_id` at start of `run_daily()` (e.g., `f"{date_str}-{uuid4().hex[:8]}"`)
- Pass `correlation_id` to all writer functions
- In the exception handler at end of `run_daily()`, write to `pipeline_errors`
- Compute `write_hash` from signal inputs before writing regime_call

### 4. Documentation
Create `docs/IMMUTABILITY.md`:
- Explain the 4-layer immutability: triggers + audit_log + write_hash + correlation_id
- Include SQL to verify hash: `SELECT write_hash, ... FROM regime_calls WHERE id = ?`
- Explain how to detect tampering

## Constraints
- Do NOT break existing tests
- Do NOT change signal logic
- Type hints everywhere
- ruff + mypy clean

## Acceptance Criteria
- [ ] write_hash is SHA-256 of inputs
- [ ] correlation_id traces pipeline runs
- [ ] pipeline_errors receives exceptions
- [ ] docs/IMMUTABILITY.md complete
- [ ] 198/198 tests pass
- [ ] ruff clean
```

---

### P1-T4: DATA SOURCE UPGRADE (Data Quality)

**Chamber 1 Approval:**
- Dr. Aris: Polygon.io is a credible institutional data source. yfinance is not.
- Marcus: Data quality is as important as signal quality. Bad data = bad calls.

**Chamber 2 Approval:**
- Sasha: Multi-tier fallback must remain. Polygon primary, Alpha Vantage secondary, yfinance tertiary.
- Xavier: Data lineage logging must track which source was used for each price.

**Task Details:**

1. **Upgrade FX spot fetcher:**
   - In `pipeline/src/fetchers/fx_spot.py`:
     - Make Polygon.io the PRIMARY source
     - Alpha Vantage becomes SECONDARY
     - yfinance becomes TERTIARY fallback only
   - Polygon endpoint: `https://api.polygon.io/v2/aggs/ticker/C:EURUSD/range/1/day/{start}/{end}`
   - Note: Polygon uses `C:EURUSD` format for forex pairs

2. **Add data lineage logging:**
   - Add `source` column to `historical_prices` table (if not exists)
   - Add `fetch_timestamp` column
   - Log: which source provided each price point
   - This enables audit: "On 2024-03-15, EUR/USD spot came from Polygon.io at 23:05 UTC"

3. **Update `.env.example`:**
   - Add `POLYGON_API_KEY` (already exists in user's env)
   - Document the 3-tier fallback chain

4. **Test the fallback chain:**
   - Mock Polygon failure → assert Alpha Vantage is tried
   - Mock Alpha Vantage failure → assert yfinance is tried
   - All three failing → assert graceful degradation (pipeline continues with stale data)

**Acceptance Criteria:**
- [ ] Polygon.io is primary for FX spot
- [ ] Alpha Vantage is secondary
- [ ] yfinance is tertiary only
- [ ] Data lineage logged per price point
- [ ] Fallback chain tested
- [ ] 198/198 tests pass
- [ ] ruff clean

**Cursor Spec (copy-paste ready):**
```markdown
# Spec: P1-T4 Data Source Upgrade

## Context
yfinance is currently used as a primary fallback for FX spot prices. Yahoo Finance data has known survivorship bias and handling inconsistencies. This upgrade makes Polygon.io the primary source.

## Files to Read First
- pipeline/src/fetchers/fx_spot.py
- pipeline/src/db/writer.py
- sql/schema.sql (historical_prices table)

## Required Changes

### 1. Reorder data sources in fx_spot.py
Modify `fetch_fx_spot()`:
1. Try Polygon.io first
2. If Polygon fails or rate-limited, try Alpha Vantage
3. If Alpha Vantage fails, try yfinance
4. If all fail, return None (pipeline handles missing data gracefully)

Polygon implementation:
```python
def fetch_fx_spot_polygon(pair: str, start: str, end: str) -> list[SpotBar] | None:
    # Polygon uses C:EURUSD format
    ticker = f"C:{pair.replace('/', '')}"
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}"
    # ... implementation
```

### 2. Add data lineage
Schema migration:
```sql
ALTER TABLE public.historical_prices ADD COLUMN IF NOT EXISTS source VARCHAR(20);
ALTER TABLE public.historical_prices ADD COLUMN IF NOT EXISTS fetch_timestamp TIMESTAMPTZ DEFAULT NOW();
```

In writer.py `write_historical_prices()`:
- Accept `source` parameter
- Write source and fetch_timestamp with each price row

### 3. Environment variables
Add to `.env.example`:
```
POLYGON_API_KEY=your_polygon_api_key
```

### 4. Tests
Create `tests/test_fx_spot_fallback.py`:
- Mock Polygon failure → Alpha Vantage succeeds
- Mock Polygon + Alpha Vantage failure → yfinance succeeds
- Mock all three failure → graceful degradation

## Constraints
- Do NOT break existing fetcher interface
- Fallback chain must be transparent to callers
- Pipeline must continue if all sources fail (uses stale data)
- ruff + mypy clean

## Acceptance Criteria
- [ ] Polygon.io primary
- [ ] Alpha Vantage secondary
- [ ] yfinance tertiary only
- [ ] Data lineage logged
- [ ] Fallback tests pass
- [ ] 198/198 tests pass
- [ ] ruff clean
```

---

## PART 6: EXECUTION ORDER

**P1 tasks have dependencies. Execute in this order:**

1. **P1-T3 first** (audit trail schema) — because P1-T1 writes to validation_log, and write_hash/correlation_id should be available
2. **P1-T1** (backfill) — depends on P1-T3 schema being ready
3. **P1-T4** (data source) — independent, can run in parallel with T1
4. **P1-T2** (notebook) — depends on P1-T1 backfill data for sensitivity analysis

**Revised order:**
- **P1-T3** (schema changes) — first, required by T1
- **P1-T1 + P1-T4** (backfill + data source) — can run in parallel after T3
- **P1-T2** (notebook) — after T1 backfill data is available

---

## PART 7: COMBINED P1-T3+T1 CURSOR SPEC

Because P1-T3 schema changes are needed before P1-T1 can write write_hash and correlation_id, execute T3 first, then T1.

```markdown
# Spec: P1-T3 Audit Trail Schema + P1-T1 Validation Backfill

## Context
Phase 1 of FX Regime Lab hardening. Two tasks:
1. P1-T3: Add write_hash, correlation_id, and pipeline_errors to schema
2. P1-T1: Backfill all historical regime calls with T+5/T+20 validation outcomes

## Files to Read First
- pipeline/src/validation/engine.py
- pipeline/src/db/writer.py
- pipeline/src/backfill/historical_fetcher.py
- pipeline/src/scheduler/orchestrator.py
- supabase/migrations/20260508000001_p0_validation_immutability.sql

## Required Changes

### P1-T3: Schema (migration 20260509000001_p1_audit_trail.sql)
```sql
ALTER TABLE public.regime_calls ADD COLUMN IF NOT EXISTS write_hash VARCHAR(64);
ALTER TABLE public.regime_calls ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64);
ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64);

CREATE TABLE IF NOT EXISTS public.pipeline_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id VARCHAR(64),
    step TEXT NOT NULL,
    error_type TEXT,
    message TEXT,
    traceback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_errors_correlation ON public.pipeline_errors (correlation_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_errors_created ON public.pipeline_errors (created_at DESC);
ALTER TABLE public.pipeline_errors ENABLE ROW LEVEL SECURITY;
```

### P1-T3: Writer changes
- `compute_write_hash(inputs: dict) -> str` — SHA-256 of sorted JSON
- `write_regime_call()` accepts `correlation_id` and `write_hash`
- `write_pipeline_error()` for exception logging

### P1-T3: Orchestrator changes
- Generate `correlation_id` at start of `run_daily()`
- Pass through all writer calls
- Write to `pipeline_errors` on exception

### P1-T1: Backfill module
Create `pipeline/src/backfill/validation_backfill.py`:
- Query unvalidated regime_calls
- For each: compute T+5, T+20 log returns
- Apply Marcus dead-band
- Compute Brier scores
- Write to validation_log (idempotent)

### P1-T1: Integration test
- `tests/integration/test_validation_backfill.py`

## Acceptance Criteria
- [ ] Schema migration applied
- [ ] write_hash computed from inputs
- [ ] correlation_id traces pipeline runs
- [ ] pipeline_errors receives exceptions
- [ ] All historical calls backfilled
- [ ] T+5/T+20 correct
- [ ] Idempotent
- [ ] 198/198 tests pass
- [ ] ruff clean
```

---

## PART 8: VERIFICATION PROTOCOL

After Cursor completes each spec:

1. **Run tests:** `cd pipeline && pytest` — must be 198/198
2. **Run lint:** `cd pipeline && ruff check .` — must be clean
3. **Run type check:** `cd pipeline && mypy src/` — no new errors
4. **Run frontend build:** `cd web && npm run build` — must pass
5. **Manual verification:**
   - P1-T1: Query Supabase — `SELECT COUNT(*) FROM validation_log WHERE brier_score_t5 IS NOT NULL` should equal `SELECT COUNT(*) FROM regime_calls`
   - P1-T3: Verify `regime_calls.write_hash` is populated
   - P1-T3: Verify `pipeline_errors` exists
   - P1-T4: Check `historical_prices.source` is populated

6. **Council Re-convene:**
   - Chamber 1: Are the backfilled stats mathematically correct?
   - Chamber 2: Is the schema type-safe and performant?
   - Chamber 3: Does this pass institutional credibility muster?

7. **Deploy Gate (Tier 2/3):**
   - Shreyash must approve schema changes before production deploy
   - Apply migration via `supabase db push`
   - Monitor first run for 48 hours

---

## PART 9: DOCUMENTATION SYNC CHECKLIST

After P1 completion, update these files:

- [ ] `TASK.md` — mark P1-T1, P1-T2, P1-T3, P1-T4 as complete
- [ ] `CONTEXT.md` — update validation section with backfill status
- [ ] `HANDOVER.md` — if any operational rules changed
- [ ] `PLAN_EXECUTION_10_10.md` — mark Phase 1 complete with actual dates
- [ ] Create `docs/IMMUTABILITY.md` (P1-T3)
- [ ] Regenerate `.agent/maps/` via `fx-agent maps` or git hook

---

## PART 10: LOCKED DECISIONS CHECK

Before executing, confirm none of these are violated:

| Decision | P1 Impact | Status |
|----------|-----------|--------|
| 3-pair lock | No pair changes | ✅ Safe |
| All DB writes through writer.py | All writes go through writer.py | ✅ Safe |
| regime_calls + validation_log append-only | P1-T1 respects immutability | ✅ Safe |
| Prefect Cloud only | No GitHub Actions added for pipeline | ✅ Safe |
| Python-only stack | No C++ | ✅ Safe |
| No ML | No ML models | ✅ Safe |

---

*End of P1 Complete Prompt. Copy everything above this line into your new session.*
