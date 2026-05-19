# PROMPT: Frontend Session — HIGH PRIORITY FIXES (Bugs)
## Tool: Terminal in `D:\Projects\fx_regime_lab\fx-regime-lab\web`
## Run: `npm run build` and `npm run lint` after ALL changes before committing

---

## Fix 1: Validation History PRED Column Shows "—" (Missing Join)

**File:** `web/src/lib/supabase/queries.ts`  
**Line:** ~425-475 (`getValidationLogForPair`)  
**Problem:** The `predicted` field is hardcoded to `"—"` because `validation_log` table does NOT have `predicted_direction`. It has `call_id` which references `regime_calls`.

**Fix:** Update `getValidationLogForPair` to join with `regime_calls` via `call_id`:

**Current query:**
```typescript
const { data, error } = await supabase
  .from("validation_log")
  .select("*")
  .eq("pair", code)
  .not("brier_score_t5", "is", null)
  .order("date", { ascending: false })
  .limit(limit);
```

**New query:**
```typescript
const { data, error } = await supabase
  .from("validation_log")
  .select("*, regime_calls!inner(predicted_direction)")
  .eq("pair", code)
  .not("brier_score_t5", "is", null)
  .order("date", { ascending: false })
  .limit(limit);
```

**Then update the mapping:**
```typescript
return (data as ValidationLogRow[]).map((r) => ({
  date: r.date,
  pair: PAIR_DISPLAY[r.pair] ?? r.pair,
  predicted: (r as any).regime_calls?.predicted_direction ?? "—",
  ...
```

**If the join fails** (FK relationship not configured in Supabase), use the fallback approach:
1. Fetch `validation_log` rows as before
2. Extract all `call_id`s
3. Fetch `regime_calls` rows for those IDs
4. Merge `predicted_direction` into the result

**Also fix `getValidationLogT5T20`** (~309) and `getValidationLog` (~217) with the same join pattern if they also need predicted direction.

**Note:** The `ValidationRowT5` type may need `predicted: string | null` added if not already present.

---

## Fix 2: Inspector Raw Inputs — Add Section Headers + Dim Null Rows

**File:** `web/src/components/ui/signal-inspector.tsx`  

### Part A: Add a `SectionHeader` component
Add this helper after the `Row` component (~line 189):

```tsx
function SectionHeader({ label }: { label: string }) {
  return (
    <div className="px-3 py-1.5 bg-[var(--terminal-bg)] border-b border-[var(--terminal-border-subtle)]">
      <p className="font-mono text-[8px] tracking-widest text-[var(--terminal-fg-dim)] uppercase">
        {label}
      </p>
    </div>
  );
}
```

### Part B: Group raw inputs into sections
Replace the entire `Raw Inputs` block (~lines 360-422) with:

