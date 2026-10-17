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
- [x] Step 3: pushed to `origin fx-live-personal`. **Live green run**
  2026-10-17 08:07–08:11 UTC published 3 calls @ 2026-10-16 (EURUSD/USDJPY
  NEUTRAL, USDINR INR_NEUTRAL; model 2.0-live). Ledger delta = new rows
  only: regime_calls +3 with all 19,503 prior rows byte-identical (SHA-256
  `eec0749c…`); validation_log +12 inserts − 6 flag-only supersessions.
  Eval on the fresh calls: `reports/llm_reader_eval_v3_latest.*` (faith
  1.000 / num 1.000, Brier n=0). Draft PR opened to main — human merges
  only, never auto-merge.
- [x] Step 4: docs updated on branch (this file, README, AGENTS.md counts,
  CONTEXT.md repair section, HANDOVER.md operator status, MASTERPLAN.md
  phases, `docs/DB_STATUS.md` 49→58, `reports/REPAIR_CHECKPOINT.md` packets
  1–6). 6 root gates still open; footer stays DEGRADED until operator
  preview check. No VERIFIED RELEASE claimed.
- [x] Step 5: footer honesty fix + owner-approved publish. Task line "keep
  DEGRADED until truly green, then change to LIVE with date" executed: the
  site banner was falsely DEGRADED (fallback scored only the current calendar
  day; calls are dated by trading day by design). Web fix scores the latest
  published day with its real DQS (0.8 gate): `queries.ts` fallback,
  `desk/layout.tsx`, `audit-trail-banner.tsx`. Checks: `tsc --noEmit` 0,
  biome clean, `npm run build` pass. Owner-instructed merge to main via
  PR #20 (merge commit, no squash, no force push — receipts on the PR
  timeline).

## Next Initiative: Personal Trading Engine (drafted 2026-10-17, awaiting owner decisions)

Audit + expansion plan: `docs/PERSONAL_TRADING_ENGINE_PLAN.md` (draft v0.1, plan gate
only, no code yet). Paper-only personal desk on the 3 pairs. Key audit findings: repair/
reader/expansion are reusable foundations; live directional record is below coin-flip
(EURUSD 26% / USDJPY 32% / USDINR 41%, May–Oct 2026); 12 corrupted validation rows
(±500bps, cross-pair contamination, May 2026); `strategy_ledger` MTM walk stopped
2026-05-27; OHLC bars stale to 2026-06-29. Plan: P0–P4 (foundations → backtests →
paper account → local-agent layer → operate), everything local-first, zero production
writes, public product untouched. 8 owner decisions with defaults in §11 of the plan.
Owner-requested MT5 add-on planned (§5.9): real spread data + demo-account execution
(owner prerequisite: terminal + demo login).

Owner GO'd all defaults (2026-10-17); P0 started. Trading subset = EURUSD + USDJPY
only (no USDINR execution). **MT5 demo CONNECTED (2026-10-17 evening):** Exness-branded
terminal `C:\Program Files\MetaTrader 5 EXNESS` (portable, build 6272), demo `414***68`
on `Exness-MT5Trial6` (hedging; owner topped up balance to **USD 10,000** — cent-equivalent
of $100 real). Trade symbols are `EURUSDm` /
`USDJPYm` (Exness 'm' suffix); quotes + OHLC history (since 2018) verified via MCP.
MCP endpoints live: terminal `127.0.0.1:22346`, MetaEditor `127.0.0.1:22345`; key lives
only in gitignored client configs (project `.mcp.json` / `.codex/config.toml`, user
OpenCode config — native tool integration confirmed working). Old MetaQuotes terminal
uninstalled + registry/shortcut cleanup done (chart profiles rescued to the new install
first). Balance RESOLVED: Exness cent accounts are real-only (no cent demo) — standard
demo topped up to $10,000 ≡ cent account at $100 (risk-relevant quantities scale ×100).
Real-money equivalent = desk balance ÷ 100; desk E₀ = 10,000 matches the demo 1:1;
owner's 1%-max-risk rule applies (0.75% default). See plan §5.9.
Spike tool: `pipeline/scripts/desk_mt5_spike.py` (env-driven, masked output).
Desk config: `pipeline/src/paper/config.py`.
P0 build (2026-10-17 night): `paper/store.py` (local SQLite — append-only hash-chained ledger +
refreshable bar cache) + `paper/prices.py` + `scripts/desk_prices_sync.py`; D1 bars seeded
(EURUSDm/USDJPYm, 2018-07-03 → 2026-10-16, 2×2588, 0 quarantined); genesis receipt in
`reports/desk/`; MetaTrader5 python package wired into the venv. Repo now fully mypy-clean
(220 files; 17 pre-existing annotation fixes) — 406/406 pytest, ruff clean.

Desk playbook v0.1 (2026-10-17 night): **`docs/DESK_TRADING_PLAYBOOK.md`** — owner removed the
per-trade approval gate for the demo phase (autonomy inside guardrails; real money still gated).
Intraday-first management (50% scale-out at 1R → break-even → 1.2×ATR_H1 trail beyond structure;
early-cut + time-stop rules; ≤8h typical, **T+5 max**). Confidence = **binary checklist** (5 hard
gates + 9 scored = 14 checks → grades A/B/C; only A/B trade; grade sizes risk 0.75%/0.5%).
Multi-TF confirmation (D1/H4/H1/M15) + per-candidate news research packet (bull/bear/neutral,
each with falsifiers). Concurrency caps: ≤3 open, ≤1 per pair, ≤2.25% open risk, −3% daily /
−6% weekly kill-switches. Limits in `paper/config.py` (`TradingLimits`); intraday bars
(H4/H1/M15) seeded into the local store. Plan §5.10 amended. Last updated: 2026-10-17.

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

> Branch `fx-live-personal` owner-instructed merge to main (PR #20, merge
> commit): pytest 391/391, web build green, LLM reader + eval slice landed
> with zero ledger writes on history. Site banner now honestly reads the
> latest published day (`Pipeline: OK · DQS 1.00`). 6 root gates open — see
> `reports/REPAIR_CHECKPOINT.md`.

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
| pytest | 406/406 ✅ (391 + 15 paper desk) | 406+ |
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
