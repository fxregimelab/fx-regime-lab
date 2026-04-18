import { Skeleton } from '@/components/ui/Skeleton';

export default function StrategyPerformanceLoading() {
  return (
    <div className="mx-auto max-w-5xl space-y-4 bg-shell-bg px-4 py-10">
      <Skeleton className="h-9 w-80 bg-neutral-200" />
      <Skeleton className="h-4 w-full max-w-xl bg-neutral-200" />
      <Skeleton className="h-40 w-full bg-neutral-200" />
    </div>
  );
}
