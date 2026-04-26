import { SkeletonBlock, TableRowSkeleton } from './primitives';

export function PerformancePageSkeleton() {
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <div className="mb-10 flex flex-col gap-2.5 border-b border-[#e5e5e5] pb-6">
        <SkeletonBlock widthClass="w-[100px]" heightClass="h-2.5" />
        <SkeletonBlock widthClass="w-[200px]" heightClass="h-8" />
      </div>
      <div className="mb-6 grid grid-cols-2 gap-px bg-[#e5e5e5] sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex flex-col gap-2.5 bg-white px-5 py-5">
            <SkeletonBlock widthClass="w-[100px]" heightClass="h-2" />
            <SkeletonBlock widthClass="w-20" heightClass="h-8" />
            <SkeletonBlock widthClass="w-[120px]" heightClass="h-2.5" />
          </div>
        ))}
      </div>
      <div className="mb-6 border border-[#e5e5e5]">
        <div className="flex justify-between border-b border-[#f0f0f0] px-5 py-4">
          <SkeletonBlock widthClass="w-[200px]" heightClass="h-2.5" />
          <SkeletonBlock widthClass="w-[60px]" heightClass="h-5" />
        </div>
        <div className="px-5 pb-2 pt-4">
          <SkeletonBlock widthClass="w-full" heightClass="h-[120px]" />
          <div className="flex justify-between pt-2">
            {[0, 1, 2, 3, 4].map((i) => (
              <SkeletonBlock key={i} widthClass="w-10" heightClass="h-2" />
            ))}
          </div>
        </div>
        <div className="grid grid-cols-3 border-t border-[#f0f0f0]">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className={`flex flex-col gap-2 px-[18px] py-3.5 ${i < 2 ? 'border-r border-[#f0f0f0]' : ''}`}
            >
              <SkeletonBlock widthClass="w-[60px]" heightClass="h-3" />
              <SkeletonBlock widthClass="w-full" heightClass="h-10" />
            </div>
          ))}
        </div>
      </div>
      <div className="border border-[#e5e5e5]">
        <div className="flex gap-2 border-b border-[#e5e5e5] bg-[#fafafa] px-[18px] py-2.5">
          {(['DATE', 'PAIR', 'CALL', 'OUTCOME', 'RET%'] as const).map((h) => (
            <SkeletonBlock key={h} widthClass="w-[60px]" heightClass="h-2.5" />
          ))}
        </div>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <TableRowSkeleton key={i} cols={5} tone="shell" />
        ))}
      </div>
    </div>
  );
}
