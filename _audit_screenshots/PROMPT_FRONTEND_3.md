# PROMPT: Frontend Session — LOW PRIORITY (Nice-to-Have Polish)
## Tool: Terminal in `D:\Projects\fx_regime_lab\fx-regime-lab\web`
## Run: `npm run build` and `npm run lint` after ALL changes

---

## Fix 10: Keyboard Shortcuts for Terminal Navigation

**File:** Create `web/src/hooks/use-terminal-shortcuts.ts`

```tsx
"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

const PAIR_SHORTCUTS: Record<string, string> = {
  "1": "/terminal/fx-regime/eurusd",
  "2": "/terminal/fx-regime/usdjpy",
  "3": "/terminal/fx-regime/usdinr",
};

const TAB_SHORTCUTS: Record<string, string> = {
  o: "/terminal",
  c: "/terminal/calendar",
  t: "/terminal/performance",
  m: "/terminal/memos",
};

export function useTerminalShortcuts() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      // Ignore if typing in input/textarea
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      )
        return;

      // Ignore with modifiers
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      const key = e.key.toLowerCase();

      // Pair shortcuts (only in terminal)
      if (pathname?.startsWith("/terminal")) {
        if (PAIR_SHORTCUTS[key]) {
          e.preventDefault();
          router.push(PAIR_SHORTCUTS[key]);
          return;
        }
        if (TAB_SHORTCUTS[key]) {
          e.preventDefault();
          router.push(TAB_SHORTCUTS[key]);
          return;
        }
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [router, pathname]);
}
```

**Then add to `web/src/app/terminal/layout.tsx`**:

```tsx
import { useTerminalShortcuts } from "@/hooks/use-terminal-shortcuts";

// Inside the layout component:
useTerminalShortcuts();
```

**Optional:** Add a small keyboard hint panel in the terminal nav:
```
[1] EUR/USD  [2] USD/JPY  [3] USD/INR  [O] Overview  [C] Calendar  [T] Track  [M] Memos
```

---

## Fix 11: Confidence Chart — Add Accent Threshold Reference Line

**File:** Find where the confidence trend chart is rendered in the inspector.  
**Likely:** `web/src/components/ui/signal-inspector.tsx` or a chart component it uses.

**What to add:** A horizontal dashed line at the accent threshold (55%) so users can see how far confidence is from "high confidence".

If using a recharts `<AreaChart>` or similar:

```tsx
<ReferenceLine
  y={CONFIDENCE_ACCENT * 100}
  stroke="var(--terminal-warning)"
  strokeDasharray="3 3"
  strokeWidth={1}
  label={{
    value: "Accent",
    position: "right",
    fill: "var(--terminal-warning)",
    fontSize: 9,
    fontFamily: "monospace",
  }}
/>
```

If using a custom SVG chart, add a `<line>` element at the 55% Y position.

---

## Fix 12: Regime Timeline — Larger Squares + Hover Tooltips

**File:** Find the regime timeline component in the inspector or pair detail page.

**Current:** Tiny squares, no tooltips.

**Fix:** Increase square size slightly and add hover tooltips showing date + regime:

```tsx
<div
  className="w-[10px] h-[10px] cursor-pointer hover:ring-1 hover:ring-white transition-all"
  style={{ backgroundColor: regimeColor }}
  title={`${date}: ${regime.replace(/_/g, " ")}`}
/>
```

If the current size is smaller (e.g., 6px), increase to 10px. If already 10px, leave as-is and just add the `title` tooltip.

---

## Fix 13: Per-Card "Last Updated" Timestamp

**File:** `web/src/components/dashboard/SignalCard.tsx` or `web/src/app/terminal/page.tsx`  
**Where:** Bottom-right corner of each pair card (terminal overview).

**Add:**
```tsx
{signal?.date && (
  <p className="absolute bottom-2 right-2 font-mono text-[8px] text-[var(--color-text-dim)]">
    {signal.date}
  </p>
)}
```

If the card doesn't have `position: relative`, add `className="relative ..."` to the card container.

---

## Fix 14: Inspector Data Freshness Banner

**File:** `web/src/components/ui/signal-inspector.tsx`  
**Where:** At the very top of the inspector drawer content, before "Current Regime".

**Add:**
```tsx
{signalDate && (
  <div className="flex items-center justify-between py-1.5 px-2 bg-[var(--terminal-bg)] border border-[var(--terminal-border-subtle)] mb-4">
    <p className="font-mono text-[9px] text-[var(--terminal-fg-dim)]">
      Source: {pairLabel} desk
    </p>
    <p className="font-mono text-[9px] text-[var(--terminal-fg-dim)]">
      Last update: {signalDate}
    </p>
  </div>
)}
```

This requires passing `signalDate` as a prop to `SignalInspector`. If it's already available (e.g., from `signal.date`), use it.

---

## Post-Fix Verification

```bash
cd D:/Projects/fx_regime_lab/fx-regime-lab/web
npx tsc --noEmit
npm run build
npm run lint
```

---

### Done. Report back: "Frontend low-priority polish applied. Build + lint clean."
