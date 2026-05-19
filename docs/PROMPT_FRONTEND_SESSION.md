# PROMPT: Frontend Session v2.0 — Full Site Repair
> **For:** Coding subagent (Cursor/Kimi)  
> **Scope:** Every page and component in `fx-regime-lab/web/src`  
> **Test gate:** `cd fx-regime-lab/web && npm run build` must pass clean  
> **Style:** Minimal changes. Follow existing patterns. No new dependencies.

---

## Global Constants

Create `fx-regime-lab/web/src/lib/config.ts` (or append to existing constants) with these **source-of-truth values** from the pipeline. Every component must import from here — no more hardcoded weights/thresholds anywhere.

```typescript
// === PAIR COMPOSITE WEIGHTS (from pipeline/src/regime/composite.py) ===
export const PAIR_COMPOSITE_WEIGHTS = {
  EURUSD: { rate: 0.45, cot: 0.25, vol: 0.20, oi: 0.05, special: 0.05, fpi: 0.0 },
  USDJPY: { rate: 0.40, cot: 0.20, vol: 0.25, oi: 0.05, special: 0.10, fpi: 0.0 },
  USDINR: { rate: 0.30, cot: 0.10, vol: 0.20, oi: 0.05, special: 0.20, fpi: 0.15 },
} as const;

// === CROWDING THRESHOLDS (from pipeline/src/signals/cot.py _CROWD_SOFT_HI/LO) ===
export const CROWD_SOFT_HI = 90;
export const CROWD_SOFT_LO = 10;

// === CONFIDENCE CALIBRATION (from pipeline/src/regime/confidence.py) ===
export const PLATT_SCALE = 0.40;
export const PLATT_INTERCEPT = 0.35;

// === BIAS THRESHOLDS (from pipeline src/regime/composite.py) ===
export const BIAS_THRESHOLD = 0.30;

// === ACCENT THRESHOLD (visual only) ===
export const CONFIDENCE_ACCENT = 0.55;

// === STALE THRESHOLD ===
export const STALE_THRESHOLD_DAYS = 10;
```

Then replace ALL hardcoded occurrences of these values across the entire frontend with imports from `config.ts`.

---

## Task 1: Data Layer — `lib/supabase/queries.ts` + `lib/queries.ts`

### 1A. Fix `useStrategyLedger` broken column
**File:** `web/src/lib/queries.ts`  
Find: `order("entry_date", { ascending: false })`  
Replace: `order("date", { ascending: false })`  

### 1B. Add missing DB fields to mappers
**File:** `web/src/lib/supabase/queries.ts`

In `toLatestSignal()`, add these fields to the returned object (they already exist in `signals` table):
- `z_blended: row.z_blended ?? null`
- `india_vix: row.india_vix ?? null`
- `inr_forward_premium: row.inr_forward_premium ?? null`
- `oi_delta: row.oi_delta ?? null`
- `volume_rvol: row.volume_rvol ?? null`
- `structural_instability: row.structural_instability ?? null`
- `ecb_balance_sheet: row.ecb_balance_sheet ?? null`
- `bund_btp_spread: row.bund_btp_spread ?? null`
- `boj_policy_rate: row.boj_policy_rate ?? null`

In `toLatestRegimeCall()`, add:
- `special_signal_value: row.special_signal_value ?? null`
- `special_signal_label: row.special_signal_label ?? null`

**File:** `web/src/lib/queries.ts` (React Query hooks)  
Update `LatestSignalRow` and `LatestRegimeCallRow` types to match.

### 1C. Expand `getSignalHistory()` select
**File:** `web/src/lib/supabase/queries.ts`  
Current select: `date, spot, rate_diff_2y, cot_percentile, realized_vol_20d`  
Expand to include all signal columns that exist in the DB.

### 1D. Remove `2026-04-01` hardcoded floor
**File:** `web/src/lib/supabase/queries.ts`  
Find `gte('date', '2026-04-01')` in `getValidationLogT5T20` and `getRegimeBreakdown`.  
Remove or replace with a configurable constant.

### 1E. Fix unsafe `as Type[]` casts
Replace `as PipelineDayHealth[]`, `as AccuracyAlert[]`, etc. with runtime validation (e.g., `Array.isArray(data) && data.every(isValidHealthRow)`) or use Zod if already installed. If Zod is not installed, use simple `typeof` checks.

---

## Task 2: Terminal Pair Detail Page — `terminal/fx-regime/[pair]/page.tsx`

