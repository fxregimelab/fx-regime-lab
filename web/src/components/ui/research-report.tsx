'use client';

import Image from 'next/image';
import { fmt2, fmtPct, fmtKM } from './utils';

type PairMeta = {
  label: string;
  display: string;
  pairColor: string;
};

type RegimeCallLite = {
  regime?: string;
  confidence?: number;
  rate_signal?: string | null;
  cot_signal?: string | null;
  vol_signal?: string | null;
  oi_signal?: string | null;
  signal_composite?: number;
  primary_driver?: string | null;
};

type SignalLite = {
  spot?: number | null;
  rate_diff_2y?: number | null;
  rate_diff_10y?: number | null;
  realized_vol_20d?: number | null;
  realized_vol_5d?: number | null;
  cot_lev_money_net?: number | null;
  oi_delta?: number | null;
};

type AnalogLite = {
  rank: number;
  match_date: string;
  match_score: number;
  forward_30d_return: number | null;
  regime_stability: number | null;
  context_label: string | null;
};

type HistLite = {
  date: string;
  spot?: number | null;
  rate_diff_2y?: number | null;
  rate_diff_10y?: number | null;
  cot_lev_money_net?: number | null;
};

function seriesPath(values: number[], width: number, height: number): string {
  if (!values.length) return '';
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return values
    .map((v, i) => {
      const x = (i / Math.max(1, values.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');
}

function sectionSignalTone(signal?: string | null): { label: string; color: string } {
  if (signal === 'BULLISH') return { label: 'Positive Bias', color: '#0b3d91' };
  if (signal === 'BEARISH') return { label: 'Negative Bias', color: '#8b1d1d' };
  return { label: 'Neutral', color: '#4a4a4a' };
}

export function ResearchReport({
  pair,
  today,
  call,
  sig,
  analysisText,
  analogs,
  history,
}: {
  pair: PairMeta;
  today: string;
  call?: RegimeCallLite;
  sig?: SignalLite;
  analysisText: string;
  analogs: AnalogLite[];
  history: HistLite[];
}) {
  const h12m = history.slice(-252);
  const spotVals = h12m.filter((r) => r.spot != null).map((r) => Number(r.spot));
  const y2Vals = h12m.filter((r) => r.rate_diff_2y != null).map((r) => Number(r.rate_diff_2y));
  const y10Vals = h12m.filter((r) => r.rate_diff_10y != null).map((r) => Number(r.rate_diff_10y));
  const cotVals = h12m.filter((r) => r.cot_lev_money_net != null).map((r) => Number(r.cot_lev_money_net));
  const avgFwd = analogs.length ? analogs.reduce((a, b) => a + (b.forward_30d_return ?? 0), 0) / analogs.length : 0;
  const avgStability = analogs.length ? analogs.reduce((a, b) => a + (b.regime_stability ?? 0), 0) / analogs.length : 0;

  return (
    <article className="hidden print:block research-report text-[#000] bg-white tabular-nums">
      <section className="report-page">
        <header className="flex items-start justify-between border-b border-[#d0d0d0] pb-4">
          <div className="flex items-center gap-3">
            <Image src="/logos/logo-without-bg.png" alt="FX Regime Lab" width={36} height={36} />
            <div>
              <h1 className="font-sans text-[24px] font-extrabold tracking-tight">FX Regime Lab</h1>
              <p className="font-sans text-[11px] text-[#888] tracking-wide">Strictly Confidential - Institutional Use Only</p>
            </div>
          </div>
          <div className="text-right">
            <p className="font-sans text-[11px] text-[#888]">Research Briefing</p>
            <p className="font-sans text-[13px] font-bold">{pair.display}</p>
            <p className="font-sans text-[11px] text-[#888]">{today}</p>
          </div>
        </header>

        <div className="mt-5">
          <h2 className="font-sans text-[16px] font-bold mb-2">1. Executive Summary</h2>
          <p className="font-serif text-[13px] leading-6 text-[#111]">{analysisText || 'No AI briefing available for this reporting cycle.'}</p>
          <div className="grid grid-cols-3 gap-4 mt-4">
            <div className="border border-[#d8d8d8] p-3">
              <p className="font-sans text-[11px] text-[#888]">Active Regime</p>
              <p className="font-sans text-[14px] font-bold">{call?.regime ?? '—'}</p>
            </div>
            <div className="border border-[#d8d8d8] p-3">
              <p className="font-sans text-[11px] text-[#888]">Confidence Meter</p>
              <p className="font-sans text-[14px] font-bold">{fmtPct(call?.confidence)}</p>
            </div>
            <div className="border border-[#d8d8d8] p-3">
              <p className="font-sans text-[11px] text-[#888]">Spot</p>
              <p className="font-sans text-[14px] font-bold">{sig?.spot != null ? Number(sig.spot).toFixed(pair.label === 'USDJPY' ? 2 : 4) : '—'}</p>
            </div>
          </div>
        </div>

        <div className="mt-6">
          <h2 className="font-sans text-[16px] font-bold mb-2">2. Signal Convergence</h2>
          <div className="grid grid-cols-2 gap-3">
            {[
              ['RATES', call?.rate_signal],
              ['COT', call?.cot_signal],
              ['VOL', call?.vol_signal],
              ['OI', call?.oi_signal],
            ].map(([name, signal]) => {
              const tone = sectionSignalTone(signal);
              return (
                <div key={name} className="border border-[#d8d8d8] p-3">
                  <p className="font-sans text-[11px] text-[#888]">{name}</p>
                  <p className="font-sans text-[14px] font-bold" style={{ color: tone.color }}>
                    {tone.label}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="report-page">
        <h2 className="font-sans text-[16px] font-bold mb-2">3. Historical Analogs</h2>
        {analogs.length ? (
          <div className="space-y-3">
            {analogs.map((a) => (
              <div key={`${a.rank}-${a.match_date}`} className="border border-[#d8d8d8] p-3">
                <p className="font-sans text-[13px] font-bold">
                  Analog Match: {Math.round(a.match_score)}% with {new Date(a.match_date).toLocaleString('en-US', { month: 'short', year: 'numeric' })}
                </p>
                <p className="font-serif text-[12px] text-[#222] mt-1">
                  This period aligns on directional trend structure and composite pressure profile. Both periods saw yield-spread momentum and positioning stress appearing
                  in tandem with regime inflection behavior.
                </p>
                <p className="font-sans text-[11px] text-[#888] mt-2">
                  30D Forward Return: <span className="text-[#000]">{(a.forward_30d_return ?? 0).toFixed(2)}%</span> | Regime Stability:{' '}
                  <span className="text-[#000]">{(a.regime_stability ?? 0).toFixed(0)}%</span>
                </p>
              </div>
            ))}
            <p className="font-sans text-[11px] text-[#888]">
              Aggregate analog expectation: <span className="text-[#000]">{avgFwd.toFixed(2)}%</span> over 30D with{' '}
              <span className="text-[#000]">{avgStability.toFixed(0)}%</span> average stability.
            </p>
          </div>
        ) : (
          <p className="font-serif text-[13px]">Historical analogs are unavailable for this cycle.</p>
        )}

        <h2 className="font-sans text-[16px] font-bold mt-6 mb-2">4. Technical Snapshots</h2>
        <div className="space-y-4">
          <div className="border border-[#d8d8d8] p-3">
            <p className="font-sans text-[12px] font-bold mb-1">Price Action (Last 12 Months)</p>
            <svg width="100%" height="120" viewBox="0 0 720 120" preserveAspectRatio="none">
              <path d={seriesPath(spotVals, 720, 120)} fill="none" stroke="#0b3d91" strokeWidth="2" />
            </svg>
          </div>
          <div className="border border-[#d8d8d8] p-3">
            <p className="font-sans text-[12px] font-bold mb-1">Yield Spread Trend</p>
            <svg width="100%" height="120" viewBox="0 0 720 120" preserveAspectRatio="none">
              <path d={seriesPath(y2Vals, 720, 120)} fill="none" stroke="#1f4e79" strokeWidth="2" />
              <path d={seriesPath(y10Vals, 720, 120)} fill="none" stroke="#7f6000" strokeWidth="2" />
            </svg>
          </div>
          <div className="border border-[#d8d8d8] p-3">
            <p className="font-sans text-[12px] font-bold mb-1">COT Position Trend</p>
            <svg width="100%" height="120" viewBox="0 0 720 120" preserveAspectRatio="none">
              {cotVals.map((v, i) => {
                const x = (i / Math.max(1, cotVals.length - 1)) * 720;
                const barH = Math.min(110, Math.abs(v) / (Math.max(...cotVals.map((n) => Math.abs(n)), 1)) * 110);
                const y = v >= 0 ? 60 - barH : 60;
                return <rect key={`${i}-${v}`} x={x} y={y} width={Math.max(1, 700 / Math.max(cotVals.length, 50))} height={barH} fill="#4a4a4a" />;
              })}
            </svg>
          </div>
        </div>
      </section>
    </article>
  );
}

