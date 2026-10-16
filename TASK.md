# TASK.md — Current Sprint

> **Read `IDENTITY.md` first** — it is the hard constraint.  
> **Read `MASTERPLAN.md` second** — it defines all phases, priorities, and gates.  
> Read `docs/METHODOLOGY_AUDIT_TRIPLE_PERSONA.md` for the full audit report.

## Current Sprint: fx-live-personal (background branch only, 2026-10-17)

Branch `fx-live-personal` cut from main `bb089f3` (includes `v2.1-archive` tag).
Main stays archived. Never push to main. Never move the tag.

- [x] Step 1 triage: pytest 379/379 green, `tsc --noEmit` 0 errors,
  `biome check` clean (206 files), `npm run build` pass. Migrations 59 files
  on disk (58 real + 1 zero-byte tmp; `DB_STATUS.md` documents 49 — stale).
  Prefect pull branch still `main` (background runs need manual trigger).
  MOF + ECB-SDW fetchers deferred (proxies only). Footer stays DEGRADED.
- [x] Step 2 first AI + eval slice: one LLM reader
  (`pipeline/src/ai/renderers/analyst_note.py`,
  `pipeline/src/ai/analyst_reader.py`) + eval harness
  (`pipeline/src/eval/llm_reader_eval.py`). Baseline
  `reports/llm_reader_eval_v1.md`: faithfulness 1.000, number accuracy 1.000
  (deterministic, 3 synthetic rows), Brier n=0 (no outcomes claimed).
  391/391 pytest (379 + 12 new), ruff clean. Zero ledger writes.
- [ ] Step 3: push slices to `origin fx-live-personal`; draft PR only when
  live + eval green with ledger delta zero (new rows only). No auto-merge.
- [ ] Step 4: docs updated on branch (this file, README, AGENTS.md counts,
  CONTEXT.md repair section, HANDOVER.md operator status, MASTERPLAN.md
  phases, `reports/REPAIR_CHECKPOINT.md` packets). 6 root gates still open.
  No VERIFIED RELEASE without live observation + receipts.

## Completed

**Step 0: Identity Compliance Audit — COMPLETED (2026-05-18)**
- All IDENTITY violations identified, approved, and resolved

**Stream A: Signal Depth — COMPLETED (2026-05-17)**
- 6 pair-specific macro signals deployed and populating daily
- 235 pytest passing (was 228)
- ruff clean, TypeScript clean, Biome clean
- See git history for implementation commits

**Phase M.1: Bias Fixes — COMPLETED (2026-05-18)**
- M.1.1 COT causal exclusion (`hist = vals[:-1]`)
- M.1.2 Special causal exclusion (`hist[:-1]`)
- M.1.3 Spot Z-score causal window
- M.1.4 FPI SD → MAD
- M.1.5 OI weight 0.05 for all pairs
- 250 tests passing

**Phase M.2: Adaptive Weighting — COMPLETED (2026-05-19)**
- M.2.1 Dynamic beta precision weights with 10% floor
- M.2.2 Redundancy penalty (0.03 per same-sign pair, cap 0.15)
- M.2.3 Heuristic Platt confidence calibration (`0.35 + 0.40 * raw`)
- Removed USDINR post-hoc nudges from orchestrator

**Phase M.3: Signal Quality — COMPLETED (2026-05-19)**
- M.3.1 Real EURUSD special signal (Bund-BTP + ECB BS percentile blend)
- M.3.2 Rate z_blended (60% tactical + 40% structural)
- M.3.3 COT smart spread (AM-LM blended 70/30)
- M.3.4 Risk-adjusted carry v2 (prefers implied vol, falls back to RV20)
- EURUSD special_label updated to signal-aware logic

**Phase M.5: Diagnostic Calibration & Validation — COMPLETED (2026-05-20)**
- `src/diagnostics/permutation_importance.py` — shuffle-based family importance
- `src/backfill/simulation_engine.py` — `simulate_all_days_v2` with full M.3 logic
- `src/diagnostics/accuracy_report.py` — side-by-side v1 vs v2 Markdown reports
- `tests/test_simulation_engine.py` — 2 synthetic diagnostic tests
- 264 tests passing, ruff clean, mypy clean on new modules

## Current Phase: M.4 Prep + Live Monitoring (branch fx-live-personal active, 2026-10-17)

> Background branch `fx-live-personal` @ `bb089f3`: pytest 391/391, web build
> green, LLM reader + eval slice landed with zero ledger writes. Footer stays
> DEGRADED. 6 root gates open — see `reports/REPAIR_CHECKPOINT.md`.

**Staged Pipeline v2 — Slice #16 COMPLETED (2026-06-24)**
- Production adapters: `ProductionFetcherPort`, `ProductionWriterPort`, `ProductionAlertPort`
- Single-pair Prefect `@flow`: `src/staged.orchestrator.run_single_pair_flow`
- Recorded EUR/USD fixture: `pipeline/tests/fixtures/eurusd_snapshot.py`
- Adapter unit tests + orchestrator integration tests
- 292 pytest passing, ruff clean, mypy strict clean