### 2A. Replace hardcoded `SIGNAL_ARCH`
Find the hardcoded array:
```typescript
const SIGNAL_ARCH = [
  { label: "RATE", weight: 40 },
  { label: "COT", weight: 30 },
  { label: "VOL", weight: 20 },
  { label: "OI", weight: 10 },
];
```
Replace with dynamic lookup:
```typescript
const w = PAIR_COMPOSITE_WEIGHTS[pair as keyof typeof PAIR_COMPOSITE_WEIGHTS];
const SIGNAL_ARCH = [
  { label: "RATE", weight: Math.round(w.rate * 100) },
  ...(pair !== "USDINR" ? [{ label: "COT", weight: Math.round(w.cot * 100) }] : []),
  { label: "VOL", weight: Math.round(w.vol * 100) },
  { label: "OI", weight: Math.round(w.oi * 100) },
  ...(w.special > 0 ? [{ label: "SPECIAL", weight: Math.round(w.special * 100) }] : []),
  ...(w.fpi > 0 ? [{ label: "FPI", weight: Math.round(w.fpi * 100) }] : []),
].filter(Boolean);
```
Apply this same pattern everywhere `SIGNAL_ARCH` is hardcoded (inspector, data-lineage, decomposition).

### 2B. Fix COT EXTREME threshold
Find `> 85` or `< 15` in `getWatchlist()`. Replace with `> CROWD_SOFT_HI` / `< CROWD_SOFT_LO` (90/10).

### 2C. Add explicit USDINR COT guard in `getWatchlist()`
Even if null checks make it safe, add `if (pair === "USDINR") return null` for COT watchlist items.

### 2D. Display pair-specific macro signals
In the signal metrics table (around line 400), add conditional rows:
- If `pair === "EURUSD"` and `sig.ecb_balance_sheet !== null`: show "ECB Balance Sheet"
- If `pair === "EURUSD"` and `sig.bund_btp_spread !== null`: show "Bund-BTP Spread"
- If `pair === "USDJPY"` and `sig.boj_policy_rate !== null`: show "BoJ Policy Rate"
- If `pair === "USDINR"` and `sig.india_vix !== null`: show "India VIX"
- If `pair === "USDINR"` and `sig.inr_forward_premium !== null`: show "INR Forward Premium"
- If `sig.oi_delta !== null`: show "OI Delta" (all pairs)
- If `sig.volume_rvol !== null`: show "Volume RVOL" (all pairs)
- If `sig.structural_instability !== null`: show "Structural Instability" (all pairs)

### 2E. Display `special_signal_value` / `special_signal_label`
In the regime call section, show:
- `call.special_signal_label`: label text
- `call.special_signal_value`: value (formatted to 2 decimals)
Only if non-null.

### 2F. Extract spot formatting helper
Replace repeated `pairMeta.label === "USDJPY" ? 2 : 4` with:
```typescript
export function spotDecimals(pair: string): number {
  return pair === "USDJPY" ? 2 : 4;
}
```

---

## Task 3: Signal Inspector — `components/ui/signal-inspector.tsx`

### 3A. Replace hardcoded `SIGNAL_ARCH` with dynamic per-pair weights
Same pattern as Task 2A.

### 3B. Hide COT row for USDINR
Add guard: `if (pair === "USDINR")` do not render COT Signal row.

### 3C. Expand Raw Inputs section
Add all missing fields:
- `z_blended`
- `ecb_balance_sheet`
- `bund_btp_spread`
- `boj_policy_rate`
- `india_vix`
- `inr_forward_premium`
- `oi_delta`
- `volume_rvol`
- `structural_instability`
- `special_signal_value`
- `special_signal_label`

Render with conditional rendering (only show if non-null).

---

## Task 4: Methodology Content — `app/methodology/MethodologyContent.tsx`

### 4A. Update all composite weight descriptions
Replace static weight text with per-pair weights from `PAIR_COMPOSITE_WEIGHTS`.

### 4B. Rewrite EURUSD special signal section
Old: "placeholder (returns 0.0)"  
New: "Bund-BTP spread (Italian sovereign stress) blended with ECB balance sheet YoY growth rate. Computed as dual-horizon MAD Z-score."

### 4C. Add z_blended section (M.3.2)
Add subsection under Rate Differentials:  
"z_blended: 60% tactical (252d) + 40% structural (2520d real 10Y) MAD Z-score. Tactical captures near-term momentum; structural captures secular valuation."

### 4D. Add COT smart spread section (M.3.3)
Add subsection under COT:  
"COT smart spread: 70% traditional non-commercial net-long percentile + 30% (asset-manager minus leveraged-money) spread. Reduces noise from speculator repositioning."

### 4E. Add adaptive precision weighting section (M.2.1)
Add subsection under Composite:  
"Precision weights: static weights scaled by |Spearman beta| / 0.10, floored at 10%. Signals with stronger historical predictive power receive higher effective weight."

### 4F. Add redundancy penalty section (M.2.2)
Add subsection:  
"Redundancy penalty: 0.03 per same-sign pair, capped at 0.15. Prevents overconfidence when correlated signals (rate + carry) align."

### 4G. Fix rate Z formula
Replace Gaussian z formula with MAD Z:  
`z = (x_t − median_{252d}) / (MAD_{252d} × 1.4826)`

### 4H. Fix confidence formula
Add Platt calibration step:  
`confidence_calibrated = clip(0.35 + 0.40 × confidence_raw, 0.0, 1.0)`  
Note: max calibrated confidence ≈ 0.71 even if raw reaches 0.90.

### 4I. Fix USDJPY confidence bonus text
Change "carry signal > 0.5" → "special signal > 0.5".

