'use client';

import { useState } from 'react';

const steps = [
  {
    id: 'ingest',
    n: '01',
    title: 'Ingest',
    body: 'The scheduler pulls spot, yields, COT, volatility, and calendar feeds into a single daily bundle. Each source is validated for freshness before any transforms run.',
    body2:
      'Failures short-circuit the pair that depends on the missing series while leaving unrelated pairs untouched.',
  },
  {
    id: 'normalize',
    n: '02',
    title: 'Normalize',
    body: 'Raw levels are converted into rolling percentiles and z-scores so EUR, JPY, and INR live on comparable footing.',
    body2: 'Winsorized tails stop one bad print from dominating the composite.',
  },
  {
    id: 'composite',
    n: '03',
    title: 'Composite',
    body: 'Percentile blocks are weighted into a directional score bounded roughly between -2 and +2.',
    body2:
      'Weights tilt toward rate differentials, then positioning, then volatility, with INR-specific overlays where needed.',
  },
  {
    id: 'regime',
    n: '04',
    title: 'Regime',
    body: 'The composite lands in threshold bands that map to human-readable regime labels plus a confidence read.',
    body2:
      'Vol-gate logic can override the label when implied volatility spikes through its historical ceiling.',
  },
  {
    id: 'validate',
    n: '05',
    title: 'Validate',
    body: 'Each morning call is frozen in the log and checked the next session against realized spot direction.',
    body2: 'Outcomes and next-day returns stay public with no retroactive edits.',
  },
] as const;

export function MethodologyTabs() {
  const [i, setI] = useState(0);
  const step = steps[i];
  return (
    <div className="border border-[#e5e5e5]">
      <div className="flex flex-wrap border-b border-[#e5e5e5] bg-[#fafafa]">
        {steps.map((s, idx) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setI(idx)}
            className={`flex min-w-[100px] flex-1 flex-col items-start gap-1 border-r border-[#f0f0f0] px-3 py-3 text-left last:border-r-0 ${
              i === idx ? 'border-b-2 border-b-[#F5923A]' : 'border-b-2 border-b-transparent'
            }`}
          >
            <span className="font-mono text-[10px] text-[#a0a0a0]">{s.n}</span>
            <span className="font-mono text-[10px] font-semibold text-[#0a0a0a]">{s.title}</span>
          </button>
        ))}
      </div>
      <div className="p-6">
        <p className="font-sans text-[14px] leading-relaxed text-[#444]">{step.body}</p>
        <p className="mt-3 font-sans text-[14px] leading-relaxed text-[#444]">{step.body2}</p>
      </div>
    </div>
  );
}
