import { Skeleton } from '@/components/ui/Skeleton';

export default function TerminalStrategyLoading() {
  return (
    <div className="mx-auto max-w-5xl space-y-4 bg-terminal-bg px-4 py-8">
      <Skeleton className="h-5 w-48 bg-neutral-800" />
      <Skeleton className="h-4 w-56 bg-neutral-800" />
      <div className="grid gap-2 sm:grid-cols-3">
        <Skeleton className="h-12 bg-neutral-800" />
        <Skeleton className="h-12 bg-neutral-800" />
        <Skeleton className="h-12 bg-neutral-800" />
      </div>
    </div>
  );
}
