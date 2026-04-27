'use client';

import { useRouter } from 'next/navigation';
import { TerminalNav } from '@/components/layout/terminal-nav';
import { ConfidenceBar } from '@/components/ui/confidence-bar';
import { PAIRS, BRAND } from '@/lib/mockData';
import { fmtPct, fmt2 } from '@/components/ui/utils';
import { motion } from 'framer-motion';
import { useLatestRegimeCalls, useLatestSignals, useLastPipelineRun } from '@/lib/queries';

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' as const } },
};

export default function TerminalIndex() {
  const router = useRouter();
  const regimeQ = useLatestRegimeCalls();
  const signalsQ = useLatestSignals();
  const lastRunQ = useLastPipelineRun();

  const calls = regimeQ.data;
  const sigs = signalsQ.data;
  const err = regimeQ.isError || signalsQ.isError;
  const pending = regimeQ.isPending || signalsQ.isPending;
  const asOfDay =
    lastRunQ.data?.slice(0, 10) ??
    (calls?.EURUSD as { date?: string } | undefined)?.date ??
    new Date().toISOString().slice(0, 10);
  const utcClock = lastRunQ.data ? `${new Date(lastRunQ.data).toISOString().slice(11, 16)} UTC` : '—';

  return (
    <div className="min-h-screen bg-[#080808] text-[#e8e8e8] font-sans">
      <TerminalNav />
      <motion.div variants={container} initial="hidden" animate="show" className="max-w-[1200px] mx-auto py-10 px-6">
        {pending ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0.5 mb-8">
            {[0, 1, 2].map((i) => (
              <div key={i} className="bg-[#0d0d0d] border border-[#1e1e1e] p-4 h-36 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0.5 mb-8">
            {PAIRS.map((p) => {
              const call = calls?.[p.label];
              const sig = sigs?.[p.label];
              const chg = sig?.day_change_pct as number | undefined;

              return (
                <motion.button
                  variants={item}
                  key={p.label}
                  type="button"
                  onClick={() => router.push(`/terminal/fx-regime/${p.urlSlug}`)}
                  className="bg-[#0d0d0d] border border-[#1e1e1e] p-4 text-left transition-colors cursor-pointer hover:bg-[#111]"
                  style={{ borderTop: `2px solid ${p.pairColor}` }}
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-mono text-xs font-bold tracking-wide" style={{ color: p.pairColor }}>
                      {p.display}
                    </span>
                    {chg != null && (
                      <span className={`font-mono text-[11px] font-bold ${chg >= 0 ? 'text-[#4ade80]' : 'text-[#f87171]'}`}>
                        {chg >= 0 ? '+' : ''}
                        {chg.toFixed(2)}%
                      </span>
                    )}
                  </div>
                  <p className="font-mono text-[26px] font-bold text-white tracking-tight leading-none mb-1.5">
                    {sig?.spot != null ? Number(sig.spot).toFixed(p.label === 'USDJPY' ? 2 : 4) : '—'}
                  </p>
                  <p className="font-mono text-[10px] font-bold text-[#c0c0c0] tracking-wide mb-2.5">
                    {(call?.regime as string) ?? '—'}
                  </p>
                  <ConfidenceBar value={call?.confidence != null ? Number(call.confidence) : null} tone="dark" color={p.pairColor} />
                  <p className="font-mono text-[9px] text-[#555] mt-1.5 tracking-widest">
                    CONF {fmtPct(call?.confidence as number | undefined)}
                  </p>
                </motion.button>
              );
            })}
          </div>
        )}

        <motion.p variants={item} className="font-mono text-[9px] text-[#666] tracking-widest mb-3">
          STRATEGIES
        </motion.p>

        <motion.div
          variants={item}
          className="border border-[#1e1e1e] cursor-pointer hover:border-[#2a2a2a] transition-colors"
          onClick={() => router.push('/terminal/fx-regime')}
          onKeyDown={(e) => e.key === 'Enter' && router.push('/terminal/fx-regime')}
          role="button"
          tabIndex={0}
        >
          <div className="px-5 py-3.5 border-b border-[#1a1a1a] flex justify-between bg-[#0c0c0c]">
            <div className="flex items-center gap-3">
              <span className="font-mono text-[9px] text-[#777] tracking-widest">ACTIVE STRATEGY</span>
              <span className="font-mono text-[11px] font-bold" style={{ color: BRAND.accent }}>
                FX-REGIME
              </span>
            </div>
            <span className="font-mono text-[10px] text-[#666]">Open →</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 border-b border-[#141414]">
            {PAIRS.map((p, i) => {
              const call = calls?.[p.label];
              return (
                <div key={p.label} className={`p-4 ${i < 2 ? 'border-b md:border-b-0 md:border-r border-[#141414]' : ''}`}>
                  <p className="font-mono text-[10px] font-bold mb-1.5" style={{ color: p.pairColor }}>
                    {p.display}
                  </p>
                  <p className="font-mono text-[10px] text-[#c0c0c0] font-bold tracking-wide mb-2">
                    {(call?.regime as string) ?? '—'}
                  </p>
                  <div className="flex gap-4">
                    <span className="font-mono text-[10px] text-[#999]">
                      CONF{' '}
                      <span className="text-[#e0e0e0] font-bold">{fmtPct(call?.confidence as number | undefined)}</span>
                    </span>
                    <span className="font-mono text-[10px] text-[#666]">
                      COMPOSITE{' '}
                      <span className="text-[#e0e0e0] font-bold">{fmt2(call?.signal_composite as number | undefined)}</span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="px-5 py-3 flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full shrink-0 ${err ? 'bg-[#f87171]' : pending ? 'bg-[#737373]' : 'live-indicator animate-pulse'}`}
            />
            <span className={`font-mono text-[10px] ${err ? 'text-[#f87171]' : 'text-[#777]'}`}>
              {err ? 'ERROR' : 'Pipeline'}: {asOfDay} {utcClock}
            </span>
          </div>
        </motion.div>

        <motion.div variants={item} className="border border-dashed border-[#141414] mt-0.5 px-5 py-3.5">
          <span className="font-mono text-[9px] text-[#222] tracking-widest">MORE STRATEGIES — PHASE 2+</span>
        </motion.div>
      </motion.div>
    </div>
  );
}
