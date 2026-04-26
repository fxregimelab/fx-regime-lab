'use client';

import { useMemo, useState } from 'react';

function regimeForScore(v: number): string {
  if (v > 1) return 'STRONG USD STRENGTH';
  if (v >= 0.4) return 'MODERATE USD STRENGTH';
  if (v >= -0.4) return 'NEUTRAL';
  if (v >= -1) return 'MODERATE USD WEAKNESS';
  return 'STRONG USD WEAKNESS';
}

export function CompositeSimulator() {
  const [v, setV] = useState(0);
  const label = useMemo(() => regimeForScore(v), [v]);
  return (
    <div className="border border-[#e5e5e5] p-6">
      <label
        htmlFor="composite-slider"
        className="font-mono text-[10px] tracking-wide text-[#a0a0a0]"
      >
        COMPOSITE INPUT
      </label>
      <input
        id="composite-slider"
        type="range"
        min={-2}
        max={2}
        step={0.01}
        value={v}
        onChange={(e) => setV(Number(e.target.value))}
        className="mt-4 block w-full accent-[#F5923A]"
      />
      <div className="mt-2 flex justify-between font-mono text-[9px] text-[#bbb]">
        <span>-2</span>
        <span>{v.toFixed(2)}</span>
        <span>+2</span>
      </div>
      <p className="mt-6 font-sans text-[15px] font-semibold uppercase text-[#0a0a0a]">{label}</p>
    </div>
  );
}
