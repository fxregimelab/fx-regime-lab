'use client';

import { useEffect, useState } from 'react';

function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}

export function PipelineOfflineCard() {
  const [countdown, setCountdown] = useState(47);
  useEffect(() => {
    const t = setInterval(() => setCountdown((c) => (c > 0 ? c - 1 : 60)), 1000);
    return () => clearInterval(t);
  }, []);

  const rows = [
    ['SIGNALS', 'FAILED'],
    ['REGIME CALLS', 'STALE'],
    ['VALIDATION', 'STALE'],
    ['BRIEF', 'MISSING'],
  ] as const;

  return (
    <div className="border border-[#1e1e1e] bg-[#0c0c0c] p-3.5">
      <div className="mb-2.5 flex items-center gap-1.5">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#ef4444]" />
        <span className="font-mono text-[10px] font-bold tracking-wide text-[#ef4444]">
          PIPELINE OFFLINE
        </span>
      </div>
      {rows.map(([label, status]) => (
        <div key={label} className="flex justify-between border-b border-[#0f0f0f] py-1.5">
          <span className="font-mono text-[9px] tracking-wide text-[#888]">{label}</span>
          <span
            className={`font-mono text-[9px] font-bold ${status === 'FAILED' ? 'text-[#ef4444]' : 'text-amber-400'}`}
          >
            {status}
          </span>
        </div>
      ))}
      <div className="mt-2.5 flex items-center justify-between border-t border-[#141414] pt-2.5">
        <span className="font-mono text-[9px] text-[#333]">Last run: {utcToday()} 07:12 UTC</span>
        <span className="font-mono text-[9px] text-[#555]">Retry in {countdown}s</span>
      </div>
    </div>
  );
}
