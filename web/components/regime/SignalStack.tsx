// Signal stack table
'use client';

import type { RegimeCall } from '@/lib/types/regime';

type Props = { call: RegimeCall | null };

export function SignalStack({ call }: Props) {
  if (!call) return null;
  const rows: [string, string | null | undefined][] = [
    ['Rate', call.rate_signal],
    ['COT', call.cot_signal],
    ['Vol', call.vol_signal],
    ['Risk reversal', call.rr_signal],
    ['OI', call.oi_signal],
  ];
  return (
    <table className="w-full border-collapse font-mono text-xs text-neutral-300">
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k} className="border-b border-neutral-800">
            <td className="py-1 text-neutral-500">{k}</td>
            <td className="py-1 text-right text-neutral-200">{v ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
