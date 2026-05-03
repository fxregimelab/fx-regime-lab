'use client';

import { useMemo, useState } from 'react';
import { AlphaLedger } from '@/components/ui/alpha-ledger';
import { useStrategyLedger, useUniverse } from '@/lib/queries';

function hitLabel(v: number | null | undefined): 'WIN' | 'LOSS' | 'PENDING' {
  if (v === null || v === undefined || v === -1) return 'PENDING';
  if (v === 1) return 'WIN';
  return 'LOSS';
}

function hitTone(label: 'WIN' | 'LOSS' | 'PENDING'): string {
  if (label === 'WIN') return 'text-[#22c55e]';
  if (label === 'LOSS') return 'text-[#ef4444]';
  return 'text-[#a3a3a3]';
}

/** Shared body for alpha ledger (terminal + legacy shell). */
export function PerformanceLedgerPageContent() {
  const [selectedPair, setSelectedPair] = useState<string>('EURUSD');
  const universeQ = useUniverse();
  const trackedPairs = universeQ.data ?? [];
  const ledgerQ = useStrategyLedger(selectedPair);
  const rows = ledgerQ.data ?? [];
  const last10 = useMemo(() => rows.slice(0, 10), [rows]);

  return (
    <section className="w-full px-6 md:px-8 py-10">
      <p className="mb-2 text-[9px] tracking-widest text-[#777]">ALPHA LEDGER · OOS</p>
      <h1 className="mb-1 font-sans text-3xl font-bold text-white">Performance</h1>
      <p className="mb-6 font-mono text-[11px] tracking-wide text-[#8a8a8a]">
        Regime-grouped hit rates and Brier (T+5) from forward-walking strategy_ledger.
      </p>

      <div className="mb-6 flex flex-wrap gap-2">
        {trackedPairs.map((pair) => (
          <button
            key={pair}
            type="button"
            onClick={() => setSelectedPair(pair)}
            className={`border border-solid px-3 py-1 text-[10px] tracking-widest tabular-nums rounded-none shadow-none ${
              selectedPair === pair
                ? 'border-[#222] bg-[#111] text-white'
                : 'border-[#111] bg-[#000000] text-[#888]'
            }`}
          >
            {pair}
          </button>
        ))}
      </div>

      {ledgerQ.isPending ? (
        <div className="h-40 animate-pulse border border-solid border-[#111] bg-[#000000]" />
      ) : ledgerQ.isError ? (
        <p className="text-[#ef4444] font-mono text-sm">Could not load strategy ledger.</p>
      ) : (
        <>
          <AlphaLedger rows={rows} />

          <div className="mt-10">
            <p className="mb-3 text-[9px] tracking-widest text-[#777]">LAST 10 RAW SIGNALS</p>
            <div
              className="grid w-full border border-solid border-[#111] bg-[#000000] rounded-none"
              style={{
                gridTemplateColumns: '1fr 1fr 0.9fr 0.65fr 0.65fr 0.65fr',
              }}
            >
              {(['Date', 'Regime', 'Direction', 'T+1', 'T+3', 'T+5'] as const).map((h) => (
                <div
                  key={h}
                  className="border-b border-r border-solid border-[#222] px-2 py-2 text-[9px] tracking-widest text-[#777] last:border-r-0"
                >
                  {h}
                </div>
              ))}
              {last10.length === 0 ? (
                <div className="col-span-6 border-t border-solid border-[#111] px-2 py-6 text-center text-[11px] text-[#777] tabular-nums">
                  No signals yet.
                </div>
              ) : (
                last10.flatMap((r) => {
                  const t1 = hitLabel(r.t1_hit);
                  const t3 = hitLabel(r.t3_hit);
                  const t5 = hitLabel(r.t5_hit);
                  return [
                    <div
                      key={`${r.id}-d`}
                      className="border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums text-white"
                    >
                      {r.date}
                    </div>,
                    <div
                      key={`${r.id}-reg`}
                      className="border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums text-white"
                    >
                      {r.regime}
                    </div>,
                    <div
                      key={`${r.id}-dir`}
                      className="border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums text-white"
                    >
                      {r.direction}
                    </div>,
                    <div
                      key={`${r.id}-t1`}
                      className={`border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums ${hitTone(t1)}`}
                    >
                      {t1}
                    </div>,
                    <div
                      key={`${r.id}-t3`}
                      className={`border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums ${hitTone(t3)}`}
                    >
                      {t3}
                    </div>,
                    <div
                      key={`${r.id}-t5`}
                      className={`border-b border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums ${hitTone(t5)}`}
                    >
                      {t5}
                    </div>,
                  ];
                })
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
