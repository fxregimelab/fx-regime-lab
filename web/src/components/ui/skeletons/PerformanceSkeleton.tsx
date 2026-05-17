import { SHIMMER_LIGHT } from "./shimmer";

function StatsCardSkeleton() {
  return (
    <div className="bg-[var(--shell-bg-elevated)] p-5 md:p-6">
      <span className={`${SHIMMER_LIGHT} mb-2.5 block w-16 h-2`} />
      <span className={`${SHIMMER_LIGHT} block w-20 h-8`} />
      <span className={`${SHIMMER_LIGHT} mt-1.5 block w-14 h-2`} />
    </div>
  );
}

/** Structured skeleton matching Performance page proportions.
 *  Light-themed to match the shell page.
 */
export function PerformanceSkeleton() {
  return (
    <div className="min-h-screen bg-[var(--shell-bg)]">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full">
        <div className="mb-10 pb-6 border-b border-[var(--shell-border)]">
          <span className={`${SHIMMER_LIGHT} mb-2.5 block w-24 h-2`} />
          <span className={`${SHIMMER_LIGHT} mb-2 block w-48 h-10`} />
          <span className={`${SHIMMER_LIGHT} block w-96 h-4`} />
        </div>

        {/* ── Stats Grid ────────────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--shell-border)] border border-[var(--shell-border)] mb-10">
          <StatsCardSkeleton />
          <StatsCardSkeleton />
          <StatsCardSkeleton />
          <StatsCardSkeleton />
          <StatsCardSkeleton />
        </div>

        {/* ── Accuracy Milestone Tracker ────────────────────────── */}
        <div className="border border-[var(--shell-border)] bg-[var(--shell-bg-elevated)] p-6 md:p-8 mb-10">
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <span className={`${SHIMMER_LIGHT} mb-2 block w-32 h-2`} />
              <span className={`${SHIMMER_LIGHT} block w-24 h-10`} />
            </div>
            <span className={`${SHIMMER_LIGHT} block w-16 h-6`} />
          </div>
          <span className={`${SHIMMER_LIGHT} mb-6 block w-full h-3`} />
          <div className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_200px]">
            <span className={`${SHIMMER_LIGHT} block w-full h-16`} />
            <div className="grid grid-cols-2 gap-px bg-[var(--shell-border)] md:grid-cols-1">
              <div className="bg-[var(--shell-bg-elevated)] p-3">
                <span className={`${SHIMMER_LIGHT} mb-1 block w-20 h-2`} />
                <span className={`${SHIMMER_LIGHT} block w-12 h-5`} />
              </div>
              <div className="bg-[var(--shell-bg-elevated)] p-3">
                <span className={`${SHIMMER_LIGHT} mb-1 block w-20 h-2`} />
                <span className={`${SHIMMER_LIGHT} block w-12 h-5`} />
              </div>
              <div className="bg-[var(--shell-bg-elevated)] p-3">
                <span className={`${SHIMMER_LIGHT} mb-1 block w-20 h-2`} />
                <span className={`${SHIMMER_LIGHT} block w-12 h-5`} />
              </div>
              <div className="bg-[var(--shell-bg-elevated)] p-3">
                <span className={`${SHIMMER_LIGHT} mb-1 block w-20 h-2`} />
                <span className={`${SHIMMER_LIGHT} block w-12 h-5`} />
              </div>
            </div>
          </div>
        </div>

        {/* ── Equity Curve ──────────────────────────────────────── */}
        <div className="border border-[var(--shell-border)] bg-[var(--shell-bg-elevated)] mb-10">
          <div className="px-5 py-3 border-b border-[var(--shell-border)] flex items-center justify-between">
            <span className={`${SHIMMER_LIGHT} block w-64 h-2`} />
            <span className={`${SHIMMER_LIGHT} block w-24 h-2`} />
          </div>
          <span
            className={`${SHIMMER_LIGHT} block w-full h-[240px] md:h-[320px] lg:h-[400px]`}
          />
        </div>

        {/* ── Brier Chart ───────────────────────────────────────── */}
        <div className="border border-[var(--shell-border)] bg-[var(--shell-bg-elevated)] mb-10">
          <div className="px-5 py-3 border-b border-[var(--shell-border)]">
            <span className={`${SHIMMER_LIGHT} block w-48 h-2`} />
          </div>
          <span
            className={`${SHIMMER_LIGHT} block w-full h-[180px] md:h-[220px]`}
          />
        </div>

        {/* ── Pair Breakdown Table ──────────────────────────────── */}
        <div className="border border-[var(--shell-border)] bg-[var(--shell-bg-elevated)] overflow-hidden mb-10">
          <div className="px-5 py-3 border-b border-[var(--shell-border)]">
            <span className={`${SHIMMER_LIGHT} block w-32 h-2`} />
          </div>
          <div className="overflow-x-auto">
            <div className="w-full">
              {/* Header row */}
              <div className="flex border-b border-[var(--shell-border)] bg-[var(--shell-bg-sunken)]">
                <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
                <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
              </div>
              {/* Body rows */}
              <BreakdownRow even />
              <BreakdownRow />
              <BreakdownRow even />
              <BreakdownRow />
            </div>
          </div>
        </div>

        {/* ── Validation History ────────────────────────────────── */}
        <div className="mb-10">
          <span className={`${SHIMMER_LIGHT} mb-4 block w-48 h-2`} />
          <div className="border border-[var(--shell-border)] bg-[var(--shell-bg-elevated)] overflow-hidden">
            {/* Header row */}
            <div className="flex border-b border-[var(--shell-border)] bg-[var(--shell-bg-sunken)]">
              <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
              <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
              <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
              <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
              <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
              <span className={`${SHIMMER_LIGHT} m-2 w-12 h-2 flex-1`} />
            </div>
            {/* Body rows */}
            <HistoryRow even />
            <HistoryRow />
            <HistoryRow even />
            <HistoryRow />
            <HistoryRow even />
            <HistoryRow />
          </div>
        </div>
      </div>
    </div>
  );
}

function BreakdownRow({ even = false }: { even?: boolean }) {
  const bg = even
    ? "bg-[var(--shell-bg-sunken)]"
    : "bg-[var(--shell-bg-elevated)]";
  return (
    <div className={`flex border-b border-[var(--shell-border-subtle)] ${bg}`}>
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
    </div>
  );
}

function HistoryRow({ even = false }: { even?: boolean }) {
  const bg = even
    ? "bg-[var(--shell-bg-sunken)]"
    : "bg-[var(--shell-bg-elevated)]";
  return (
    <div className={`flex border-b border-[var(--shell-border-subtle)] ${bg}`}>
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
      <span className={`${SHIMMER_LIGHT} m-2 w-10 h-2 flex-1`} />
    </div>
  );
}
