import { Skeleton } from '@/components/ui/Skeleton';

export default function TerminalPairLoading() {
  return (
    <div className="mx-auto max-w-6xl space-y-6 bg-terminal-bg px-4 py-8">
      <Skeleton className="h-5 w-64 bg-neutral-800" />
      <Skeleton className="h-32 w-full bg-neutral-800" />
      <Skeleton className="h-48 w-full bg-neutral-800" />
    </div>
  );
}
