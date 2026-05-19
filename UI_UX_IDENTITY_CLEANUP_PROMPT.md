# UI/UX Identity Cleanup Prompt

> **Context:** This is a hard-constraint cleanup task. The project has an `IDENTITY.md` that defines what FX Regime Lab is and is not. Several UI elements currently violate that identity. This prompt contains ALL required frontend changes. Do NOT add, remove, or reinterpret any item.

---

## Rule: Identity-First

Before modifying any file, read `IDENTITY.md` in the project root. Every change must align with these hard constraints:
- **Not a signal service.** No execution advice. No position sizing. No stop levels in public output.
- **Not educational.** Never "educational purposes," "learning," or explanatory tone. Practitioner-to-practitioner only.
- **Not a backtesting showcase.**
- **Not a fintech product.** No monetization layer.

---

## Task List (Complete All)

### 1. Remove `position_size` from public UI display

**Files to modify:**
- `web/src/app/terminal/fx-regime/[pair]/page.tsx`
  - Find the `position_size` display in the pair desk panel (around line 356). Remove the row/cell that renders `call?.position_size`. If it's inside a grid of metrics, adjust grid columns so layout doesn't break.
  - Also remove `call?.position_size != null` from any conditional check that gates display of a section.
  
- `web/src/components/dashboard/SignalCard.tsx`
  - Find the `position_size` render (around line 279). Remove it. Adjust surrounding layout if needed.

- `web/src/components/ui/data-lineage.tsx`
  - Find the `position_size` field in the data lineage component (around line 195-200). Remove the entire lineage row for position sizing. The row label is something like "Confidence × vol rank → position sizing tier".
  - Remove `position_size` from the `call` prop type/interface in this file.

**What to keep:** `position_size` can remain in the database query layer (`queries.ts`) and database types — just don't render it in UI.

---

### 2. Remove `stop_level` from public UI display

**Files to modify:**
- `web/src/app/terminal/fx-regime/[pair]/page.tsx`
  - Find the `stop_level` display (around line 364-365). Remove the row/cell that renders `call.stop_level.toFixed(...)`. Adjust layout.
  - Remove `call?.stop_level != null` from any conditional check.

- `web/src/components/dashboard/SignalCard.tsx`
  - Find the `stop_level` render (around line 289-290). Remove it. Adjust layout.

- `web/src/components/ui/data-lineage.tsx`
  - Find the `stop_level` field in the data lineage component (around line 203-211). Remove the entire lineage row for stop level. The row label is something like "Spot ± 0.5% buffer → hypothetical stop level".
  - Remove `stop_level` from the `call` prop type/interface in this file.

**What to keep:** `stop_level` can remain in database query layer and types — just don't render it in UI.

---

### 3. Fix educational language in disclaimer

**File:** `web/src/components/ui/research-disclaimer.tsx`

**Current:**
```
[RESEARCH ONLY] For research and educational purposes only. These regime classifications are
derived from a deterministic 3-layer signal framework and validated out-of-sample. Not investment advice.
```

**Change to:**
```
[RESEARCH ONLY] For research purposes only. These regime classifications are
derived from a deterministic 3-layer signal framework and validated out-of-sample. Not investment advice.
```

(Remove the word "educational" and the "and" before it.)

---

### 4. Fix educational language in brief page footer

**File:** `web/src/app/brief/page.tsx` (around line 315)

**Current:**
```
RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE. ALL CALLS LOGGED PRIOR TO MARKET OPEN.
```

**Change to:**
```
RESEARCH ONLY. NOT INVESTMENT ADVICE. ALL CALLS LOGGED PRIOR TO MARKET OPEN.
```

---

### 5. Fix signal-framing language in about page

**File:** `web/src/app/about/page.tsx` (around line 56-58, inside AuthorIdentity bio)

**Current:**
```
Built FX Regime Lab to bridge the gap between institutional-grade
quantitative research and publicly accessible daily signals.
```

**Change to:**
```
Built FX Regime Lab to bridge the gap between institutional-grade
quantitative research and publicly accessible daily regime classifications.
```

(Replace "signals" with "regime classifications".)

---

### 6. Reframe LinkedIn sharing from "ALERT" to "NOTE"

**File:** `web/src/components/ui/desk-card.tsx` (around line 560-606)

**Current button text:** `[ COPY LINKEDIN ALPHA ]`

**Change to:** `[ SHARE REGIME NOTE ]`

This is just a button label change. The underlying API call to `/api/linkedin-alpha-hook` stays the same — the backend prompt reframing will be handled separately.

---

### 7. Verify no layout breaks

After removing `position_size` and `stop_level` from pair desk and SignalCard:
- Check that grid layouts don't have empty gaps
- Ensure the remaining metrics (spot price, regime, confidence, signal composite, directional bias, driver, risk flags) still render cleanly
- Run `cd web && npx tsc --noEmit` to confirm no TypeScript errors from removed props
- Run `cd web && npm run build` to confirm build passes

---

## Files You Will Modify

1. `web/src/app/terminal/fx-regime/[pair]/page.tsx`
2. `web/src/components/dashboard/SignalCard.tsx`
3. `web/src/components/ui/data-lineage.tsx`
4. `web/src/components/ui/research-disclaimer.tsx`
5. `web/src/app/brief/page.tsx`
6. `web/src/app/about/page.tsx`
7. `web/src/components/ui/desk-card.tsx`

## Verification Checklist

- [ ] `position_size` no longer appears on any public page (pair desk, SignalCard, data lineage)
- [ ] `stop_level` no longer appears on any public page (pair desk, SignalCard, data lineage)
- [ ] Research disclaimer no longer contains "educational"
- [ ] Brief page footer says "RESEARCH ONLY" not "RESEARCH AND LEARNING ONLY"
- [ ] About page bio says "regime classifications" not "signals"
- [ ] LinkedIn button says "SHARE REGIME NOTE" not "COPY LINKEDIN ALPHA"
- [ ] `npx tsc --noEmit` passes zero errors
- [ ] `npm run build` passes zero errors
- [ ] `npx biome check . --changed` is clean

## What NOT to Touch

- Do NOT delete `position_size` or `stop_level` from database types (`database.types.ts`)
- Do NOT delete `position_size` or `stop_level` from Supabase queries (`queries.ts`)
- Do NOT modify the LinkedIn alpha hook API route (`web/src/app/api/linkedin-alpha-hook/route.ts`)
- Do NOT modify the methodology page content
- Do NOT modify pipeline/backend code
- Do NOT add new features, animations, or design changes