### 4J. Tone rewrite — IDENTITY.md compliance
Remove pedagogical framing. Examples:
- Delete: "This means the model cannot see the future."
- Delete: "Think of it as a Schmitt trigger..."
- Keep: formulas, thresholds, data sources
- Replace: "We use" → "System uses"; "You can think of" → delete; tutorial steps → bullet facts

### 4K. Fix Signal Families sidebar
- Rate weight: "30–45% (pair-specific)"
- COT weight: "10–25% (pair-specific)"
- OI weight: "5% (explicit, all pairs)"
- Remove "Risk Reversal" from signal families list (it's a Layer 3 input)

---

## Task 5: Signal Decomposition — `components/methodology/SignalDecomposition.tsx`

### 5A. Fix "Live Example" label
If still using synthetic data, change title to: `"Illustrative Example (Synthetic Data)"`  
**OR** fetch real latest signal via a small API call / prop.

### 5B. Update weights to match EURUSD pipeline truth
Special signal: 5% (not omitted). OI: 5% (not 10%).

### 5C. Fix EURUSD special signal text
Same as 4B.

---

## Task 6: About Page — `app/about/page.tsx`

### 6A. Fix "8 signal families"
Change to: `"6 weighted composite inputs + 3 regime-execution signals"` or `"6 signal families (rate, COT, volatility, open interest, special, FPI)"`

### 6B. Audit or remove "17,000+ validated regime calls"
Either:
- Fetch actual count from `validation_log` row count (server component)
- Or remove the hardcoded number

### 6C. Remove dead X/Twitter link
Either set real href or remove the entry.

---

## Task 7: Performance Page — `app/performance/page.tsx` + components

### 7A. Use DB stats as source of truth
In `computeStatsFromLog`, do NOT override `winRate`, `brierScore`, `sampleSize` from DB `validation_stats`. Use DB values directly. Only compute rolling 90d from log dates.

### 7B. Fix "Total calls" fallback
Exclude NEUTRAL and `—` rows from fallback count.

### 7C. Fix 90-Day label vs 30-point window
Option A: Change label to "30-Call Window Accuracy"  
Option B: Pass 90 days of daily history (not 30 rolling windows)

### 7D. Add equity curve subtitle
Add text: `"Cross-pair aggregate log-returns"` below chart title.

### 7E. Fix hardcoded EUR/USD gate in AccuracyMilestoneTracker
Read from per-pair config: EURUSD = 0.55, others = 0.50.

---

## Task 8: Brief Page — `app/brief/page.tsx`

### 8A. Fix DollarDominanceIndex INR misclassification
Replace naive substring matching with `classifyRegime()` from `regime-classifier.ts`.
For USDINR:
- `INR_APPRECIATION` → USD WEAK
- `INR_DEPRECIATION` → USD STRONG
- All other regimes → neutral

---

## Task 9: CrossAssetMatrix — `components/dashboard/CrossAssetMatrix.tsx`

### 9A. Add pair-specific macro tiles
Below the generic cross-asset grid, add conditional tiles:
- EURUSD: ECB BS, Bund-BTP spread
- USDJPY: BoJ rate
- USDINR: India VIX, INR forward premium

Fetch from `getLatestSignals()` or `getCrossAssetSnapshot()` (add fields if needed).

---

## Task 10: Memo Pages — `app/memo/page.tsx` + `[date]/page.tsx` + sidebar

### 10A. Render `ai_thesis_summary`
In the memo detail page, below `raw_content`, add a collapsible section:
```
[ ▼ AI Thesis Summary ]
{memo.ai_thesis_summary}
```
Handle JSON type — stringify if it's an object.

---

## Task 11: Missing Route + Misc

### 11A. Create `app/terminal/fx-regime/page.tsx`
Simple redirect: `redirect("/terminal")`.

### 11B. Extract hardcoded thresholds to `config.ts`
Search all files for:
- `0.55`, `0.50`, `0.30`, `0.05`, `0.10`, `0.15`, `90`, `10`, `85`, `15`, `8`
Replace with config imports where they correspond to pipeline constants.

---

## Task 12: Type Safety + Build

### 12A. Update `database.types.ts`
Ensure all new fields (`z_blended`, etc.) are in the generated types.

### 12B. Build check
```bash
cd fx-regime-lab/web && npm run build
```
Fix all TypeScript errors.

### 12C. Biome check
```bash
cd fx-regime-lab/web && npx biome check --write .
```

---

## Cross-Cutting Rules

1. **No new dependencies.** Use existing React, Next.js, Tailwind, Supabase.
2. **Follow existing patterns.** If a component uses `cn()` for classes, keep using it. If it uses server components, keep server components.
3. **Minimal diffs.** Don't refactor unrelated code.
4. **USDINR COT = null.** Always guard. Never show COT UI for USDINR.
5. **IDENTITY.md tone.** Practitioner-to-practitioner. No "we", no "you", no tutorials. Facts, thresholds, sources.
6. **DB = source of truth.** When pipeline and frontend disagree, frontend changes. Never the reverse.
