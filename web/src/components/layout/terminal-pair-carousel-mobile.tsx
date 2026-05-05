'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { PAIRS } from '@/lib/mockData';
import { useLatestSignals } from '@/lib/queries';

/** Horizontal swipe row for G10 pairs — mobile only; sits below TerminalNav. */
export function TerminalPairCarouselMobile() {
  const currentRoute = usePathname() || '';
  const { data: signals } = useLatestSignals();

  return (
    <div
      className="md:hidden shrink-0 border-b border-[var(--bg-hover,#111)] bg-[var(--bg-surface,#080808)]"
      aria-label="Pair navigation"
    >
      <div className="flex overflow-x-auto whitespace-nowrap hide-scrollbar gap-1 px-3 py-2 touch-pan-x">
        {PAIRS.map((p) => {
          const active = currentRoute.includes(p.urlSlug);
          const sig = signals?.[p.label];
          const chgPct = sig?.day_change_pct as number | undefined;
          return (
            <Link
              key={p.label}
              href={`/terminal/fx-regime/${p.urlSlug}`}
              className={`inline-flex shrink-0 items-center gap-2 rounded-none border px-3 py-2 font-mono text-[10px] no-underline transition-colors ${
                active ? 'border-[#333] bg-[#141414]' : 'border-transparent bg-transparent'
              }`}
              style={{
                borderBottomWidth: active ? 2 : 1,
                borderBottomColor: active ? p.pairColor : 'transparent',
              }}
            >
              <span className="font-bold tabular-nums" style={{ color: p.pairColor }}>
                {p.display}
              </span>
              {sig && chgPct != null ? (
                <span
                  className={`tabular-nums ${chgPct >= 0 ? 'text-[var(--color-bullish)]' : 'text-[var(--color-bearish)]'}`}
                >
                  {chgPct >= 0 ? '+' : ''}
                  {chgPct.toFixed(2)}%
                </span>
              ) : null}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
