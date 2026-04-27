const W = 800;
const H = 120;
const PAD = 8;

interface EquityChartProps {
  dates: string[];
  series: Record<string, number[]>;
  /** Cumulative ALL (decimal); shown in header when provided */
  cumulativeDecimal?: number | null;
}

export function EquityChart({ dates, series, cumulativeDecimal }: EquityChartProps) {
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

  const allVals = [...ALL, ...EURUSD, ...USDJPY, ...USDINR];
  const mn = Math.min(...allVals);
  const mx = Math.max(...allVals);
  const range = mx - mn || 0.01;

  const toPoints = (arr: number[]) =>
    arr.map((v, i) => {
      const n = arr.length;
      const x = PAD + (i / (n - 1)) * (W - 2 * PAD);
      const y = PAD + (1 - (v - mn) / range) * (H - 2 * PAD);
      return { x, y };
    });

  const allPts = toPoints(ALL);
  const lineD = allPts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const areaD = `${lineD} L${W - PAD},${H - PAD} L${PAD},${H - PAD} Z`;
  const dotStep = Math.max(1, Math.floor(allPts.length / 28));
  const dotPts = allPts.filter((_, i) => i % dotStep === 0 || i === allPts.length - 1);

  const thinPath = (arr: number[], color: string) => {
    if (arr.length < 2) return null;
    const pts = toPoints(arr);
    const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    return (
      <path
        key={color}
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={1}
        strokeOpacity={0.35}
        vectorEffect="non-scaling-stroke"
      />
    );
  };

  const cumPct =
    cumulativeDecimal != null ? `${cumulativeDecimal >= 0 ? '+' : ''}${(cumulativeDecimal * 100).toFixed(2)}%` : null;

  const tickDates = dates.filter((_, i) => i % 3 === 0 || i === dates.length - 1);

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#f0f0f0] px-5 py-4">
        <div>
          <p className="mb-1 font-mono text-[10px] tracking-[0.1em] text-[#888]">CUMULATIVE RETURN — ALL PAIRS</p>
          <p className="font-mono text-[11px] text-[#aaa]">
            {dates.length === 0
              ? '—'
              : dates.length === 1
                ? dates[0]
                : `${dates[0]} → ${dates[dates.length - 1]} · Next-day spot in call direction`}
          </p>
        </div>
        {cumPct ? (
          <p className="font-mono text-[22px] font-bold leading-none tracking-[-0.03em] text-[#16a34a]">{cumPct}</p>
        ) : null}
      </div>
      <div className="px-5 pb-2 pt-4">
        <svg
          className="mx-auto block h-auto w-full max-w-[920px]"
          width={W}
          height={H}
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label="Cumulative return equity curve"
        >
          <title>Cumulative return equity curve</title>
          <defs>
            <linearGradient id="equityGradShell" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#16a34a" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#16a34a" stopOpacity="0" />
            </linearGradient>
          </defs>
          {thinPath(EURUSD, '#4BA3E3')}
          {thinPath(USDJPY, '#F5923A')}
          {thinPath(USDINR, '#D94030')}
          <path d={areaD} fill="url(#equityGradShell)" />
          <path d={lineD} fill="none" stroke="#16a34a" strokeWidth={2} vectorEffect="non-scaling-stroke" />
          {dotPts.map((p, i) => (
            <circle key={`dot-${i}`} cx={p.x} cy={p.y} r={3} fill="#16a34a" stroke="#fff" strokeWidth={1.5} />
          ))}
        </svg>
        <div className="mx-auto flex max-w-[920px] flex-wrap justify-between gap-2 px-1 pt-2">
          {tickDates.map((d) => (
            <span key={d} className="font-mono text-[9px] text-[#bbb]">
              {d}
            </span>
          ))}
        </div>
      </div>
      <div className="mx-auto mt-2 flex max-w-[920px] flex-wrap justify-center gap-4 border-t border-[#f0f0f0] px-5 pb-4 pt-4 font-mono text-[9px] text-[#737373]">
        <span className="flex items-center gap-1.5">
          <span className="h-px w-4 bg-[#16a34a]" /> ALL (equal-weight)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-px w-4 bg-[#4BA3E3]" /> EUR/USD
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-px w-4 bg-[#F5923A]" /> USD/JPY
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-px w-4 bg-[#D94030]" /> USD/INR
        </span>
      </div>
    </div>
  );
}
