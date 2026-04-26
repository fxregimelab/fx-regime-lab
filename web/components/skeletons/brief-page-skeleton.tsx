import { SkeletonBlock } from './primitives';

export function BriefPageSkeleton() {
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <div className="mb-10 flex justify-between border-b border-[#e5e5e5] pb-6">
        <div className="flex flex-col gap-2.5">
          <SkeletonBlock widthClass="w-[120px]" heightClass="h-2.5" />
          <SkeletonBlock widthClass="w-[280px]" heightClass="h-8" />
        </div>
        <SkeletonBlock widthClass="w-[120px]" heightClass="h-9" />
      </div>
      <div className="mb-10 flex flex-col gap-2 border border-[#e5e5e5] border-l-[3px] bg-[#fafafa] p-4 pl-5">
        <SkeletonBlock widthClass="w-[120px]" heightClass="h-2.5" />
        <SkeletonBlock heightClass="h-3.5" />
        <SkeletonBlock widthClass="w-4/5" heightClass="h-3.5" />
      </div>
      <div className="mb-8 flex gap-2 border-b border-[#e5e5e5] pb-0.5">
        {[0, 1, 2, 3].map((i) => (
          <SkeletonBlock key={i} widthClass="w-20" heightClass="h-9" />
        ))}
      </div>
      {[0, 1, 2].map((i) => (
        <div key={i} className="mb-4 border border-[#e5e5e5] border-t-[3px]">
          <div className="flex justify-between border-b border-[#f0f0f0] bg-[#fafafa] px-6 py-5">
            <div className="flex flex-col gap-2">
              <SkeletonBlock widthClass="w-20" heightClass="h-3.5" />
              <SkeletonBlock widthClass="w-[200px]" heightClass="h-3" />
            </div>
            <SkeletonBlock widthClass="w-[60px]" heightClass="h-7" />
          </div>
          <div className="grid grid-cols-5 border-b border-[#f0f0f0]">
            {[0, 1, 2, 3, 4].map((j) => (
              <div
                key={j}
                className={`flex flex-col gap-2 px-[18px] py-3.5 ${j < 4 ? 'border-r border-[#f0f0f0]' : ''}`}
              >
                <SkeletonBlock widthClass="w-[60px]" heightClass="h-2" />
                <SkeletonBlock widthClass="w-[50px]" heightClass="h-3.5" />
              </div>
            ))}
          </div>
          <div className="flex flex-col gap-2 px-6 py-5">
            <SkeletonBlock heightClass="h-3.5" />
            <SkeletonBlock heightClass="h-3.5" />
            <SkeletonBlock widthClass="w-[70%]" heightClass="h-3.5" />
          </div>
        </div>
      ))}
    </div>
  );
}
