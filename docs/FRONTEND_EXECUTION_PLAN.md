# Frontend Execution Plan v2.0 — Full Site Audit & Repair
> **Scope:** ALL pages (terminal, methodology, about, performance, brief, audit, calendar, memo, homepage)
> **Date:** 2026-05-15
> **Build:** Next.js 15.3.9, React 19, Tailwind v4, Biome clean
> **Test gate:** `cd web && npm run build` + `cd pipeline && pytest`

---

## Executive Summary

| Category | Count | Severity |
|----------|-------|----------|
| 🔴 Critical (wrong data, misleading claims, identity violations) | 12 | Blocker |
| 🟡 High (missing features, stale descriptions, accuracy drift) | 16 | Must-fix |
| 🟠 Medium (hardcoded thresholds, pair-specific gaps) | 14 | Should-fix |
| 🟢 Low (dead links, cosmetic, tone polish) | 6 | Polish |

**Total actionable items: 48**

---

## 🔴 Critical (P0 — Blockers)

### C1. Composite weights wrong on all 3 pairs
- **Files:** `MethodologyContent.tsx` (402-451), `[pair]/page.tsx` (166-171, 727-766), `signal-inspector.tsx` (95-100), `data-lineage.tsx` (92, 123)
- **Issue:** All 4 locations show `RATE 40 / COT 30 / VOL 20 / OI 10`. Pipeline truth:
  | Pair | Rate | COT | Vol | OI | Special | FPI |
  |------|------|-----|-----|----|---------|-----|
  | EURUSD | 45% | 25% | 20% | 5% | 5% | — |
  | USDJPY | 40% | 20% | 25% | 5% | 10% | — |
  | USDINR | 30% | 10% | 20% | 5% | 20% | 15% |
- **Fix:** Replace hardcoded `SIGNAL_ARCH` with per-pair weight map. Update visual decomposition bar + legend.

### C2. EURUSD special signal labeled "placeholder"
- **Files:** `MethodologyContent.tsx` (407), `SignalDecomposition.tsx` (76)
- **Issue:** "EURUSD returns 0.0 (no active special factor)" — false. Since M.3.1, EURUSD uses Bund-BTP spread + ECB balance sheet.
- **Fix:** Rewrite description to mention Bund-BTP percentile + ECB BS YoY blend.

### C3. SignalDecomposition shows synthetic data as "Live Example"
- **File:** `SignalDecomposition.tsx` (lines 17-83 synthetic, line 253 label)
- **Issue:** `IDENTITY.md` line 130: "No illustrative examples presented as live data. If the data is not live, the page does not go up."
- **Fix:** Either fetch real latest signal from DB or relabel as "Illustrative (Synthetic) Example".

### C4. DollarDominanceIndex misclassifies INR regimes
- **File:** `brief/page.tsx` (lines 30-46)
- **Issue:** Naive `"APPRECIATION"` substring match. `INR_APPRECIATION` (INR strengthening = USD weakening) counts as USD STRONG. Backwards.
- **Fix:** Use `classifyRegime()` from `regime-classifier.ts` instead of string matching.

### C5. UseStrategyLedger orders by non-existent `entry_date`
- **File:** `web/src/lib/queries.ts` (line ~113)
- **Issue:** `order("entry_date", ...)` should be `order("date", ...)`
- **Fix:** Rename column reference.

### C6. `india_vix` and `inr_forward_premium` in DB but never queried
- **Files:** `lib/supabase/queries.ts` mapper drops them; `LatestSignal` type omits them
- **Issue:** Pipeline writes these for USDINR but frontend never fetches or displays.
- **Fix:** Add to `LatestSignal`, `toLatestSignal()`, and render in USDINR signal table.

### C7. COT "EXTREME" threshold 85/15 on `[pair]/page.tsx` — pipeline uses 90/10
- **File:** `[pair]/page.tsx` (line 87-89 in `getWatchlist()`)
- **Fix:** Update to 90/10 to match `_CROWD_SOFT_HI/LO`.

### C8. Performance page re-computes DB stats (overrides backend)
- **File:** `performance/page.tsx` (lines 184-331)
- **Issue:** `computeStatsFromLog()` recalculates win rate, Brier, sample size from raw log. Any backend fix won't reflect. Also treats NEUTRAL/`—` as excluded from denominator.
- **Fix:** Use `validation_stats` table values as source of truth; only compute rolling 90d from log dates.

