'use client';

import { PULSE_BAR_H } from './macro-pulse-bar';

/** Fixed height for sticky offset math (py-2 + single line mono). */
export const SYSTEMIC_BANNER_H = 32;

type SystemicClusterBannerProps = {
  /** When true, render as a static strip inside terminal chrome (no sticky offset). */
  embedded?: boolean;
};

export function SystemicClusterBanner({ embedded = false }: SystemicClusterBannerProps) {
  const base =
    'w-full bg-[#2a2208] border-b border-[#6b5900] font-mono text-[10px] tracking-widest text-[#fbbf24] px-4 py-2 text-center leading-tight';
  if (embedded) {
    return (
      <div
        className={base}
        style={{ minHeight: `${SYSTEMIC_BANNER_H}px`, boxShadow: 'none' }}
        role="status"
      >
        [ SYSTEMIC TREND DETECTED: UNIFORM DOLLAR FLOW ]
      </div>
    );
  }
  return (
    <div
      className={`sticky z-[95] ${base}`}
      style={{ top: `${PULSE_BAR_H}px`, minHeight: `${SYSTEMIC_BANNER_H}px`, boxShadow: 'none' }}
      role="status"
    >
      [ SYSTEMIC TREND DETECTED: UNIFORM DOLLAR FLOW ]
    </div>
  );
}
