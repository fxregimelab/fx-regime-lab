import { RegimeTransitionMatrix } from '@/components/RegimeTransitionMatrix';
import { PerformanceRolling7d } from '@/components/performance/PerformanceRolling7d';
import { PerformanceSparkStrip } from '@/components/performance/PerformanceSparkStrip';
import { mapEquityCurve, mapValidationRow } from '@/lib/supabase/map-row';
import {
  getAllValidationRows,
  getEquityCurve,
  getRegimeCallsForTransitions,
  getShellPerformanceMetrics,
} from '@/lib/supabase/queries';
import type { ValidationRow } from '@/lib/types';
import { EquityChart } from './EquityChart';
import { PerformanceFilters } from './PerformanceFilters';

export default async function PerformancePage() {
  const [shellRes, validationRes, equityRes, transRes] = await Promise.all([
    getShellPerformanceMetrics(),
    getAllValidationRows(),
    getEquityCurve(),
    getRegimeCallsForTransitions(),
  ]);

  const shell = shellRes.data ?? {
    callsValidated: 0,
    correct: 0,
    rolling7dPct: null,
    rolling7dCorrect: 0,
    rolling7dTotal: 0,
    avgNextDayReturn: null,
    cumulativeAllLast: null,
    perPairRolling: {},
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

  const acc7 =
    shell.rolling7dPct != null
      ? `${shell.rolling7dPct >= 10 ? shell.rolling7dPct.toFixed(1) : shell.rolling7dPct.toFixed(2)}%`
      : '—';
  const avgRet =
    shell.avgNextDayReturn != null
      ? `${shell.avgNextDayReturn >= 0 ? '+' : ''}${(shell.avgNextDayReturn * 100).toFixed(2)}%`
      : '—';
  const cumRet =
    shell.cumulativeAllLast != null
      ? `${shell.cumulativeAllLast >= 0 ? '+' : ''}${(shell.cumulativeAllLast * 100).toFixed(2)}%`
      : '—';
  const callsV = shell.callsValidated > 0 ? String(shell.callsValidated) : '—';
  const sub7 =
    shell.rolling7dTotal > 0 ? `${shell.rolling7dCorrect}/${shell.rolling7dTotal} correct` : 'Last 7d window';

  const transRows = transRes.error ? [] : (transRes.data ?? []);

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <div className="mb-10 border-b border-[#e5e5e5] pb-8">
        <p className="mb-2 font-mono text-[10px] tracking-[0.12em] text-[#a0a0a0]">TRACK RECORD</p>
        <h1 className="font-sans text-[32px] font-extrabold tracking-tight text-[#0a0a0a]">Performance</h1>
        <p className="mt-2 max-w-xl font-sans text-[14px] text-[#737373]">
          Next-day directional validation. Updated daily after market close.
        </p>
      </div>

      <div className="mb-8 grid grid-cols-2 gap-px bg-[#e5e5e5] shadow-[0_0_0_1px_#e5e5e5] sm:grid-cols-4">
        {[
          {
            label: '7D ACCURACY',
            value: acc7,
            color: 'text-[#16a34a]',
            sub: sub7,
          },
          {
            label: 'AVG NEXT-DAY RET',
            value: avgRet,
            color: 'text-[#F5923A]',
            sub: 'Per call directional',
          },
          {
            label: 'CUMULATIVE RET',
            value: cumRet,
            color: 'text-[#4BA3E3]',
            sub: 'Equal-weight ALL',
          },
          {
            label: 'CALLS VALIDATED',
            value: callsV,
            color: 'text-[#0a0a0a]',
            sub: '3 pairs',
          },
        ].map((m) => (
          <div key={m.label} className="bg-white px-5 py-5">
            <p className="mb-2 font-mono text-[9px] tracking-[0.12em] text-[#999]">{m.label}</p>
            <p className={`font-mono text-[28px] font-bold leading-none tracking-[-0.03em] ${m.color}`}>
              {m.value}
            </p>
            <p className="mt-2 font-mono text-[10px] text-[#bbb]">{m.sub}</p>
          </div>
        ))}
      </div>

      <section className="mb-10 border border-[#e5e5e5]">
        <EquityChart
          dates={equityData.dates}
          series={equityData.series}
          cumulativeDecimal={shell.cumulativeAllLast}
        />
        <PerformanceSparkStrip series={equityData.series} />
      </section>

      <PerformanceRolling7d perPairRolling={shell.perPairRolling} />

      <RegimeTransitionMatrix rows={transRows} />

      <section className="mt-14">
        <h2 className="mb-2 font-sans text-[16px] font-semibold text-[#0a0a0a]">Validation log</h2>
        <PerformanceFilters rows={validationRows} />
      </section>

      <p className="mt-12 border-t border-[#f0f0f0] pt-8 font-mono text-[10px] leading-[1.8] tracking-[0.06em] text-[#c0c0c0]">
        NEXT-DAY DIRECTIONAL OUTCOME. RETURN % IS NEXT-DAY CLOSE-TO-CLOSE SPOT MOVE IN THE DIRECTION OF THE CALL.
        RESEARCH ONLY — NOT INVESTMENT ADVICE.
      </p>
    </div>
  );
}
