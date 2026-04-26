import { EmptyState } from '@/components/states';
import { ErrorBoundaryCard } from '@/components/states';
import { PAIRS } from '@/lib/mock/data';
import type { Database } from '@/lib/supabase/database.types';
import { mapSignalRow } from '@/lib/supabase/map-row';
import { getLatestSignals } from '@/lib/supabase/queries';
import { fmt2, fmtInt } from '@/lib/utils/format';

type SignalDb = Database['public']['Tables']['signals']['Row'];

export default async function SignalsPage() {
  const rows = await Promise.all(PAIRS.map((p) => getLatestSignals(p.label)));
  const errors = rows.map((r) => r.error).filter(Boolean);
  if (errors.length === rows.length && errors[0]) {
    return (
      <div className="mx-auto max-w-[1280px] px-6 py-10">
        <ErrorBoundaryCard message={errors[0].message} tone="shell" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">SIGNALS</p>
      <h1 className="mt-2 font-sans text-[32px] font-extrabold tracking-tight text-[#0a0a0a]">
        Latest signal rows
      </h1>
      <p className="mt-2 max-w-2xl font-sans text-[14px] leading-relaxed text-[#737373]">
        Last ten daily signal snapshots per pair (rate, positioning, volatility).
      </p>

      <div className="mt-10 grid gap-8 lg:grid-cols-3">
        {PAIRS.map((p, i) => {
          const res = rows[i];
          if (res.error) {
            return (
              <div key={p.label}>
                <p className="mb-2 font-mono text-[10px] text-[#D94030]">{p.label}</p>
                <ErrorBoundaryCard message={res.error.message} tone="shell" />
              </div>
            );
          }
          const data = (res.data ?? []) as SignalDb[];
          if (data.length === 0) {
            return (
              <div key={p.label}>
                <p className="mb-2 font-mono text-[11px] font-semibold text-[#0a0a0a]">{p.label}</p>
                <EmptyState
                  title="No signals"
                  subtitle={`No signal rows in Supabase for ${p.label} yet.`}
                />
              </div>
            );
          }
          const mapped = data.map(mapSignalRow);
          return (
            <div key={p.label} className="border border-[#e5e5e5]">
              <div className="border-b border-[#f0f0f0] bg-[#fafafa] px-4 py-3">
                <p className="font-mono text-[11px] font-semibold text-[#0a0a0a]">{p.display}</p>
              </div>
              <div className="grid grid-cols-[1fr_1fr_1fr_1fr] gap-2 border-b border-[#e5e5e5] bg-[#fafafa] px-3 py-2 font-mono text-[8px] tracking-wide text-[#a0a0a0]">
                <span>DATE</span>
                <span>SPOT</span>
                <span>2Y</span>
                <span>COT%</span>
              </div>
              <ul>
                {mapped.map((s) => (
                  <li
                    key={`${s.pair}-${s.date}`}
                    className="grid grid-cols-4 gap-2 border-b border-[#f5f5f5] px-3 py-2 font-mono text-[10px] text-[#0a0a0a] last:border-b-0"
                  >
                    <span>{s.date}</span>
                    <span>{fmt2(s.spot)}</span>
                    <span>{fmt2(s.rate_diff_2y)}</span>
                    <span>{fmtInt(s.cot_percentile)}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
