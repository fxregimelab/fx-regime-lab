# P1-T1 + P1-T4 COMPLETE PROMPT — Validation Backfill & Data Source Upgrade

> **COPY AND PASTE THIS ENTIRE DOCUMENT** into your new AI session. Do not summarize. Do not omit sections. This prompt is self-contained and includes all context, protocol, and execution specs required to complete P1-T1 and P1-T4.

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

## PART 2: PROJECT CONTEXT + COMPLETION STATUS

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
- pytest must pass (205 tests), npm run build must pass

### P0 Status: COMPLETE (2026-05-08)
- P0-T1: Validation engine wired into orchestrator (`run_validation()` called daily)
- P0-T2: Immutable ledger enforced (triggers active in Supabase, UPDATE/DELETE blocked)
- P0-T3: Alerting active (Slack heartbeat, email on DQS < 0.70)
- Supabase migration `20260508000001_p0_validation_immutability.sql` applied
- 205/205 tests pass, ruff clean

### P1-T3 Status: COMPLETE (2026-05-08)
- `correlation_id` and `write_hash` columns added to `regime_calls`
- `pipeline_errors` table created with all required columns
- `compute_write_hash()` produces deterministic SHA-256 of inputs
- `docs/IMMUTABILITY.md` documents tamper-evident guarantees
- Schema applied to Supabase via `supabase db query --linked`
- 205/205 tests pass, ruff clean

**The OMEGA Council (13 personas):**
- Chamber 1 (Strategy): Dr. Aris (Structural Economist), Lena (Quant Researcher), Marcus (Macro PM), Chen (Alpha Analyst)
- Chamber 2 (Engineering): Elias (Data Architect), Sasha (SRE), Viktor (Python Rigorist), Xavier (System Architect)
- Chamber 3 (Perception): Peer Reviewer, Hugo (Design Psychologist), Elena (Institutional UX), Claire (Substack Editor), Coach Silas (Strategic Performance)

**You MUST simulate the council for every significant decision.**

---

## PART 3: WHY THESE TASKS EXIST

### P1-T1: Validation Backfill (The Track Record)

The validation engine runs daily starting from P0, but historical regime calls from before P0 have no T+5/T+20 outcomes. Without backfill:
- The Performance page shows empty accuracy stats
- The Brier score table has no historical data
- An admissions director sees a framework with no proven edge

**This is the highest-EV task in all of P1.** It transforms the project from "aspirational" to "proven."

### P1-T4: Data Source Upgrade (Credibility)

yfinance is used as a fallback for FX spot prices. Yahoo Finance data has known issues:
- Survivorship bias
- Inconsistent split/dividend handling
- Ticker changes without notice

For institutional rigor, the primary source must be Polygon.io or equivalent. This is not urgent for the track record, but it is required before presenting to a quant fund recruiter.

---

## PART 4: THE 14/10 PROTOCOL

Every task must execute through these 14 steps:

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
- P1-T4 (data source swap): Tier 2 — auto + approval gate

---

## PART 5: P1-T1 — VALIDATION BACKFILL (Historical Proof)

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

### Task Details

1. **Read these files first:**
   - `pipeline/src/validation/engine.py` — live validation logic (T+5/T+20, Brier, dead-band)
   - `pipeline/src/db/writer.py` — how to write validation rows
   - `pipeline/src/backfill/historical_fetcher.py` — how to fetch historical prices
   - `supabase/migrations/20260508000001_p0_validation_immutability.sql` — validation_log schema

2. **Create backfill module:** `pipeline/src/backfill/validation_backfill.py`

   **Functions to implement:**
   - `get_unvalidated_calls() -> list[dict]` — Query `regime_calls` rows that lack corresponding `validation_log` rows with non-null `brier_score_t5`
   - `get_spot_price(pair: str, target_date: date) -> float | None` — Read from `historical_prices` table. Fallback to yfinance for missing dates.
   - `add_trading_days(start: date, n: int) -> date` — Add n trading days (weekdays only, skip weekends)
   - `compute_log_return_bps(s0: float, sh: float) -> float` — `10000 * ln(sh / s0)`
   - `apply_dead_band(bps: float) -> str` — Returns "CORRECT" / "WRONG" / "NEUTRAL" based on Marcus dead-band ±5 bps
   - `compute_brier_score(conviction: int, outcome: str) -> float` — `(p - y)²` where `p = conviction / 5` (normalized 0-1), `y = 1` if CORRECT, `0` if WRONG, `0.5` if NEUTRAL
   - `backfill_validation_for_call(call: dict) -> bool` — Full backfill for one call, write to validation_log
   - `run_backfill_all(limit: int | None = None) -> tuple[int, int]` — Backfill all unvalidated calls. Return `(processed, skipped)`.

