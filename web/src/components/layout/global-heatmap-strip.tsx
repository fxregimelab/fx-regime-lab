'use client';

import { usePathname, useRouter } from 'next/navigation';
import { PAIRS } from '@/lib/mockData';
import { useLatestSignals } from '@/lib/queries';

/**
 * 48px pair heat strip — daily Δ as proxy for short-horizon impulse (no 15m feed in schema).
 * Client-side navigation via Next router (no full document reload).
 */
export function GlobalHeatmapStrip() {
  const router = useRouter();
  const pathname = usePathname() || '';
  const { data: signals } = useLatestSignals();

  return (
    <div
      className="hidden md:flex w-[48px] shrink-0 flex-col items-center border-r border-[#111] bg-[#000000] py-3 gap-2 shadow-none"
      aria-label="Pair heatmap strip"
    >
      {PAIRS.map((p) => {
        const chg = signals?.[p.label]?.day_change_pct as number | undefined;
        const active = pathname.includes(`/fx-regime/${p.urlSlug}`);
        const up = chg != null && chg > 0;
        const down = chg != null && chg < 0;
        return (
          <button
            key={p.label}
            type="button"
            title={
              chg != null
                ? `${p.display} · ${chg >= 0 ? '+' : ''}${chg.toFixed(2)}% (daily)`
                : p.display
            }
            onClick={() => router.push(`/terminal/fx-regime/${p.urlSlug}`)}
            className={`h-7 w-7 shrink-0 rounded-none border shadow-none transition-colors ${
              active ? 'border-white/50' : 'border-[#333]'
            } ${
              up
                ? 'bg-emerald-500/20 border-emerald-500/55 outline outline-1 outline-emerald-500/35 outline-offset-0'
                : down
                  ? 'bg-red-500/15 border-red-500/50 outline outline-1 outline-red-500/35 outline-offset-0'
                  : 'bg-[#080808]'
            }`}
          />
        );
      })}
    </div>
  );
}
