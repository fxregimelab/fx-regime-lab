import { SkeletonBlock } from './primitives';
import { TableRowSkeleton } from './primitives';

export function SignalsPageSkeleton() {
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <div className="mb-8 border-b border-[#e5e5e5] pb-6">
        <SkeletonBlock widthClass="w-[140px]" heightClass="h-2.5" />
        <SkeletonBlock widthClass="mt-2 w-[280px]" heightClass="h-8" />
        <SkeletonBlock widthClass="mt-2 w-full max-w-xl" heightClass="h-3" />
      </div>
      <div className="grid gap-8 lg:grid-cols-3">
        {[0, 1, 2].map((col) => (
          <div key={col} className="border border-[#e5e5e5]">
            <div className="border-b border-[#f0f0f0] bg-[#fafafa] px-4 py-3">
              <SkeletonBlock widthClass="w-24" heightClass="h-3" />
            </div>
            <div className="border-b border-[#e5e5e5] bg-[#fafafa] px-3 py-2">
              <div className="grid grid-cols-4 gap-2">
                {['DATE', 'SPOT', '2Y', 'COT'].map((h) => (
                  <SkeletonBlock key={h} widthClass="w-12" heightClass="h-2" />
                ))}
              </div>
            </div>
            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((r) => (
              <TableRowSkeleton key={r} cols={4} tone="shell" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
