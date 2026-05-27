import { Skeleton } from "@/components/ui/skeleton";

export default function TrackRecordLoading() {
  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      {/* Header skeleton */}
      <div className="border-b border-[var(--color-border)]">
        <div className="max-w-[1152px] mx-auto px-6 py-6">
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-96" />
        </div>
      </div>

      <div className="max-w-[1152px] mx-auto px-6 py-8">
        {/* Tab bar skeleton */}
        <div className="flex gap-4 mb-8">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-24" />
        </div>

        {/* Stats cards skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>

        {/* Chart skeleton */}
        <Skeleton className="h-80 w-full mb-8" />

        {/* Table skeleton */}
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    </div>
  );
}
