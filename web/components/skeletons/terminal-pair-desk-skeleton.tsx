import { SkeletonBlock, TableRowSkeleton } from './primitives';

export function TerminalPairDeskSkeleton() {
  return (
    <div className="min-h-screen bg-[#080808] text-[#e8e8e8]">
      <div className="h-[76px] border-b border-[#1e1e1e] bg-[#080808]">
        <div className="mx-auto flex h-full max-w-[1200px] items-center justify-between px-6">
          <SkeletonBlock widthClass="w-[140px]" heightClass="h-3" tone="terminal" />
          <div className="flex gap-2">
            {[0, 1, 2].map((i) => (
              <SkeletonBlock key={i} widthClass="w-20" heightClass="h-7" tone="terminal" />
            ))}
          </div>
        </div>
      </div>
      <div className="mx-auto max-w-[1200px] px-6 py-6">
        <div className="mb-0.5 grid grid-cols-2 gap-0.5 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex flex-col gap-3 border border-[#1e1e1e] bg-[#0d0d0d] px-5 py-4"
            >
              <SkeletonBlock widthClass="w-20" heightClass="h-2" tone="terminal" />
              <SkeletonBlock widthClass="w-[120px]" heightClass="h-8" tone="terminal" />
              <SkeletonBlock widthClass="w-full" heightClass="h-[3px]" tone="terminal" />
            </div>
          ))}
        </div>
        <div className="mb-4 flex gap-2 border border-t-0 border-[#1a1a1a] bg-[#0c0c0c] px-5 py-2.5">
          {[0, 1, 2, 3].map((i) => (
            <SkeletonBlock key={i} widthClass="w-[100px]" heightClass="h-[26px]" tone="terminal" />
          ))}
        </div>
        <div className="grid gap-0.5 lg:grid-cols-[1fr_300px]">
          <div>
            <div className="flex flex-wrap border-b border-[#1a1a1a] bg-[#0a0a0a]">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <SkeletonBlock key={i} widthClass="w-20" heightClass="h-9" tone="terminal" />
              ))}
            </div>
            <div className="border border-t-0 border-[#1a1a1a]">
              {['r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6'].map((id) => (
                <TableRowSkeleton key={id} cols={4} tone="terminal" />
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-0.5">
            {[
              { id: 'ctx-a', h: 100 },
              { id: 'ctx-b', h: 160 },
              { id: 'ctx-c', h: 80 },
            ].map(({ id, h }) => (
              <div
                key={id}
                className="flex flex-col gap-2 border border-[#1a1a1a] bg-[#0c0c0c] p-3"
              >
                <SkeletonBlock widthClass="w-20" heightClass="h-2" tone="terminal" />
                <SkeletonBlock
                  widthClass="w-full"
                  heightClass={h === 100 ? 'h-[100px]' : h === 160 ? 'h-40' : 'h-20'}
                  tone="terminal"
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
