import { SkeletonBlock, TableRowSkeleton } from './primitives';

export function PairDetailSkeleton() {
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <div className="mb-10 grid grid-cols-1 gap-8 border-b border-[#e5e5e5] pb-6 md:grid-cols-[1fr_auto]">
        <div className="flex flex-col gap-2.5">
          <SkeletonBlock widthClass="w-[140px]" heightClass="h-2.5" />
          <SkeletonBlock widthClass="w-[220px]" heightClass="h-10" />
          <SkeletonBlock widthClass="w-40" heightClass="h-5" />
        </div>
        <SkeletonBlock widthClass="w-40" heightClass="h-10" />
      </div>
      <div className="mb-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        {[0, 1].map((i) => (
          <div key={i} className="border border-[#e5e5e5] border-t-[3px]">
            <div className="border-b border-[#f0f0f0] bg-[#fafafa] px-5 py-3.5">
              <SkeletonBlock widthClass="w-[120px]" heightClass="h-2.5" />
            </div>
            <div className="flex flex-col gap-2.5 p-5">
              <SkeletonBlock widthClass="w-4/5" heightClass="h-3.5" />
              <SkeletonBlock widthClass="w-full" heightClass="h-[3px]" />
              {[0, 1, 2].map((j) => (
                <div key={j} className="flex justify-between">
                  <SkeletonBlock widthClass="w-[100px]" heightClass="h-2.5" />
                  <SkeletonBlock widthClass="w-[50px]" heightClass="h-2.5" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="mb-6 border border-[#e5e5e5]">
        <div className="border-b border-[#f0f0f0] bg-[#fafafa] px-5 py-3.5">
          <SkeletonBlock widthClass="w-[200px]" heightClass="h-2.5" />
        </div>
        <div className="grid grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className={`flex flex-col gap-2 px-5 py-4 ${i < 2 ? 'border-r border-[#f0f0f0]' : ''}`}
            >
              <SkeletonBlock widthClass="w-20" heightClass="h-2" />
              <SkeletonBlock widthClass="w-[90%]" heightClass="h-3.5" />
              <SkeletonBlock widthClass="w-20" heightClass="h-2.5" />
            </div>
          ))}
        </div>
      </div>
      <div className="mb-6 border border-[#e5e5e5]">
        <div className="border-b border-[#f0f0f0] bg-[#fafafa] px-5 py-3.5">
          <SkeletonBlock widthClass="w-[180px]" heightClass="h-2.5" />
        </div>
        <div className="flex flex-wrap gap-1 p-4">
          {[
            'a1',
            'a2',
            'a3',
            'a4',
            'a5',
            'a6',
            'a7',
            'a8',
            'a9',
            'a10',
            'b1',
            'b2',
            'b3',
            'b4',
            'b5',
            'b6',
            'b7',
            'b8',
            'b9',
            'b10',
            'c1',
            'c2',
            'c3',
            'c4',
            'c5',
            'c6',
            'c7',
            'c8',
            'c9',
            'c10',
          ].map((id) => (
            <div key={id} className="h-5 w-5 bg-[#f0f0f0]" />
          ))}
        </div>
      </div>
      <div className="border border-[#e5e5e5]">
        {[0, 1, 2, 3].map((i) => (
          <TableRowSkeleton key={i} cols={5} tone="shell" />
        ))}
      </div>
    </div>
  );
}
