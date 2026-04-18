import { Skeleton } from '@/components/ui/Skeleton';

export default function TerminalLoading() {
  return (
    <div className="min-h-[40vh] bg-terminal-bg">
      <div className="mx-auto max-w-6xl space-y-5 px-4 py-10">
        <Skeleton className="h-5 w-48 bg-neutral-800" />
        <Skeleton className="h-8 w-56 bg-neutral-800" />
        <div className="min-h-[220px] w-full rounded-md border border-neutral-800 bg-neutral-900/40 p-4">
          <div className="space-y-3">
            <Skeleton className="h-10 w-4/5 max-w-lg bg-neutral-800" />
            <Skeleton className="h-14 w-32 bg-neutral-800" />
            <Skeleton className="h-px w-full bg-neutral-800" />
            <Skeleton className="h-24 w-full bg-neutral-800" />
          </div>
        </div>
      </div>
    </div>
  );
}
