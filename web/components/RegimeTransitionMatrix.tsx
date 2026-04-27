import {
  TRANSITION_BUCKET_LABELS,
  TRANSITION_COL_SHORT,
  buildRegimeTransitionMatrix,
} from '@/lib/regime-transition-matrix';

type Row = { date: string; pair: string; regime: string };

export function RegimeTransitionMatrix({ rows }: { rows: Row[] }) {
  const matrix = buildRegimeTransitionMatrix(rows);

  return (
    <div className="mb-6 border border-[#e5e5e5]">
      <div className="border-b border-[#f0f0f0] px-5 py-4">
        <p className="mb-1 font-mono text-[10px] tracking-[0.1em] text-[#888]">REGIME TRANSITION MATRIX</p>
        <p className="font-sans text-[13px] text-[#aaa]">
          How often each regime transitions to another (based on available history)
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[10px]">
          <thead>
            <tr className="border-b border-[#f0f0f0]">
              <th className="min-w-[180px] px-3 py-2.5 text-left font-medium text-[#aaa]">FROM \ TO</th>
              {TRANSITION_COL_SHORT.map((h) => (
                <th key={h} className="min-w-[80px] px-2 py-2.5 text-center font-medium text-[#aaa]">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TRANSITION_BUCKET_LABELS.map((regime, ri) => (
              <tr key={regime} className="border-b border-[#f8f8f8]">
                <td className="px-3 py-2.5 text-[#555]">{regime}</td>
                {matrix[ri]?.map((cell, ci) => {
                  const n = cell != null && cell !== '—' ? parseInt(cell, 10) : NaN;
                  const bgClass =
                    cell == null
                      ? 'bg-[#f8f8f8] text-[#f0f0f0]'
                      : Number.isFinite(n) && n > 50
                        ? 'bg-[#dbeafe] font-bold text-[#0a0a0a]'
                        : Number.isFinite(n) && n > 25
                          ? 'bg-[#eff6ff] text-[#444]'
                          : 'bg-white text-[#888]';
                  return (
                    <td key={ci} className={`px-2 py-2.5 text-center ${bgClass}`}>
                      {cell ?? '—'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
