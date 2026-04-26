import { SkeletonBlock } from './primitives';

export function HomePageSkeleton() {
  return (
    <div className="bg-white">
      <section className="mx-auto grid max-w-[1280px] gap-10 px-6 py-12 md:grid-cols-2 md:items-start md:gap-16 md:py-16">
        <div className="flex flex-col gap-4">
          <SkeletonBlock widthClass="w-[120px]" heightClass="h-2.5" />
          <SkeletonBlock widthClass="w-[90%]" heightClass="h-[52px]" />
          <SkeletonBlock widthClass="w-3/4" heightClass="h-[52px]" />
          <SkeletonBlock widthClass="w-[60%]" heightClass="h-[52px]" />
          <div className="mt-2 flex flex-col gap-2">
            <SkeletonBlock heightClass="h-3.5" />
            <SkeletonBlock heightClass="h-3.5" />
            <SkeletonBlock widthClass="w-[70%]" heightClass="h-3.5" />
          </div>
          <div className="mt-2 flex gap-3">
            <SkeletonBlock widthClass="w-[140px]" heightClass="h-10" />
            <SkeletonBlock widthClass="w-[120px]" heightClass="h-10" />
          </div>
        </div>
        <div className="border border-[#1e1e1e] bg-[#0a0a0a] p-5">
          <div className="mb-5 flex justify-between">
            <SkeletonBlock widthClass="w-20" heightClass="h-3" tone="terminal" />
            <SkeletonBlock widthClass="w-10" heightClass="h-3" tone="terminal" />
          </div>
          <SkeletonBlock widthClass="w-[140px]" heightClass="h-9" tone="terminal" />
          <SkeletonBlock widthClass="w-full" heightClass="h-3" tone="terminal" />
          <SkeletonBlock widthClass="w-4/5" heightClass="h-3" tone="terminal" />
          <SkeletonBlock widthClass="w-full" heightClass="h-[3px]" tone="terminal" />
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="flex justify-between border-b border-[#111] py-2">
              <SkeletonBlock widthClass="w-[120px]" heightClass="h-2.5" tone="terminal" />
              <SkeletonBlock widthClass="w-10" heightClass="h-2.5" tone="terminal" />
            </div>
          ))}
        </div>
      </section>
      <div className="border-y border-[#e5e5e5]">
        <div className="mx-auto grid max-w-[1280px] grid-cols-2 gap-6 px-6 sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className={`flex flex-col gap-2 py-5 sm:border-r sm:border-[#e5e5e5] ${i === 3 ? 'sm:border-r-0' : ''}`}
            >
              <SkeletonBlock widthClass="w-[60px]" heightClass="h-7" />
              <SkeletonBlock widthClass="w-[100px]" heightClass="h-2.5" />
            </div>
          ))}
        </div>
      </div>
      <section className="mx-auto max-w-[1280px] px-6 py-12">
        <div className="mb-6 flex justify-between">
          <SkeletonBlock widthClass="w-[200px]" heightClass="h-[22px]" />
          <SkeletonBlock widthClass="w-[100px]" heightClass="h-8" />
        </div>
        <div className="grid grid-cols-1 gap-px bg-[#e5e5e5] sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex flex-col gap-3 bg-white p-5">
              <div className="flex justify-between">
                <SkeletonBlock widthClass="w-20" heightClass="h-3.5" />
                <SkeletonBlock widthClass="w-[50px]" heightClass="h-5" />
              </div>
              <SkeletonBlock widthClass="w-[120px]" heightClass="h-5" />
              <SkeletonBlock widthClass="w-4/5" heightClass="h-3" />
              <SkeletonBlock widthClass="w-full" heightClass="h-[3px]" />
              <div className="flex flex-col gap-2 border-t border-[#f0f0f0] pt-3">
                {[0, 1, 2].map((j) => (
                  <div key={j} className="flex justify-between">
                    <SkeletonBlock widthClass="w-20" heightClass="h-2.5" />
                    <SkeletonBlock widthClass="w-10" heightClass="h-2.5" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