### C9. Accuracy tracker says "90-Day" but uses 30 pts of 10-call rolling
- **Files:** `performance/page.tsx` (lines 525), `AccuracyMilestoneTracker.tsx` (line 286)
- **Issue:** Label says /90, denominator says /90, but only 30 historical points are ever passed.
- **Fix:** Either change label to "30-point window" or pass 90 days of data.

### C10. Rate Z-score formula shows Gaussian z — pipeline uses MAD Z
- **File:** `MethodologyContent.tsx` (line 163)
- **Issue:** `z = (x_t - μ) / σ` shown. Pipeline uses `median / (MAD × 1.4826)`.
- **Fix:** Update formula and description.

### C11. Confidence derivation omits Platt calibration
- **File:** `MethodologyContent.tsx` (line 492)
- **Issue:** Shows raw `clip(..., 0.30, 0.90)`. Pipeline applies `0.35 + 0.40 × raw` afterwards.
- **Fix:** Add calibration step to formula and note that final confidence caps at ~0.71 for raw 0.90.

### C12. USDJPY confidence bonus misattributed to "carry signal"
- **File:** `MethodologyContent.tsx` (line 483)
- **Issue:** Says "USDJPY carry signal > 0.5". Pipeline checks `special_signal > 0.5`.
- **Fix:** Correct text.

---

## 🟡 High (P1 — Must-fix)

### H1. Missing M.3.2 `z_blended` everywhere
- **Pipeline:** `rate.py` computes 60% tactical + 40% structural MAD Z
- **Issue:** Not persisted to DB, not shown in UI. Terminal shows only raw `rate_diff_2y`.
- **Fix:** Add `z_blended` to `signals` table schema + writer + mapper + display.

### H2. Missing M.3.3 COT smart spread from methodology
- **Pipeline:** `cot.py:61-109` uses 70% traditional net long + 30% asset-manager-minus-leveraged-money spread
- **Issue:** Nowhere in UI. Methodology still says "non-commercial net positions".
- **Fix:** Add methodology section; add COT smart spread display in terminal COT chip tooltip.

### H3. Missing M.2.1 adaptive precision weighting from methodology
- **Pipeline:** `_precision_weights()` scales by |beta|/0.10 with 10% floor
- **Issue:** Methodology describes static weights only.
- **Fix:** Add section explaining dynamic beta-informed reweighting.

### H4. Missing M.2.2 redundancy penalty from methodology
- **Pipeline:** 0.03 per same-sign pair, cap 0.15
- **Issue:** Nowhere in UI.
- **Fix:** Add section + display penalty value in signal inspector.

### H5. Missing FPI MAD normalization from methodology
- **Pipeline:** `fpi.py:27-37` uses 20-day rolling MAD Z-score
- **Issue:** Methodology describes FPI but not MAD normalization.
- **Fix:** Update FPI section.

### H6. Missing causal exclusion per signal (M.1.1–M.1.3)
- **Pipeline:** COT/Spot/Vol causal exclusion windows
- **Issue:** General "no lookahead" mentioned but no per-signal exclusion rules.
- **Fix:** Add explicit causal window rules table.

### H7. `oi_delta`, `volume_rvol`, `structural_instability` not displayed
- **Pipeline:** All computed and written to `signals` table
- **Issue:** Dropped by `toLatestSignal()` mapper
- **Fix:** Add to mapper + display in signal inspector.

### H8. `special_signal_value` / `special_signal_label` never rendered
- **Pipeline:** On `regime_calls` table: ECB_sentiment, JPY_funding_stress, EM_carry_RBI
- **Issue:** Nowhere in any component
- **Fix:** Add to `LatestRegimeCall` type and render per-pair.

### H9. `getSignalHistory()` only selects 5 columns
- **File:** `queries.ts`
- **Issue:** Only `date, spot, rate_diff_2y, cot_percentile, realized_vol_20d` — misses everything else
- **Fix:** Expand select to include all signal fields.

