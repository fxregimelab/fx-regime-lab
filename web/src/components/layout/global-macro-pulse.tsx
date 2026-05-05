'use client';

import { MacroPulseBar, PULSE_BAR_H } from '@/components/ui/macro-pulse-bar';

/** Persistent global macro strip — fixed to viewport top on every route. */
export function GlobalMacroPulse() {
  return (
    <div
      className="fixed top-0 left-0 right-0 z-[110] border-b border-[#111] bg-[#000000] shadow-none"
      style={{ height: PULSE_BAR_H }}
      role="presentation"
    >
      <MacroPulseBar embeddedInGlobalChrome />
    </div>
  );
}