```tsx
{/* ── Raw Inputs ──────────────────────────────────────── */}
<div>
  <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase mb-2">
    Raw Inputs
  </p>
  <div className="border border-[var(--terminal-border-subtle)] bg-[var(--terminal-bg-sunken)]">
    {/* Rate Section */}
    <SectionHeader label="Rate" />
    <Row label="Spot" value={fmt2(spot)} highlight />
    <Row label="Rate Diff 2Y" value={fmt2(rateDiff2y)} sub="bps" />
    <Row label="Rate Diff 10Y" value={fmt2(rateDiff10y)} sub="bps" />
    <Row label="Rate Z (Tactical)" value={fmt2(rateZTactical)} />
    <Row label="Rate Z (Structural)" value={fmt2(rateZStructural)} />
    {zBlended != null && (
      <Row label="Rate Z (Blended)" value={fmt2(zBlended)} />
    )}

    {/* Positioning Section */}
    <SectionHeader label="Positioning" />
    {pairLabel !== "USDINR" && (
      <Row label="COT net position pctile" value={fmt2(cotNetPositionPctile)} />
    )}
    <Row label="OI Delta" value={fmt2(oiDelta)} />

    {/* Volatility Section */}
    <SectionHeader label="Volatility" />
    <Row label="Realized Vol 20D" value={fmt2(realizedVol20d)} sub="%" />
    <Row label="Realized Vol 5D" value={fmt2(realizedVol5d)} sub="%" />
    <Row label="Implied Vol 30D" value={fmt2(impliedVol30d)} sub="%" />
    <Row label="Day Change" value={fmtPct(dayChangePct)} />

    {/* Cross-Asset Section */}
    <SectionHeader label="Cross-Asset" />
    <Row label="Cross-Asset US10Y" value={fmt2(crossAssetUs10y)} />
    <Row label="Skew Alignment" value={fmt2(skewAlignment)} />
    <Row label="Breakeven Inflation 10Y" value={fmt2(breakevenInflation10y)} sub="%" />

    {/* Special Section */}
    <SectionHeader label="Special" />
    {ecbBalanceSheet != null && (
      <Row label="ECB Balance Sheet" value={fmt2(ecbBalanceSheet)} />
    )}
    {bundBtpSpread != null && (
      <Row label="Bund-BTP Spread" value={fmt2(bundBtpSpread)} />
    )}
    {bojPolicyRate != null && (
      <Row label="BoJ Policy Rate" value={fmt2(bojPolicyRate)} />
    )}
    {indiaVix != null && (
      <Row label="India VIX" value={fmt2(indiaVix)} />
    )}
    {inrForwardPremium != null && (
      <Row label="INR Forward Premium" value={fmt2(inrForwardPremium)} />
    )}
    {volumeRvol != null && (
      <Row label="Volume RVOL" value={fmt2(volumeRvol)} />
    )}
    <Row label="Structural Instability" value={structuralInstability ? "YES" : "NO"} />
    {specialSignalValue != null && specialSignalLabel != null && (
      <Row
        label={specialSignalLabel}
        value={specialSignalValue.toFixed(2)}
      />
    )}
  </div>
</div>
```

**Note:** The `cotNetPositionPctile` prop needs to be added to `SignalInspectorProps`. Check what prop holds the COT percentile value — it may already exist under a different name (search the component props).

---

## Fix 3: Track Record "[ = ]" → "PENDING"

**File:** `web/src/components/ui/alpha-ledger.tsx`  
**Line:** 21-25  
**Problem:** Unresolved hits show `[ = ]` which looks like a rendering bug.

**Current:**
```typescript
export function hitAuditMark(v: number | null | undefined): string {
  if (v === 1) return "[ ✓ ]";
  if (v === 0) return "[ ✕ ]";
  return "[ = ]";
}
```

**Fix:**
```typescript
export function hitAuditMark(v: number | null | undefined): string {
  if (v === 1) return "[ ✓ ]";
  if (v === 0) return "[ ✕ ]";
  return "PENDING";
}
```

**Also update the CSS class:**
```typescript
function hitAuditClass(v: number | null | undefined): string {
  if (v === 1) return "text-white font-bold";
  if (v === 0) return "text-[#555] font-light";
  return "text-[var(--terminal-fg-dim)] font-normal italic";
}
```

---

## Fix 4: Compare Page "+—%" → "N/A"

**File:** `web/src/components/ui/compare-view.tsx`  
**Line:** ~100-114  
**Problem:** When `day_change_pct` is null, the code shows `+—%` (green color because `null >= 0` is `true` in JS).

**Current:**
```tsx
<span
  className={
    (sig?.day_change_pct as number) >= 0
      ? "text-[var(--color-up)]"
      : "text-[var(--color-down)]"
  }
>
  {(sig?.day_change_pct as number) >= 0 ? "+" : ""}
  {(sig?.day_change_pct as number)?.toFixed(2) ?? "—"}%
</span>
```

**Fix:**
```tsx
{sig?.day_change_pct == null ? (
  <span className="text-[var(--color-text-muted)]">N/A</span>
) : (
  <span
    className={
      sig.day_change_pct >= 0
        ? "text-[var(--color-up)]"
        : "text-[var(--color-down)]"
    }
  >
    {sig.day_change_pct >= 0 ? "+" : ""}
    {sig.day_change_pct.toFixed(2)}%
  </span>
)}
```

---

## Post-Fix Verification Commands

```bash
cd D:/Projects/fx_regime_lab/fx-regime-lab/web

# Type check
npx tsc --noEmit

# Build
npm run build

# Lint
npm run lint
```

**All three must pass with zero errors.**

---

### Done. Report back: "Frontend high-priority fixes applied. Build + lint clean."