**DB Audit & Cleanup — FULLY COMPLETED (2026-05-21)**
- Audit report in `docs/DB_AUDIT_STRATEGY.md`
- Live schema reference in `docs/DB_STATUS.md`
- **Round 1 (merged to main):**
  - 6 stale columns dropped from `signals` table
  - 12 stale columns dropped from `validation_log` table
  - Stream A migration (`20260518000003`) pushed to production
  - `queries.ts` refactored to read live data instead of ghost columns
  - `database.types.ts` synced with cleaned schema
- **Round 2 (merged to main):**
  - `validation_log.notes` dropped (unused)
  - 6 stale tables removed from `database.types.ts`
  - All 234 tests passing, ruff clean, TypeScript clean
- All migrations synced local ↔ remote (49 applied)

**M.4 Threshold Optimization (LOCKED)**
- Gate: 90+ days live OOS before Tier 3 threshold optimization
- M.4.1 Walk-forward optimize `_COMPOSITE_STRONG`
- M.4.2 Walk-forward optimize `_VOL_RANK_ENTER_MAX`
- M.4.3 Walk-forward optimize hysteresis boundaries
- **Status:** Locked until validation ledger has 90+ days of live calls

## Implementation Queue (Historical Record)

### Phase M.1: Bias Fixes (No-Regret, Zero Overfitting) — ✅ DONE

| Task | File | Expected Gain | Complexity |
|------|------|--------------|------------|
| M.1.1 Fix look-ahead bias in COT percentile | `src/signals/cot.py` | +1-2 pp | Very Low |
| M.1.2 Fix look-ahead bias in Special percentile | `src/signals/special.py` | +1-2 pp | Very Low |
| M.1.3 Fix spot Z-score inclusion of current point | `src/logic/math_utils.py` | +0.5-1 pp | Low |
| M.1.4 Replace FPI SD with MAD | `src/signals/fpi.py` | +0.5-1 pp | Very Low |
| M.1.5 Reduce OI weight to ≤0.05 | `src/regime/composite.py` | +0.5-1 pp | Very Low |

### Phase M.2: Adaptive Weighting (Medium Complexity, Low Overfitting) — ✅ DONE

| Task | File | Expected Gain | Complexity |
|------|------|--------------|------------|
| M.2.1 Use dynamic betas to precision-weight composite | `src/regime/composite.py` | +2-4 pp | Medium |
| M.2.2 Add covariance-aware composite variance penalty | `src/regime/composite.py` | +1-2 pp | Medium |
| M.2.3 Calibrate confidence to empirical probability | `src/regime/confidence.py` | Indirect | Medium |

### Phase M.3: Signal Quality (Medium Complexity, Medium Overfitting) — ✅ DONE

| Task | File | Expected Gain | Complexity |
|------|------|--------------|------------|
| M.3.1 Build real EUR/USD special signal (term premium / CPI diff) | `src/signals/special.py` | +1-3 pp | Medium |
| M.3.2 Elevate real yield differential to co-primary | `src/signals/rate.py` | +3-4 pp | Medium |
| M.3.3 Replace COT net long with AM-Lev spread | `src/signals/cot.py` | +2-3 pp | Medium |
| M.3.4 Replace RV20 with implied vol in carry | `src/signals/rate.py` | +1-2 pp | Low |

### Phase M.4: Threshold Optimization (High Complexity, Medium Overfitting) — 🔒 LOCKED

| Task | File | Expected Gain | Complexity |
|------|------|--------------|------------|
| M.4.1 Walk-forward optimize _COMPOSITE_STRONG | `src/logic/layer2_directional.py` | +1-2 pp | High |
| M.4.2 Walk-forward optimize _VOL_RANK_ENTER_MAX | `src/logic/layer3_execution.py` | +0.5-1 pp | High |
| M.4.3 Walk-forward optimize hysteresis boundaries | `src/logic/math_utils.py` | +0.5-1 pp | High |

**Gate:** Phase B must be met before any Tier 3 threshold optimization. M.4 is locked until 90+ days live OOS.

## Test & Quality Baseline

| Metric | Current | Target |
|--------|---------|--------|
| pytest | 391/391 ✅ (379 baseline + 12 reader/eval) | 391+ |
| TypeScript | 0 errors ✅ | 0 |
| Biome | Clean ✅ | Clean |
| Build | `npm run build` ✅ | Pass |

## Verification (Run Before Any Merge)

```bash
cd pipeline && pytest
cd web && npx tsc --noEmit
cd web && npm run build
cd web && npx biome check . --changed
```

## Identity Reminders

- No execution advice in public UI (position_size, stop_level are internal-only)
- No "signals" language — use "classifications" or "regime calls"
- No educational framing — practitioner-to-practitioner research tone
- Immutable ledger: `regime_calls` and `validation_log` are append-only
- 3-pair lock: EURUSD, USDJPY, USDINR only

## Last Deploy

- **Commit:** DB Cleanup Round 1 & 2 merged to main
- **Status:** All green. Vercel auto-deploy active.

---

*Historical completion records are in git history. See previous commits for Rounds 1–5, P0–P4, v2.0, Stream A, and Phases M.1–M.5.*
