import { Skeleton } from "@/components/ui/skeleton";

export default function DeskLoading() {
  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      {/* Header skeleton */}
      <div className="border-b border-[var(--color-border)]">
        <div className="max-w-[1152px] mx-auto px-6 py-4 flex items-center justify-between">
          <Skeleton className="h-5 w-40" />
          <div className="flex gap-6">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-20" />
          </div>
        </div>
      </div>

      <div className="max-w-[1152px] mx-auto px-6 py-6 space-y-6">
        {/* Status bar skeleton */}
        <Skeleton className="h-12 w-full" />

        {/* Cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>

        {/* Matrix skeleton */}
        <Skeleton className="h-64 w-full" />

        {/* Bottom row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </div>
    </div>
  );
}
