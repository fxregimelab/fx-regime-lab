import { mapEquityCurve, mapValidationRow } from '@/lib/supabase/map-row';
import { getAllValidationRows, getEquityCurve, getValidationStats } from '@/lib/supabase/queries';
import type { ValidationRow } from '@/lib/types';
import { EquityChart } from './EquityChart';
import { PerformanceFilters } from './PerformanceFilters';

export default async function PerformancePage() {
  const [statsRes, validationRes, equityRes] = await Promise.all([
    getValidationStats(),
    getAllValidationRows(),
    getEquityCurve(),
  ]);

  const stats = statsRes.data ?? {
    winRate: 0,
    callsMade: 0,
    medianReturn: 0,
    daysLive: 0,
  };

  const validationRows = validationRes.error
    ? []
    : (validationRes.data ?? []).map(mapValidationRow).filter((r): r is ValidationRow => r != null);

  type EquityDb = { date: string; pair: string; actual_return_1d: number | null };
  const equityRows = (equityRes.data ?? []) as EquityDb[];
  const equityData =
    equityRes.error || !equityRows.length
      ? { dates: [] as string[], series: {} as Record<string, number[]> }
      : mapEquityCurve(
          equityRows.map((r) => ({
            date: r.date,
            pair: r.pair,
            return_pct: r.actual_return_1d,
          }))
        );

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">PERFORMANCE</p>
      <h1 className="mt-2 font-sans text-[32px] font-extrabold tracking-tight text-[#0a0a0a]">
        Track Record
      </h1>

      <div className="mt-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          {
            label: 'WIN RATE',
            value: stats.callsMade > 0 ? `${Math.round(stats.winRate * 100)}%` : '—',
          },
          {
            label: 'CALLS MADE',
            value: stats.callsMade > 0 ? String(stats.callsMade) : '—',
          },
          {
            label: 'MEDIAN RETURN',
            value:
              stats.callsMade > 0
                ? `${stats.medianReturn >= 0 ? '+' : ''}${(stats.medianReturn * 100).toFixed(2)}%`
                : '—',
          },
          {
            label: 'DAYS LIVE',
            value: stats.daysLive > 0 ? String(stats.daysLive) : '—',
          },
        ].map((m) => (
          <div key={m.label} className="border border-[#e5e5e5] p-4">
            <p className="font-mono text-[9px] tracking-wide text-[#a0a0a0]">{m.label}</p>
            <p className="mt-2 font-mono text-[24px] font-bold text-[#0a0a0a]">{m.value}</p>
          </div>
        ))}
      </div>

      <section className="mt-14">
        <h2 className="font-sans text-[18px] font-semibold text-[#0a0a0a]">
          Cumulative P&amp;L (equal-weight)
        </h2>
        <div className="mt-6">
          <EquityChart dates={equityData.dates} series={equityData.series} />
        </div>
      </section>

      <section className="mt-14">
        <h2 className="mb-2 font-sans text-[16px] font-semibold text-[#0a0a0a]">Validation log</h2>
        <PerformanceFilters rows={validationRows} />
      </section>
    </div>
  );
}
