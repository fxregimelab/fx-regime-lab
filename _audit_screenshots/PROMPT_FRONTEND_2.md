# PROMPT: Frontend Session — MEDIUM PRIORITY (Polish & Features)
## Tool: Terminal in `D:\Projects\fx_regime_lab\fx-regime-lab\web`
## Run: `npm run build` and `npm run lint` after ALL changes

---

## Fix 5: Performance Page — Add Per-Pair Accuracy Cards

**File:** `web/src/app/performance/page.tsx`  
**Where:** Below the aggregate stats hero (after the 5 big stat cards, before EURUSD accuracy gauge)  

**What to add:** A row of 3 small cards showing per-pair rolling accuracy:

```tsx
{/* Per-Pair Accuracy Breakdown */}
<div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
  {[
    { pair: "EUR/USD", gate: 0.55, gateLabel: "55%" },
    { pair: "USD/JPY", gate: 0.50, gateLabel: "50%" },
    { pair: "USD/INR", gate: 0.50, gateLabel: "50%" },
  ].map(({ pair, gate, gateLabel }) => {
    const acc = accuracyByPair[pair];
    const val = acc?.rolling30 ?? acc?.overall ?? null;
    const isAbove = val != null && val >= gate;
    const isWarning = val != null && val >= gate - 0.05 && val < gate;
    return (
      <div
        key={pair}
        className="border border-[var(--color-border-subtle)] bg-[var(--color-surface)] p-4"
      >
        <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] uppercase">
          {pair} Accuracy (30D)
        </p>
        <p
          className={`font-mono text-[24px] font-bold tabular-nums mt-1 ${
            isAbove
              ? "text-[var(--color-up)]"
              : isWarning
                ? "text-[var(--color-warning)]"
                : "text-[var(--color-down)]"
          }`}
        >
          {val != null ? `${(val * 100).toFixed(1)}%` : "—"}
        </p>
        <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-1">
          Gate: {gateLabel}
          {val != null && val < gate && (
            <span className="text-[var(--color-down)] ml-1">
              [BELOW GATE]
            </span>
          )}
        </p>
      </div>
    );
  })}
</div>
```

**Data source:** The `accuracyByPair` object should already be computed in the page. If not, compute it from the validation log data that's already fetched.

---

## Fix 6: Status Bar — Health-Linked Messaging

**File:** `web/src/components/dashboard/SystemStatusBar.tsx`  
**Problem:** When pipeline fails, the bar still says "System integrity verified".

**Current logic:** The left side always shows "System integrity verified".

**Fix:** Make the left message dynamic based on `pipelineStatus`:

```tsx
const statusMessage = useMemo(() => {
  if (pipelineStatus === "FAILED") return { text: "System integrity check: FAILED", color: "text-[var(--color-down)]" };
  if (pipelineStatus === "INTERRUPTED" || pipelineStatus === "UNKNOWN") return { text: "System integrity check: STALE", color: "text-[var(--color-warning)]" };
  return { text: "System integrity verified", color: "text-[var(--color-text-muted)]" };
}, [pipelineStatus]);
```

Replace the static text with:
```tsx
<span className={`font-mono text-[10px] ${statusMessage.color}`}>
  {statusMessage.text}
  {lastUpdate && ` · ${lastUpdate}`}
</span>
```

---

## Fix 7: Calendar — Expand Cryptic Tooltip Text

**File:** `web/src/app/terminal/calendar-tab.tsx` or `web/src/components/ui/convexity-radar.tsx`  
**Problem:** "N < 5 · VOL ONLY" is meaningless to most users.

**Find:** Wherever the calendar renders the `MIE×RV20` and `N < 5` text.

**Fix:** Wrap the text in a tooltip (using a `title` attribute or a custom tooltip component):

```tsx
<span
  className="font-mono text-[9px] text-[var(--color-text-muted)] cursor-help"
  title="Macro Impact Estimate × Realized Vol (20d). Insufficient historical samples for this event type (< 5 similar past events). Using volatility-only projection."
>
  [ N &lt; 5 · VOL ONLY ]
</span>
```

Do this for ALL cryptic status badges in the calendar.

---

## Fix 8: Brief Page — Empty State Enhancement

**File:** `web/src/app/brief/page.tsx`  
**Problem:** "No brief available for today" is a dead end.

**Find:** The empty state rendering (where it shows the "No brief available" message).

