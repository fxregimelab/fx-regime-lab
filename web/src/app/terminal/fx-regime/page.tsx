'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ConfidenceBar } from '@/components/ui/confidence-bar';
import { PAIRS } from '@/lib/mockData';
import { fmtPct } from '@/components/ui/utils';
import { motion } from 'framer-motion';
import { useLatestRegimeCalls, useLatestSignals } from '@/lib/queries';

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' as const } },
};

/** Pair selection grid — matches the main terminal index cards, without the strategies panel. */
export default function FxRegimePairSelectionPage() {
  const router = useRouter();
  const regimeQ = useLatestRegimeCalls();
  const signalsQ = useLatestSignals();

  const calls = regimeQ.data;
  const sigs = signalsQ.data;
  const err = regimeQ.isError || signalsQ.isError;
  const pending = regimeQ.isPending || signalsQ.isPending;

  return (
    <div className="min-h-screen bg-[#000000] text-[#e8e8e8] font-sans">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="max-w-[1200px] mx-auto py-10 px-6"
        style={{ marginTop: 'var(--terminal-nav-h, 104px)' }}
      >
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8">
          <div>
            <p className="font-mono text-[9px] text-[#666] tracking-widest mb-2">FX REGIME</p>
            <h1 className="font-mono text-lg font-bold text-white tracking-tight">Pair selection</h1>
            <p className="font-mono text-[10px] text-[#777] mt-1 max-w-md">
              Choose a pair to open the regime terminal. Same layout as the main terminal index.
            </p>
          </div>
          <Link
            href="/terminal"
            className="font-mono text-[10px] text-[#888] hover:text-[#ccc] transition-colors shrink-0"
          >
            ← Terminal overview
          </Link>
        </div>

        {pending ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-0.5 mb-8">
            {[0, 1, 2].map((i) => (
              <div key={i} className="bg-[#0d0d0d] border border-[#111] p-4 h-36 animate-pulse" />
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
                  className="bg-[#0d0d0d] border border-[#111] p-4 text-left transition-colors cursor-pointer hover:bg-[#111]"
                  style={{ borderTop: `2px solid ${p.pairColor}` }}
                >
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-mono text-xs font-bold tracking-wide" style={{ color: p.pairColor }}>
                      {p.display}
                    </span>
                    {chg != null && (
                      <span
                        className={`font-mono text-[11px] font-bold tabular-nums ${chg >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}
                      >
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

        {err && (
          <p className="font-mono text-[10px] text-[#ef4444] mb-4">Live data failed to load — cards may be incomplete.</p>
        )}
      </motion.div>
    </div>
  );
}
