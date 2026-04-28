'use client';

import React, { useMemo } from 'react';
import { Nav } from '@/components/layout/nav';
import { Footer } from '@/components/layout/footer';
import { MacroPulseBar, PULSE_BAR_H } from '@/components/ui/macro-pulse-bar';
import { ValidationTable } from '@/components/ui/validation-table';
import { PAIRS, BRAND } from '@/lib/mockData';
import { useValidationLog, useEquityCurve, useLastPipelineRun } from '@/lib/queries';
import { mapValidationLogToTableRows, rolling7dAccuracyPct, buildEquitySeries } from '@/lib/validation-format';

const SHELL_NAV_H = 54;
const SHELL_TOP_OFFSET = PULSE_BAR_H + SHELL_NAV_H;

export default function PerformancePage() {
  const [filterPair, setFilterPair] = React.useState<string>('ALL');
  const validationQ = useValidationLog(500);
  const equityQ = useEquityCurve();
  const lastRunQ = useLastPipelineRun();

  const valRows = validationQ.data;
  const scored = (valRows ?? []).filter((r) => r.correct_1d !== null && r.actual_return_1d != null);
  const total = scored.length;
  const avgReturn = total
    ? (scored.reduce((s, r) => s + Number(r.actual_return_1d), 0) / total).toFixed(2)
    : '0';

  const { ALL, byPair } = useMemo(() => buildEquitySeries(equityQ.data ?? []), [equityQ.data]);
  const totalReturn = ALL.length ? ALL[ALL.length - 1].cum.toFixed(2) : '0';
  const acc7 = rolling7dAccuracyPct(valRows ?? []);

  const filteredRows = useMemo(() => {
    const all = mapValidationLogToTableRows(valRows, 200);
    if (filterPair === 'ALL') return all;
    const disp = PAIRS.find((p) => p.label === filterPair)?.display;
    return all.filter((r) => r.pair === disp);
  }, [valRows, filterPair]);

  const chartPts = useMemo(() => {
    const vals = ALL.map((x) => x.cum);
    if (vals.length < 2) return { line: '', pts: [] as [number, number][], fill: '' };
    const mn = Math.min(...vals) - 0.05;
    const mx = Math.max(...vals) + 0.05;
    const n = vals.length;
    const pts = vals.map((v, i) => [(i / (n - 1)) * 800, 112 - ((v - mn) / (mx - mn)) * 104] as [number, number]);
    const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
    return { line, pts, fill: `${line} L800,120 L0,120 Z` };
  }, [ALL]);

  const dateTicks = ALL.filter((_, i) => i % Math.max(1, Math.ceil(ALL.length / 6)) === 0 || i === ALL.length - 1).map((x) =>
    x.date.slice(5),
  );

  const TODAY = lastRunQ.data?.slice(0, 10) ?? ALL[ALL.length - 1]?.date ?? new Date().toISOString().slice(0, 10);
  const firstDate = ALL[0]?.date?.slice(5) ?? '—';

  return (
    <>
      <MacroPulseBar />
      <Nav />
      <main className="flex-1 bg-white" style={{ marginTop: `${SHELL_TOP_OFFSET}px` }}>
        <div className="max-w-[1152px] mx-auto px-6 py-12">
          <div className="mb-10 pb-6 border-b border-[#e5e5e5]">
            <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-2.5">TRACK RECORD</p>
            <h1 className="font-sans font-extrabold text-[32px] text-[#0a0a0a] tracking-tight m-0">Performance</h1>
            <p className="font-sans text-sm text-[#737373] mt-2">Next-day directional validation. Updated daily after market close.</p>
          </div>

          {validationQ.isPending || equityQ.isPending ? (
            <div className="h-48 bg-[#fafafa] border border-[#e5e5e5] animate-pulse mb-8" />
          ) : validationQ.isError ? (
            <p className="text-[#dc2626] font-mono text-sm mb-8">Could not load validation data.</p>
          ) : (
            <>
              <div className="grid grid-cols-4 gap-[1px] bg-[#e5e5e5] shadow-[0_0_0_1px_#e5e5e5] mb-8">
                {[
                  { label: '7D ACCURACY', value: acc7 == null ? '—' : `${acc7.toFixed(1)}%`, color: '#16a34a', sub: 'Rolling window' },
                  {
                    label: 'AVG NEXT-DAY RET',
                    value: `${Number(avgReturn) >= 0 ? '+' : ''}${avgReturn}%`,
                    color: BRAND.usdjpy,
                    sub: 'Per scored call',
                  },
                  {
                    label: 'CUMULATIVE RET',
                    value: `${Number(totalReturn) >= 0 ? '+' : ''}${totalReturn}%`,
                    color: BRAND.eurusd,
                    sub: 'Mean daily return, cum.',
                  },
                  { label: 'CALLS VALIDATED', value: `${total}`, color: '#0a0a0a', sub: `${PAIRS.length} pairs` },
                ].map((m) => (
                  <div key={m.label} className="bg-white px-5 py-5">
                    <p className="font-mono text-[9px] text-[#999] tracking-widest mb-2.5">{m.label}</p>
                    <p className="font-mono text-3xl font-bold tracking-tight leading-none" style={{ color: m.color }}>
                      {m.value}
                    </p>
                    <p className="font-mono text-[10px] text-[#bbb] mt-1.5">{m.sub}</p>
                  </div>
                ))}
              </div>

              <div className="border border-[#e5e5e5] mb-6">
                <div className="px-5 py-4 border-b border-[#f0f0f0] flex justify-between items-center bg-[#fafafa]">
                  <div>
                    <p className="font-mono text-[10px] text-[#888] tracking-widest mb-1">CUMULATIVE RETURN — ALL PAIRS</p>
                    <p className="font-mono text-[11px] text-[#aaa]">
                      {firstDate} — {TODAY} · Next-day spot move in call direction
                    </p>
                  </div>
                  <p className="font-mono text-[22px] font-bold text-[#16a34a] tracking-tight">
                    {Number(totalReturn) >= 0 ? '+' : ''}
                    {totalReturn}%
                  </p>
                </div>

                <div className="px-5 pt-4 pb-2">
                  {ALL.length < 2 ? (
                    <p className="font-mono text-xs text-[#999] py-8">Not enough validation history to plot.</p>
                  ) : (
                    <>
                      <svg width="100%" height="120" viewBox="0 0 800 120" preserveAspectRatio="none" className="block">
                        <defs>
                          <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#16a34a" stopOpacity="0.2" />
                            <stop offset="100%" stopColor="#16a34a" stopOpacity="0" />
                          </linearGradient>
                        </defs>
                        <path d={chartPts.fill} fill="url(#equityGrad)" />
                        <path d={chartPts.line} fill="none" stroke="#16a34a" strokeWidth="2" />
                        {chartPts.pts.map(([x, y], i) => (
                          <circle key={i} cx={x} cy={y} r="3" fill="#16a34a" stroke="#fff" strokeWidth="1.5" />
                        ))}
                      </svg>
                      <div className="flex justify-between pt-1.5 pb-2">
                        {dateTicks.map((d, i) => (
                          <span key={i} className="font-mono text-[9px] text-[#bbb]">
                            {d}
                          </span>
                        ))}
                      </div>
                    </>
                  )}
                </div>

                <div className="grid grid-cols-3 border-t border-[#f0f0f0]">
                  {PAIRS.map((p, i) => {
                    const series = byPair[p.label] ?? [];
                    const cRet = series.length ? series[series.length - 1].cum : 0;
                    return (
                      <div key={p.label} className={`px-5 py-3 ${i < 2 ? 'border-r border-[#f0f0f0]' : ''}`}>
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="font-mono text-[10px] font-bold" style={{ color: p.pairColor }}>
                            {p.display}
                          </span>
                          <span className={`font-mono text-[11px] font-bold ${cRet >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
                            {cRet >= 0 ? '+' : ''}
                            {cRet.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          <div>
            <div className="flex gap-[1px] mb-4 border-b border-[#e5e5e5]">
              {['ALL', ...PAIRS.map((p) => p.display)].map((label) => {
                const pairMeta = PAIRS.find((p) => p.display === label);
                const filterVal = label === 'ALL' ? 'ALL' : (pairMeta?.label ?? 'ALL');
                const active = label === 'ALL' ? filterPair === 'ALL' : filterPair === pairMeta?.label;
                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => setFilterPair(filterVal)}
                    className={`font-mono text-[10px] px-4 py-2.5 transition-colors -mb-[1px] tracking-wide ${active ? 'text-[#0a0a0a] font-bold border-b-2' : 'text-[#999] font-normal border-b-2 border-transparent'}`}
                    style={{ borderBottomColor: active ? pairMeta?.pairColor ?? '#0a0a0a' : 'transparent' }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>

            {validationQ.isPending ? (
              <div className="h-40 animate-pulse bg-[#fafafa] border border-[#e5e5e5]" />
            ) : (
              <ValidationTable rows={filteredRows} tone="light" />
            )}
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
