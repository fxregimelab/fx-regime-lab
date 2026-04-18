import { Skeleton } from '@/components/ui/Skeleton';

export default function ShellLoading() {
  return (
    <div className="min-w-0">
      {/* Hero: two columns — left copy lines, right dark regime card */}
      <section className="mx-auto grid max-w-6xl gap-12 px-4 py-16 lg:grid-cols-2 lg:items-start lg:gap-16">
        <div className="space-y-4">
          <Skeleton className="h-3 w-56 bg-neutral-200" />
          <Skeleton className="h-14 w-full max-w-md bg-neutral-200" />
          <Skeleton className="h-24 w-full max-w-[480px] bg-neutral-200" />
        </div>
        <div className="min-h-[280px] rounded-xl bg-terminal-surface p-6 shadow-inner">
          <Skeleton className="h-4 w-24 bg-neutral-700" />
          <Skeleton className="mt-4 h-10 w-full max-w-xs bg-neutral-700" />
          <Skeleton className="mt-6 h-1.5 w-full bg-neutral-800" />
          <Skeleton className="mt-8 h-4 w-32 bg-neutral-700" />
        </div>
      </section>

      {/* Three pair cards */}
      <div className="pb-20">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 px-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="flex flex-col rounded-xl border border-neutral-200 bg-white p-6 shadow-sm"
            >
              <Skeleton className="h-5 w-24 bg-neutral-200" />
              <Skeleton className="mt-3 h-8 w-full max-w-[200px] bg-neutral-200" />
              <Skeleton className="mt-4 h-2 w-full bg-neutral-200" />
              <Skeleton className="mt-2 h-4 w-12 bg-neutral-200" />
              <div className="mt-4 space-y-2 border-t border-neutral-200 pt-4">
                <Skeleton className="h-3 w-full bg-neutral-200" />
                <Skeleton className="h-3 w-full bg-neutral-200" />
                <Skeleton className="h-3 w-full bg-neutral-200" />
              </div>
              <Skeleton className="mt-6 h-4 w-32 bg-neutral-200" />
            </div>
          ))}
        </div>
      </div>

      {/* Track record strip — full width dark band, four stat columns */}
      <section className="bg-terminal-surface py-12 text-white">
        <div className="mx-auto max-w-6xl px-4">
          <div className="grid grid-cols-2 gap-10 md:grid-cols-4 md:gap-6">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="flex flex-col items-center py-1">
                <Skeleton className="h-10 w-20 bg-neutral-700" />
                <Skeleton className="mt-3 h-3 w-28 bg-neutral-700" />
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
