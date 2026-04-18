import { Skeleton } from '@/components/ui/Skeleton';

export default function AboutLoading() {
  return (
    <div className="mx-auto max-w-3xl space-y-4 bg-shell-bg px-4 py-10">
      <Skeleton className="h-9 w-40 bg-neutral-200" />
      <Skeleton className="h-4 w-full bg-neutral-200" />
      <Skeleton className="h-4 w-full max-w-md bg-neutral-200" />
    </div>
  );
}