**Fix:** Add below the empty state message:

```tsx
{/* Empty state enhancement */}
<div className="mt-8 space-y-4">
  {latestBriefDate && (
    <a
      href={`/brief?date=${latestBriefDate}`}
      className="inline-flex items-center gap-2 px-4 py-2 border border-[var(--color-border-subtle)] text-[var(--color-text)] font-mono text-[11px] hover:bg-[var(--color-elevated)] transition-colors"
    >
      ← View latest brief ({latestBriefDate})
    </a>
  )}
  
  {/* Preview card based on current regime snapshot */}
  <div className="border border-[var(--color-border-subtle)] bg-[var(--color-surface)] p-4 mt-4">
    <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] uppercase mb-2">
      Today&apos;s Regime Snapshot
    </p>
    <div className="flex gap-4">
      {latestCalls.map((call) => (
        <div key={call.pair} className="flex-1">
          <p className="font-mono text-[10px] text-[var(--color-text-muted)]">{call.pair}</p>
          <p className="font-mono text-[14px] font-bold">{call.regime?.replace(/_/g, " ") ?? "—"}</p>
        </div>
      ))}
    </div>
  </div>
</div>
```

**Note:** `latestBriefDate` and `latestCalls` need to be fetched. If the data is already available in the page, use it. If not, you may need to add a query for the most recent brief.

---

## Fix 9: Methodology — Add Pipeline Flowchart SVG

**File:** `web/src/app/methodology/MethodologyContent.tsx` (or wherever the methodology page content lives)  
**Where:** At the top, right after the "Signal Architecture" intro paragraph and before "Layer 1 — Regime Gate".

**What to add:** A simple SVG flowchart showing the 3-layer pipeline.

Create a new component file `web/src/components/methodology/PipelineFlowchart.tsx`:

```tsx
export function PipelineFlowchart() {
  return (
    <div className="my-8 p-6 border border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
      <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] uppercase mb-4 text-center">
        Three-Layer Pipeline
      </p>
      <div className="flex items-center justify-center gap-2 flex-wrap">
        {/* Layer 1 */}
        <div className="text-center px-4 py-3 border border-[var(--color-border-subtle)] bg-[var(--color-void)] min-w-[140px]">
          <p className="font-mono text-[10px] text-[var(--color-text-muted)]">LAYER 1</p>
          <p className="font-mono text-[12px] font-bold text-[var(--color-text)]">Regime Gate</p>
          <p className="font-mono text-[8px] text-[var(--color-text-dim)] mt-1">Rate · COT · Vol · OI</p>
        </div>
        
        <span className="text-[var(--color-text-muted)]">→</span>
        
        {/* Layer 2 */}
        <div className="text-center px-4 py-3 border border-[var(--color-border-subtle)] bg-[var(--color-void)] min-w-[140px]">
          <p className="font-mono text-[10px] text-[var(--color-text-muted)]">LAYER 2</p>
          <p className="font-mono text-[12px] font-bold text-[var(--color-text)]">Composite Score</p>
          <p className="font-mono text-[8px] text-[var(--color-text-dim)] mt-1">Beta weights · Redundancy penalty</p>
        </div>
        
        <span className="text-[var(--color-text-muted)]">→</span>
        
        {/* Layer 3 */}
        <div className="text-center px-4 py-3 border border-[var(--color-border-subtle)] bg-[var(--color-void)] min-w-[140px]">
          <p className="font-mono text-[10px] text-[var(--color-text-muted)]">LAYER 3</p>
          <p className="font-mono text-[12px] font-bold text-[var(--color-text)]">Regime Call</p>
          <p className="font-mono text-[8px] text-[var(--color-text-dim)] mt-1">Platt calibration · Accuracy gate</p>
        </div>
      </div>
      
      {/* Feedback loop */}
      <div className="mt-3 text-center">
        <p className="font-mono text-[8px] text-[var(--color-text-dim)]">
          ↓ T+5 / T+20 validation → immutable audit log ← back to weight calibration
        </p>
      </div>
    </div>
  );
}
```

Then import and render `<PipelineFlowchart />` in the methodology page.

---

## Post-Fix Verification

```bash
cd D:/Projects/fx_regime_lab/fx-regime-lab/web
npx tsc --noEmit
npm run build
npm run lint
```

---

### Done. Report back: "Frontend medium-priority fixes applied. Build + lint clean."
