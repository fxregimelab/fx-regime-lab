import type { SignalRow } from '@/lib/types';
import { fmt2 } from '@/lib/utils/format';

function toBars(signal: SignalRow) {
  const r = Math.abs(signal.rate_diff_2y) * 10;
  const c = signal.cot_percentile;
  const v20 = signal.realized_vol_20d * 5;
  const vI = (signal.implied_vol_30d ?? signal.realized_vol_20d) * 3;
  const total = r + c + v20 + vI || 1;
  return [
    { k: 'Rate Differential', pct: (r / total) * 100 },
    { k: 'COT Positioning', pct: (c / total) * 100 },
    { k: 'Realized Vol', pct: (v20 / total) * 100 },
    { k: 'Implied Vol', pct: (vI / total) * 100 },
  ];
}

export function AttributionTab({
  signal,
  pairColor,
  signalComposite,
}: {
  signal: SignalRow;
  pairColor: string;
  signalComposite: number;
}) {
  const rows = toBars(signal);

  return (
    <div className="space-y-4">
      {rows.map((row) => (
        <div key={row.k}>
          <p className="font-mono text-[9px] text-[#555]">{row.k}</p>
          <svg
            className="mt-1.5 block h-[3px] w-full"
            viewBox="0 0 100 1"
            preserveAspectRatio="none"
            role="img"
          >
            <title>{row.k}</title>
            <rect width="100" height="1" fill="#1e1e1e" />
            <rect width={row.pct} height="1" fill={pairColor} />
          </svg>
        </div>
      ))}
      <p className="pt-2 font-mono text-[20px] text-[#e8e8e8]">composite {fmt2(signalComposite)}</p>
    </div>
  );
}
