import { SkeletonBlock } from './primitives';

export function CalendarPageSkeleton() {
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <div className="mb-10 flex justify-between border-b border-[#e5e5e5] pb-6">
        <div className="flex flex-col gap-2.5">
          <SkeletonBlock widthClass="w-[120px]" heightClass="h-2.5" />
          <SkeletonBlock widthClass="w-[240px]" heightClass="h-8" />
          <SkeletonBlock widthClass="w-[360px]" heightClass="h-3.5" />
        </div>
        <SkeletonBlock widthClass="w-[100px]" heightClass="h-10" />
      </div>
      <div className="mb-8 flex items-center justify-between border border-[#1a1a1a] bg-[#0a0a0a] px-5 py-4">
        <div className="flex items-center gap-3.5">
          <div className="h-10 w-1 bg-[#2a2a2a]" />
          <div className="flex flex-col gap-2">
            <SkeletonBlock widthClass="w-[120px]" heightClass="h-2" tone="terminal" />
            <SkeletonBlock widthClass="w-[200px]" heightClass="h-4" tone="terminal" />
          </div>
        </div>
        <SkeletonBlock widthClass="w-[60px]" heightClass="h-10" tone="terminal" />
      </div>
      <div className="mb-7 flex gap-2 border-b border-[#e5e5e5] pb-0.5">
        {[0, 1, 2, 3].map((i) => (
          <SkeletonBlock key={i} widthClass="w-[70px]" heightClass="h-9" />
        ))}
      </div>
      <div className="border border-[#e5e5e5]">
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="grid grid-cols-[100px_1fr] border-b border-[#e5e5e5] last:border-b-0"
          >
            <div className="flex flex-col gap-1.5 border-r border-[#f0f0f0] bg-[#fafafa] p-4">
              <SkeletonBlock widthClass="w-[30px]" heightClass="h-2" />
              <SkeletonBlock widthClass="w-[60px]" heightClass="h-3" />
              <SkeletonBlock widthClass="w-6" heightClass="h-2" />
            </div>
            <div className="flex items-center justify-between px-5 py-4">
              <div className="flex flex-1 flex-col gap-1.5">
                <SkeletonBlock widthClass="w-3/5" heightClass="h-3.5" />
                <SkeletonBlock widthClass="w-[30%]" heightClass="h-2" />
              </div>
              <SkeletonBlock widthClass="w-10" heightClass="h-2" />
            </div>
          </div>
        ))}
      </div>
      <div className="border border-t-0 border-[#e5e5e5] px-5 py-3">
        <SkeletonBlock widthClass="w-[300px]" heightClass="h-2.5" />
      </div>
    </div>
  );
}
