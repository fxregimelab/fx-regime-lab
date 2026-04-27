import { PAIRS } from '@/lib/mock/data';
import type { ValidationRow } from '@/lib/types';

function pairDisplay(label: string): string {
  return PAIRS.find((p) => p.label === label)?.display ?? label;
}

export function ValidationTable({
  rows,
  variant = 'light',
}: {
  rows: ValidationRow[];
  variant?: 'light' | 'dark';
}) {
  const isDark = variant === 'dark';
  const headBg = isDark ? 'bg-[#111]' : 'bg-[#fafafa]';
  const headText = isDark ? 'text-[#888]' : 'text-[#a0a0a0]';
  const border = isDark ? 'border-[#1a1a1a]' : 'border-[#e5e5e5]';
  const rowEven = isDark ? 'bg-[#0a0a0a]' : 'bg-white';
  const rowOdd = isDark ? 'bg-[#0c0c0c]' : 'bg-[#fafafa]';
  const cellText = isDark ? 'text-[#e8e8e8]' : 'text-[#0a0a0a]';

  return (
    <div className={`overflow-x-auto border-b ${border}`}>
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className={`border-b ${border} ${headBg}`}>
            {(['DATE', 'PAIR', 'CALL', 'OUTCOME', 'RETURN'] as const).map((h) => (
              <th
                key={h}
                className={`px-3 py-2 font-mono text-[9px] font-normal tracking-widest ${headText}`}
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
              className={`border-b ${border} ${i % 2 === 0 ? rowEven : rowOdd}`}
            >
              <td className={`px-3 py-2 font-mono text-[11px] ${cellText}`}>{row.date}</td>
              <td className={`px-3 py-2 font-mono text-[11px] ${cellText}`}>
                {pairDisplay(row.pair)}
              </td>
              <td className={`px-3 py-2 font-mono text-[11px] ${cellText}`}>{row.call}</td>
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
