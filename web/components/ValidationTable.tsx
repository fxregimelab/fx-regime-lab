import type { ValidationRow } from '@/lib/types';

export function ValidationTable({ rows }: { rows: ValidationRow[] }) {
  return (
    <div className="overflow-x-auto border-b border-[#e5e5e5]">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-[#e5e5e5] bg-[#fafafa]">
            {(['DATE', 'PAIR', 'CALL', 'OUTCOME', 'RETURN'] as const).map((h) => (
              <th
                key={h}
                className="px-3 py-2 font-mono text-[9px] font-normal tracking-widest text-[#a0a0a0]"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={`${row.date}-${row.pair}-${row.call}-${i}`}
              className={i % 2 === 0 ? 'bg-white' : 'bg-[#fafafa]'}
            >
              <td className="px-3 py-2 font-mono text-[11px] text-[#0a0a0a]">{row.date}</td>
              <td className="px-3 py-2 font-mono text-[11px] text-[#0a0a0a]">{row.pair}</td>
              <td className="px-3 py-2 font-mono text-[11px] text-[#0a0a0a]">{row.call}</td>
              <td
                className={`px-3 py-2 font-mono text-[11px] ${
                  row.outcome === 'correct' ? 'text-[#16a34a]' : 'text-[#dc2626]'
                }`}
              >
                {row.outcome === 'correct' ? '✓ CORRECT' : '✗ INCORRECT'}
              </td>
              <td
                className={`px-3 py-2 font-mono text-[11px] ${
                  row.return_pct >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]'
                }`}
              >
                {row.return_pct >= 0 ? '+' : ''}
                {(row.return_pct * 100).toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