### H10. ~22 unsafe `as Type[]` casts in queries.ts
- **Fix:** Add runtime validation or use Zod.

### H11. About page "17,000+ validated regime calls"
- **File:** `about/page.tsx` (line 124)
- **Issue:** Hardcoded. May not match actual `validation_log` row count.
- **Fix:** Fetch actual count or audit against DB.

### H12. About page "8 signal families"
- **File:** `about/page.tsx` (line 82)
- **Issue:** Only 6 are composite inputs. Risk reversal, carry, momentum are Layer 1/3 inputs, not composite families.
- **Fix:** Say "6 weighted composite inputs + 3 regime-execution signals" or similar.

### H13. Methodology educational tone violates IDENTITY.md
- **File:** `MethodologyContent.tsx` throughout
- **Issue:** Pedagogical annotations, step-by-step tutorials, Brier score baseline explanation.
- **Fix:** Rewrite as practitioner-to-practitioner. Remove "tutorial" framing. Keep formulas, lose explanatory prose.

### H14. Performance page hardcoded `2026-04-01` production floor
- **File:** `queries.ts` (lines 298, 353)
- **Issue:** Silently excludes all pre-April 2026 data. Makes track record look shorter.
- **Fix:** Remove floor or make it configurable.

### H15. Terminal compare page compares regime cards not raw signals
- **File:** `compare-view.tsx`
- **Issue:** Shows dominance arrays, Markov chains, AI briefs — not rate diffs, COT, vol, FPI.
- **Fix:** Add raw signal comparison columns.

### H16. Terminal performance page has no aggregate pair accuracy stats
- **File:** `performance-ledger-page-content.tsx`
- **Issue:** Only shows individual row outcomes. No win-rate %, avg Brier, Sharpe at pair level.
- **Fix:** Add summary header cards.

---

## 🟠 Medium (P2 — Should-fix)

### M1. OI weight labeled "Implicit in flags" — is explicit 5%
- **File:** `MethodologyContent.tsx` (line 651)
- **Fix:** Say "5% for all pairs".

### M2. Rate weight in sidebar says "25–30%" — all pairs are 30-45%
- **File:** `MethodologyContent.tsx` (line 611)
- **Fix:** Update.

### M3. COT weight in sidebar says "20%" — EURUSD 25%, INR 10%
- **File:** `MethodologyContent.tsx` (line 620)
- **Fix:** Update.

### M4. Signal inspector shows COT row unconditionally for USDINR
- **File:** `signal-inspector.tsx` (lines 314-318)
- **Fix:** Guard with `pair !== "USDINR"`.

### M5. Signal inspector raw inputs missing all macro fields
- **File:** `signal-inspector.tsx`
- **Fix:** Add ECB BS, Bund-BTP, BoJ rate, India VIX, INR forward, OI delta, vol RVOL.

### M6. `CrossAssetMatrix` missing pair-specific tiles
- **File:** `CrossAssetMatrix.tsx`
- **Issue:** Shows generic cross-assets but no pair-specific macro (india_vix, bund_btp_spread, boj_policy_rate)
- **Fix:** Add conditional pair-specific tiles.

### M7. EUR/USD gate 0.55 hardcoded in multiple places
- **Files:** `AccuracyMilestoneTracker.tsx:19`, `queries.ts:1006`
- **Issue:** Other pairs use 0.5. Inconsistent.
- **Fix:** Define per-pair thresholds in config.

### M8. `PAIR_PROFILES.signalWeight` unused
- **File:** `pairProfiles.ts:36`
- **Issue:** `signalWeight: 0.8` for USDINR defined but never applied.
- **Fix:** Remove dead code or wire it up.

### M9. Memo pages don't render `ai_thesis_summary`
- **Files:** `memo/page.tsx`, `memo/[date]/page.tsx`, `memo-sidebar.tsx`
- **Issue:** Fetched but never displayed.
- **Fix:** Render as collapsible section.

### M10. Dead X/Twitter link
- **File:** `about/page.tsx` (line 174)
- **Fix:** Remove or populate.

### M11. `fx-regime/page.tsx` missing — route 404s
- **Fix:** Create redirect to `/terminal`.

