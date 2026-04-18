import { Skeleton } from '@/components/ui/Skeleton';

export default function StrategyLoading() {
  return (
    <div className="mx-auto max-w-5xl space-y-4 bg-shell-bg px-4 py-10">
      <Skeleton className="h-9 w-72 bg-neutral-200" />
      <Skeleton className="h-4 w-full max-w-xl bg-neutral-200" />
      <Skeleton className="h-24 w-full bg-neutral-200" />
    </div>
  );
}
