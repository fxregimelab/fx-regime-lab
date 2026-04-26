export function SkeletonBlock({
  widthClass = 'w-full',
  heightClass = 'h-4',
  tone = 'shell',
}: {
  widthClass?: string;
  heightClass?: string;
  tone?: 'shell' | 'terminal';
}) {
  const shimmer = tone === 'terminal' ? 'shimmer-terminal' : 'shimmer-shell';
  return <div className={`shrink-0 ${shimmer} ${widthClass} ${heightClass}`} />;
}

const colGrid: Record<number, string> = {
  3: 'grid-cols-3',
  4: 'grid-cols-4',
  5: 'grid-cols-5',
};

export function TableRowSkeleton({
  cols = 4,
  tone = 'shell',
}: { cols?: number; tone?: 'shell' | 'terminal' }) {
  const border = tone === 'terminal' ? 'border-[#111]' : 'border-[#f5f5f5]';
  const bg = tone === 'terminal' ? 'bg-[#0a0a0a]' : 'bg-white';
  const grid = colGrid[cols] ?? 'grid-cols-4';
  const widths = ['w-[60%]', 'w-[80%]', 'w-1/2', 'w-[40%]', 'w-[30%]'].slice(0, cols);
  return (
    <div className={`grid ${grid} gap-3 px-[18px] py-3 ${border} border-b ${bg}`}>
      {widths.map((w) => (
        <SkeletonBlock
          key={`${tone}-${cols}-${w}`}
          widthClass={w}
          heightClass="h-[11px]"
          tone={tone}
        />
      ))}
    </div>
  );
}