### M12. `AlertStrip` and `getWatchlist()` lack explicit USDINR COT guards
- **Files:** `AlertStrip.tsx`, `[pair]/page.tsx`
- **Issue:** Implicitly safe via null checks but fragile.
- **Fix:** Add explicit guard.

### M13. Hardcoded colors throughout `PipelineHealthDashboard` and `ConvexityRadar`
- **Fix:** Use CSS variables.

### M14. Total calls card fallback overstates
- **File:** `performance/page.tsx` (line 273)
- **Issue:** Falls back to `validation.length` which includes NEUTRAL/`—` rows.
- **Fix:** Exclude non-CORRECT/WRONG rows.

---

## 🟢 Low (P3 — Polish)

### L1. Gap-to-gate inverted display
- **File:** `AccuracyMilestoneTracker.tsx:292`
- **Issue:** At 60% shows `-5.0pp` which is correct math but inverted visually.
- **Fix:** Show absolute gap or invert sign.

### L2. Stale threshold 10 days hardcoded
- **File:** `performance/page.tsx` (line 376)
- **Fix:** Config constant.

### L3. Equity curve not labeled as cross-pair aggregate
- **File:** `performance/page.tsx` (lines 333-348)
- **Fix:** Add subtitle.

### L4. Confidence accent threshold `>= 0.55` hardcoded in multiple places
- **Files:** `[pair]/page.tsx:387`, `SignalCard.tsx`
- **Fix:** Config constant.

### L5. Default selected pair "EURUSD" hardcoded in calendar + terminal performance
- **Fix:** No action needed (sensible default).

### L6. Spot formatting `pairMeta.label === "USDJPY" ? 2 : 4` repeated
- **Files:** `[pair]/page.tsx`, `compare-view.tsx`
- **Fix:** Extract helper.

---

## Implementation Phases

### Phase 1: Data Layer Repair (Week 1)
1. Fix `useStrategyLedger` `entry_date` → `date`
2. Add `z_blended` to DB schema + pipeline writer
3. Add `india_vix`, `inr_forward_premium`, `oi_delta`, `volume_rvol`, `structural_instability` to `LatestSignal` + mapper
4. Add `special_signal_value`, `special_signal_label` to `LatestRegimeCall` + mapper
5. Expand `getSignalHistory()` select list
6. Remove `2026-04-01` hardcoded date floor from queries
7. Replace unsafe `as Type[]` casts with runtime validation

### Phase 2: Terminal Accuracy (Week 1-2)
1. Replace hardcoded `SIGNAL_ARCH` with per-pair weight config
2. Fix COT EXTREME threshold to 90/10
3. Fix DollarDominanceIndex INR regime classification
4. Add explicit USDINR COT guards to AlertStrip + getWatchlist
5. Add pair-specific macro tiles to CrossAssetMatrix
6. Add raw signal comparison to Compare page
7. Add aggregate accuracy stats to Terminal Performance

### Phase 3: Methodology Rewrite (Week 2)
1. Update all composite weights to pipeline truth
2. Rewrite EURUSD special signal section (Bund-BTP + ECB BS)
3. Add z_blended section (M.3.2)
4. Add COT smart spread section (M.3.3)
5. Add adaptive weighting section (M.2.1)
6. Add redundancy penalty section (M.2.2)
7. Fix rate Z formula to MAD Z
8. Fix confidence formula with Platt calibration
9. Fix USDJPY confidence bonus text
10. Remove educational tone → practitioner tone
11. Fix SignalDecomposition synthetic data label

### Phase 4: About + Performance + Memo (Week 2-3)
1. Audit "17,000+" claim against actual DB count
2. Fix "8 signal families" → 6 composite inputs
3. Remove dead X link
4. Performance page: use DB stats as source of truth
5. Fix 90-day label vs 30-point window
6. Memo pages: render `ai_thesis_summary`
7. Add diagnostics link verification

### Phase 5: Polish + Config (Week 3)
1. Extract hardcoded thresholds to config constants
2. Extract spot formatting helper
3. Replace raw hex colors with CSS variables
4. Add `fx-regime/page.tsx` redirect
5. Final build + test pass

---

## Test Gate

```bash
cd fx-regime-lab/web && npm run build
cd fx-regime-lab/pipeline && pytest
```

Both must pass before any PR is merged.