3. **Idempotency (CRITICAL):**
   - Before writing each validation row, check if `validation_log` already has a row for this `call_id` with non-null `brier_score_t5`
   - If yes, skip (log debug message)
   - If no, write using `writer.write_validation_engine_row()`
   - Re-running the script must produce zero duplicates

4. **Price sourcing priority:**
   1. Supabase `historical_prices` table (already backfilled via `src/backfill/historical_fetcher.py`)
   2. yfinance direct fetch for missing dates
   3. If T+5 or T+20 price is missing, skip that horizon (leave column NULL)

5. **Trading day logic:**
   - Count weekdays only (Mon-Fri)
   - Skip weekends
   - If T+5 or T+20 falls on a weekend, use the next Monday
   - US holiday handling is optional but preferred

6. **Brier score computation:**
   - `conviction` is 1-5 integer from `regime_calls.confidence`
   - `p = conviction / 5` (so conviction 4 → p = 0.8)
   - `y = 1.0` if directional call matches return sign AND |bps| > 5
   - `y = 0.0` if directional call opposes return sign AND |bps| > 5
   - `y = 0.5` if |bps| ≤ 5 (Marcus dead-band — neutral, no directional credit)
   - Brier = `(p - y)²`

7. **Aggregate stats generation:**
   - After backfill completes, run `python -m src.validation.aggregate`
   - This populates `validation_stats` with per-pair, per-regime accuracy

8. **CLI entrypoint:**
   - Create `python -m src.backfill.validation_backfill` as main entrypoint
   - Accept `--dry-run` flag: compute but do not write
   - Accept `--limit N` flag: backfill only N oldest unvalidated calls
   - Print progress: `Backfilled 45/120 calls (EURUSD: 15, USDJPY: 15, USDINR: 15)`

9. **Integration test:**
   - Create `tests/integration/test_validation_backfill.py`
   - Insert a synthetic `regime_call` with known date
   - Mock `historical_prices` for S₀, S₅, S₂₀
   - Run backfill for that call
   - Assert: `validation_log` row has correct `brier_5d`, `correct_5d`, `brier_20d`, `correct_20d`
   - Assert: re-run is idempotent (no duplicate rows)

### Acceptance Criteria
- [ ] All historical `regime_calls` rows have corresponding `validation_log` rows
- [ ] T+5 and T+20 values are in correct columns (no overwriting)
- [ ] Log returns computed correctly: `bps = 10,000 × ln(Sₕ/S₀)`
- [ ] Marcus dead-band (±5 bps) applied correctly
- [ ] Brier scores use `conviction/5` as probability
- [ ] Idempotent: re-running produces zero duplicates
- [ ] `validation_stats` populated with aggregate data
- [ ] Integration test passes
- [ ] `cd pipeline && pytest` passes (205/205)
- [ ] `ruff check` clean
- [ ] `mypy` clean on new module

### Cursor Spec (copy-paste ready)
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
Create `pipeline/src/backfill/validation_backfill.py` with these functions:

```python
def get_unvalidated_calls() -> list[dict[str, Any]]:
    """Return regime_calls rows that lack validation_log rows with brier_score_t5."""

def get_spot_price(pair: str, target_date: date) -> float | None:
    """Read spot price from historical_prices table. Fallback to yfinance."""

def add_trading_days(start: date, n: int) -> date:
    """Add n trading days (weekdays only)."""

def compute_log_return_bps(s0: float, sh: float) -> float:
    """Compute log return in basis points: 10000 * ln(sh/s0)."""

def apply_dead_band(bps: float) -> str:
    """Return CORRECT / WRONG / NEUTRAL based on ±5 bps dead-band."""

def compute_brier_score(conviction: int, outcome: str) -> float:
    """Compute Brier score: (p - y)^2 where p = conviction/5."""

def backfill_validation_for_call(call: dict[str, Any]) -> bool:
    """Backfill one call. Return True if written, False if skipped."""

def run_backfill_all(limit: int | None = None) -> tuple[int, int]:
    """Backfill all unvalidated calls. Return (processed, skipped)."""
```

### 2. Idempotency logic
Before writing each validation row:
- Query validation_log for this call_id where brier_score_t5 IS NOT NULL
- If exists, skip with debug log
- If not, write using writer.write_validation_engine_row()

### 3. Price sourcing priority
1. Supabase historical_prices table
2. yfinance fallback for missing dates
3. If T+5 or T+20 price still missing, skip that horizon (leave NULL)

