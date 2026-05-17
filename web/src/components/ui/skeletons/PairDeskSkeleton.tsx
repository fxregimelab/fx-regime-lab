import { SHIMMER_DARK } from "./shimmer";

function TopTileSkeleton() {
  return (
    <div className="bg-[var(--color-elevated)] px-5 py-5">
      <span className={`${SHIMMER_DARK} mb-2 block w-16 h-2`} />
      <span className={`${SHIMMER_DARK} block w-20 h-8`} />
      <span className={`${SHIMMER_DARK} mt-2 block w-12 h-3`} />
    </div>
  );
}

function SidebarCardSkeleton() {
  return (
    <div className="bg-[var(--color-surface)] p-4">
      <span className={`${SHIMMER_DARK} mb-3 block w-24 h-2`} />
      <div className="space-y-2">
        <span className={`${SHIMMER_DARK} block w-full h-3`} />
        <span className={`${SHIMMER_DARK} block w-full h-3`} />
        <span className={`${SHIMMER_DARK} block w-full h-3`} />
      </div>
    </div>
  );
}

/** Structured skeleton matching Pair Desk page proportions.
 *  Dark-themed to match the terminal surface.
 */
export function PairDeskSkeleton() {
  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <div className="max-w-[1440px] mx-auto px-4 py-6">
        {/* ── Back nav ──────────────────────────────────────────── */}
        <span className={`${SHIMMER_DARK} mb-4 block w-24 h-3`} />

        {/* ── Top strip (4 tiles) ───────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px mb-px bg-[var(--color-border)]">
          <TopTileSkeleton />
          <TopTileSkeleton />
          <TopTileSkeleton />
          <TopTileSkeleton />
        </div>

        {/* ── Trader's TL;DR ────────────────────────────────────── */}
        <div className="bg-[var(--color-elevated)] border border-[var(--color-border)] px-5 py-3.5 mb-px flex flex-wrap gap-x-6 gap-y-2 items-center">
          <span className={`${SHIMMER_DARK} w-24 h-3`} />
          <span className={`${SHIMMER_DARK} w-32 h-3`} />
          <span className={`${SHIMMER_DARK} w-20 h-3`} />
          <span className={`${SHIMMER_DARK} ml-auto w-16 h-3`} />
        </div>

        {/* ── Spot Sparkline ────────────────────────────────────── */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] px-5 py-4 mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className={`${SHIMMER_DARK} w-32 h-2`} />
            <span className={`${SHIMMER_DARK} w-24 h-2`} />
          </div>
          <span className={`${SHIMMER_DARK} block w-full h-[60px]`} />
        </div>

        {/* ── Signal Decomposition ──────────────────────────────── */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] px-5 py-3 mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className={`${SHIMMER_DARK} w-32 h-2`} />
            <span className={`${SHIMMER_DARK} w-16 h-2`} />
          </div>
          <span className={`${SHIMMER_DARK} block w-full h-[6px]`} />
          <div className="flex justify-between mt-2">
            <span className={`${SHIMMER_DARK} w-16 h-2`} />
            <span className={`${SHIMMER_DARK} w-16 h-2`} />
            <span className={`${SHIMMER_DARK} w-16 h-2`} />
            <span className={`${SHIMMER_DARK} w-16 h-2`} />
          </div>
        </div>

        {/* ── Regime Factors chips ──────────────────────────────── */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] px-5 py-3 flex gap-2 items-center mb-4 flex-wrap">
          <span className={`${SHIMMER_DARK} w-20 h-5`} />
          <span className={`${SHIMMER_DARK} w-20 h-5`} />
          <span className={`${SHIMMER_DARK} w-20 h-5`} />
          <span className={`${SHIMMER_DARK} w-20 h-5`} />
          <span className={`${SHIMMER_DARK} w-20 h-5`} />
        </div>

        {/* ── Validation Stats ──────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-4">
          <div className="bg-[var(--color-surface)] p-4">
            <span className={`${SHIMMER_DARK} mb-1 block w-14 h-2`} />
            <span className={`${SHIMMER_DARK} block w-16 h-6`} />
          </div>
          <div className="bg-[var(--color-surface)] p-4">
            <span className={`${SHIMMER_DARK} mb-1 block w-14 h-2`} />
            <span className={`${SHIMMER_DARK} block w-16 h-6`} />
          </div>
          <div className="bg-[var(--color-surface)] p-4">
            <span className={`${SHIMMER_DARK} mb-1 block w-14 h-2`} />
            <span className={`${SHIMMER_DARK} block w-16 h-6`} />
          </div>
          <div className="bg-[var(--color-surface)] p-4">
            <span className={`${SHIMMER_DARK} mb-1 block w-14 h-2`} />
            <span className={`${SHIMMER_DARK} block w-16 h-6`} />
          </div>
          <div className="bg-[var(--color-surface)] p-4">
            <span className={`${SHIMMER_DARK} mb-1 block w-14 h-2`} />
            <span className={`${SHIMMER_DARK} block w-16 h-6`} />
          </div>
        </div>

        {/* ── Execution Panel ───────────────────────────────────── */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] px-5 py-3 mb-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <span className={`${SHIMMER_DARK} mb-1 block w-12 h-2`} />
              <span className={`${SHIMMER_DARK} block w-16 h-3`} />
            </div>
            <div>
              <span className={`${SHIMMER_DARK} mb-1 block w-12 h-2`} />
              <span className={`${SHIMMER_DARK} block w-16 h-3`} />
            </div>
            <div>
              <span className={`${SHIMMER_DARK} mb-1 block w-12 h-2`} />
              <span className={`${SHIMMER_DARK} block w-16 h-3`} />
            </div>
            <div>
              <span className={`${SHIMMER_DARK} mb-1 block w-12 h-2`} />
              <span className={`${SHIMMER_DARK} block w-16 h-3`} />
            </div>
          </div>
        </div>

        {/* ── Main grid: Signals Table + Sidebar ────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-px bg-[var(--color-border)]">
          {/* Left: Signals Table */}
          <div className="bg-[var(--color-surface)]">
            <div className="px-4 py-3 border-b border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
              <span className={`${SHIMMER_DARK} block w-32 h-2`} />
            </div>
            <div className="w-full">
              {/* Table header */}
              <div className="flex border-b border-[var(--color-border-subtle)] bg-[var(--color-void)]">
                <span className={`${SHIMMER_DARK} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_DARK} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_DARK} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_DARK} m-2 w-12 h-2 flex-1`} />
              </div>
              {/* Table rows */}
              <TableRowSkeleton />
              <TableRowSkeleton bg="void" />
              <TableRowSkeleton />
              <TableRowSkeleton bg="void" />
              <TableRowSkeleton />
              <TableRowSkeleton bg="void" />
              <TableRowSkeleton />
              <TableRowSkeleton bg="void" />
            </div>
            {/* Primary Driver footer */}
            <div className="px-4 py-3 border-t border-[var(--color-border)]">
              <span className={`${SHIMMER_DARK} block w-48 h-2`} />
            </div>
          </div>

          {/* Right: Sidebar */}
          <div className="bg-[var(--color-surface)]">
            <SidebarCardSkeleton />
            <SidebarCardSkeleton />
            <SidebarCardSkeleton />
          </div>
        </div>
      </div>
    </div>
  );
}

function TableRowSkeleton({ bg = "surface" }: { bg?: "surface" | "void" }) {
  const bgClass =
    bg === "void" ? "bg-[var(--color-void)]" : "bg-[var(--color-surface)]";
  return (
    <div
      className={`flex border-b border-[var(--color-border-subtle)] ${bgClass}`}
    >
      <span className={`${SHIMMER_DARK} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_DARK} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_DARK} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_DARK} m-2 w-10 h-2 flex-1`} />
    </div>
  );
}
