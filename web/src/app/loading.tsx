import { Skeleton } from "@/components/ui/skeleton";

export default function RootLoading() {
  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      {/* Nav skeleton */}
      <div className="border-b border-[var(--color-border)]" style={{ height: 64 }}>
        <div className="mx-auto flex h-full max-w-[1440px] items-center justify-between px-4">
          <Skeleton className="h-7 w-7" />
          <div className="hidden md:flex items-center gap-4">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
          </div>
        </div>
      </div>

      {/* Hero skeleton */}
      <div className="max-w-[1152px] mx-auto px-6 w-full pt-24 pb-16">
        <Skeleton className="h-3 w-24 mb-6" />
        <Skeleton className="h-14 w-full max-w-[720px] mb-12" />
        <Skeleton className="h-5 w-full max-w-[520px] mb-10" />
        <div className="flex gap-4 mb-12">
          <Skeleton className="h-12 w-40" />
          <Skeleton className="h-12 w-32" />
        </div>
        <div className="flex gap-6">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
    </div>
  );
}
