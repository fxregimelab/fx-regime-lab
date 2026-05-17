import { SHIMMER_DARK } from "./shimmer";

/** Structured skeleton matching SignalCard proportions.
 *  Not a generic pulse blob — every block maps to a real text element.
 */
export function SignalCardSkeleton() {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="px-5 py-4 border-b border-[var(--color-border)]">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className={`${SHIMMER_DARK} w-10 h-3`} />
            <span className={`${SHIMMER_DARK} w-16 h-2`} />
          </div>
          <span className={`${SHIMMER_DARK} w-12 h-2`} />
        </div>
        <div className="mt-3">
          <span className={`${SHIMMER_DARK} w-24 h-7`} />
        </div>
        <span className={`${SHIMMER_DARK} mt-2 block w-32 h-2`} />
      </div>

      {/* ── Sparkline ─────────────────────────────────────────── */}
      <div className="px-5 py-3 border-b border-[var(--color-border)]">
        <span className={`${SHIMMER_DARK} block w-full h-10`} />
      </div>

      {/* ── Layer 1: Regime Gate ──────────────────────────────── */}
      <div className="px-5 py-3 border-b border-[var(--color-border-subtle)]">
        <span className={`${SHIMMER_DARK} mb-2 block w-20 h-2`} />
        <span className={`${SHIMMER_DARK} block w-40 h-3`} />
      </div>

      {/* ── Layer 2: Directional ──────────────────────────────── */}
      <div className="px-5 py-3 border-b border-[var(--color-border-subtle)]">
        <span className={`${SHIMMER_DARK} mb-2 block w-24 h-2`} />
        <div className="grid grid-cols-2 gap-2">
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
        </div>
      </div>

      {/* ── Layer 3: Execution ────────────────────────────────── */}
      <div className="px-5 py-3 border-b border-[var(--color-border-subtle)]">
        <span className={`${SHIMMER_DARK} mb-2 block w-20 h-2`} />
        <div className="grid grid-cols-2 gap-2">
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
          <div className="flex justify-between items-center">
            <span className={`${SHIMMER_DARK} w-12 h-2`} />
            <span className={`${SHIMMER_DARK} w-10 h-2`} />
          </div>
        </div>
      </div>

      {/* ── Confidence ────────────────────────────────────────── */}
      <div className="px-5 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className={`${SHIMMER_DARK} w-10 h-2`} />
          <span className={`${SHIMMER_DARK} w-8 h-2`} />
        </div>
        <span className={`${SHIMMER_DARK} block w-full h-[3px]`} />
      </div>
    </div>
  );
}