### 4. Trading day calculation
- Count weekdays only (Mon-Fri)
- Skip weekends
- US holiday handling optional

### 5. Brier score
- p = conviction / 5
- y = 1.0 (correct), 0.0 (wrong), 0.5 (neutral/dead-band)
- Brier = (p - y) ** 2

### 6. Aggregate stats
After backfill, run: `python -m src.validation.aggregate`

### 7. CLI entrypoint
```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    processed, skipped = run_backfill_all(limit=args.limit)
    print(f"Backfill complete: {processed} processed, {skipped} skipped")
```

### 8. Integration test
Create `tests/integration/test_validation_backfill.py`:
- Insert synthetic regime_call
- Mock historical_prices for S0, S5, S20
- Run backfill
- Assert validation_log has correct values
- Assert re-run is idempotent

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
- [ ] 205/205 pytest tests pass
- [ ] ruff clean
- [ ] mypy clean
```

---

## PART 6: P1-T4 — DATA SOURCE UPGRADE (Data Quality)

**Chamber 1 Approval:**
- Dr. Aris: Polygon.io is a credible institutional data source. yfinance is not.
- Marcus: Data quality is as important as signal quality. Bad data = bad calls.

**Chamber 2 Approval:**
- Sasha: Multi-tier fallback must remain. Polygon primary, Alpha Vantage secondary, yfinance tertiary.
- Xavier: Data lineage logging must track which source was used for each price.

### Task Details

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

### Acceptance Criteria
- [ ] Polygon.io is primary for FX spot
- [ ] Alpha Vantage is secondary
- [ ] yfinance is tertiary only
- [ ] Data lineage logged per price point
- [ ] Fallback chain tested
- [ ] 205/205 tests pass
- [ ] ruff clean

### Cursor Spec (copy-paste ready)
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
- [ ] 205/205 tests pass
- [ ] ruff clean
```

---

## PART 7: EXECUTION ORDER

**P1-T1 and P1-T4 are independent.** They can run in parallel.

**Recommended approach:**
1. **Delegate P1-T1 to Cursor** (highest EV — do this first)
2. **Delegate P1-T4 to Cursor** in parallel (independent)
3. Run backfill script after both complete
4. Verify aggregate stats populated

---

## PART 8: VERIFICATION PROTOCOL

After Cursor completes:

1. **Run tests:** `cd pipeline && pytest` — must be 205/205
2. **Run lint:** `cd pipeline && ruff check .` — must be clean
3. **Run type check:** `cd pipeline && mypy src/` — no new errors
4. **Run frontend build:** `cd web && npm run build` — must pass
5. **Manual verification:**
   - P1-T1: `SELECT COUNT(*) FROM validation_log WHERE brier_score_t5 IS NOT NULL` should equal `SELECT COUNT(*) FROM regime_calls`
   - P1-T1: Sample 5 validation rows and manually verify math
   - P1-T4: Check `historical_prices.source` is populated with "polygon"

6. **Council Re-convene:**
   - Chamber 1: Are the backfilled stats mathematically correct?
   - Chamber 2: Is the schema type-safe and performant?
   - Chamber 3: Does this pass institutional credibility muster?

7. **Deploy Gate (Tier 2):**
   - Shreyash must approve before running backfill on production
   - Run backfill with `--dry-run` first
   - Monitor Supabase for 48 hours after backfill

---

## PART 9: DOCUMENTATION SYNC CHECKLIST

After completion, update these files:

- [ ] `TASK.md` — mark P1-T1 and P1-T4 as complete
- [ ] `CONTEXT.md` — update validation section with backfill status
- [ ] `HANDOVER.md` — if any operational rules changed
- [ ] `PLAN_EXECUTION_10_10.md` — mark Phase 1 progress
- [ ] Regenerate `.agent/maps/` via `fx-agent maps` or git hook

---

## PART 10: LOCKED DECISIONS CHECK

Before executing, confirm none of these are violated:

| Decision | Impact | Status |
|----------|--------|--------|
| 3-pair lock | No pair changes | ✅ Safe |
| All DB writes through writer.py | All writes go through writer.py | ✅ Safe |
| regime_calls + validation_log append-only | Backfill respects immutability | ✅ Safe |
| Prefect Cloud only | No GitHub Actions added for pipeline | ✅ Safe |
| Python-only stack | No C++ | ✅ Safe |
| No ML | No ML models | ✅ Safe |

---

*End of P1-T1 + P1-T4 Prompt. Copy everything above this line into your new session.*
