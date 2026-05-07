"use client";

import { AlphaLedger } from "@/components/ui/alpha-ledger";
import { useStrategyLedger, useUniverse } from "@/lib/queries";
import { useState } from "react";

/** Shared body for alpha ledger (terminal + legacy shell). */
export function PerformanceLedgerPageContent() {
  const [selectedPair, setSelectedPair] = useState<string>("EURUSD");
  const universeQ = useUniverse();
  const trackedPairs = universeQ.data ?? [];
  const ledgerQ = useStrategyLedger(selectedPair);
  const rows = ledgerQ.data ?? [];

  return (
    <section className="w-full px-6 md:px-8 py-10 shadow-none">
      <p className="mb-2 font-mono text-[9px] tracking-widest text-[#777]">
        ALPHA LEDGER · OOS
      </p>
      <h1 className="mb-1 font-sans text-3xl font-bold text-white shadow-none">
        Performance
      </h1>
      <p className="mb-6 font-mono text-[11px] tracking-wide text-[#8a8a8a] shadow-none">
        Regime-cycle grouped forward-walking ledger (non-neutral). Thermal tint
        from T+5 resolution.
      </p>

      <div className="mb-6 flex flex-wrap gap-2 shadow-none">
        {trackedPairs.map((pair) => (
          <button
            key={pair}
            type="button"
            onClick={() => setSelectedPair(pair)}
            className={`rounded-none border border-solid px-3 py-1 font-mono text-[10px] tracking-widest tabular-nums shadow-none ${
              selectedPair === pair
                ? "border-[#222] bg-[#111] text-white"
                : "border-[#111] bg-[#000000] text-[#888]"
            }`}
          >
            {pair}
          </button>
        ))}
      </div>

      {ledgerQ.isPending ? (
        <div className="h-40 animate-pulse border border-solid border-[#111] bg-[#000000] shadow-none" />
      ) : ledgerQ.isError ? (
        <p className="font-mono text-sm text-[#ef4444] shadow-none">
          Could not load strategy ledger.
        </p>
      ) : (
        <AlphaLedger rows={rows} />
      )}
    </section>
  );
}
