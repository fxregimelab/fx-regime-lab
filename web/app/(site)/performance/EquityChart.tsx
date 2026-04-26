const W = 500;
const H = 160;
const PAD = 8;

interface EquityChartProps {
  dates: string[];
  series: Record<string, number[]>;
}

export function EquityChart({ dates, series }: EquityChartProps) {
  const EURUSD = series.EURUSD ?? [];
  const USDJPY = series.USDJPY ?? [];
  const USDINR = series.USDINR ?? [];
  const ALL = series.ALL ?? [];

  if (ALL.length === 0) {
    return (
      <p className="py-10 text-center font-mono text-[11px] text-[#a0a0a0]">
        Equity curve available after first pipeline validation run.
      </p>
    );
  }

  const allVals = [...EURUSD, ...USDJPY, ...USDINR, ...ALL];
  const mn = Math.min(...allVals);
  const mx = Math.max(...allVals);
  const range = mx - mn || 0.01;

  const toPath = (arr: number[], color: string, dashed?: boolean) => {
    const n = arr.length;
    const pts = arr.map((v, i) => {
      const x = PAD + (i / (n - 1)) * (W - 2 * PAD);
      const y = PAD + (1 - (v - mn) / range) * (H - 2 * PAD);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ');
    return (
      <path
        key={color + (dashed ? '-d' : '')}
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeDasharray={dashed ? '6 4' : undefined}
        vectorEffect="non-scaling-stroke"
      />
    );
  };

  return (
    <div>
      <svg
        className="mx-auto block max-w-full"
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Cumulative P and L equity curve"
      >
        <title>Cumulative P and L equity curve</title>
        {toPath(EURUSD, '#4BA3E3')}
        {toPath(USDJPY, '#F5923A')}
        {toPath(USDINR, '#D94030')}
        {toPath(ALL, '#0a0a0a', true)}
      </svg>
      <div className="mx-auto mt-4 flex max-w-[500px] flex-wrap justify-center gap-4 font-mono text-[9px] text-[#737373]">
        <span className="flex items-center gap-1.5">
          <span className="h-px w-4 bg-[#4BA3E3]" /> EURUSD
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-px w-4 bg-[#F5923A]" /> USDJPY
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-px w-4 bg-[#D94030]" /> USDINR
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-px w-4 border-t border-dashed border-[#0a0a0a]" /> ALL
        </span>
      </div>
      <p className="mt-2 text-center font-mono text-[9px] text-[#bbb]">
        {dates.length === 0
          ? ''
          : dates.length === 1
            ? dates[0]
            : `${dates[0]} → ${dates[dates.length - 1]}`}
      </p>
    </div>
  );
}
