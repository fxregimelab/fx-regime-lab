'use client';

import { BRAND } from '@/lib/mockData';
import { ConfidenceBar } from './confidence-bar';
import { fmt2, fmtInt, timeAgo } from './utils';
import { MethodologyPopover } from './methodology-popover';

export function HeroRegimeCard({
  call,
  signals,
  connectionStatus = 'pending',
  timestamp,
}: {
  call: Record<string, unknown> | null | undefined;
  signals: Record<string, unknown> | null | undefined;
  connectionStatus?: 'live' | 'error' | 'pending';
  timestamp?: string;
}) {
  const pct = call ? Math.round(Number(call.confidence) * 100) : null;
  const chg = signals?.day_change_pct as number | null | undefined;
  const live = connectionStatus === 'live';
  const err = connectionStatus === 'error';

  return (
    <div className="bg-[#080808] border border-[#1e1e1e]">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1a1a1a]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 inline-block shrink-0" style={{ background: BRAND.eurusd }} />
          <span className="font-mono text-xs font-bold tracking-widest" style={{ color: BRAND.eurusd }}>
            EUR/USD
          </span>
        </div>
        <div className="flex items-center gap-2.5">
          {chg != null && (
            <span className={`font-mono text-[11px] font-semibold ${chg >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
              {chg >= 0 ? '+' : ''}
              {chg.toFixed(2)}%
            </span>
          )}
          <div className="flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full shrink-0 ${err ? 'bg-[#ef4444]' : live ? 'hidden' : 'bg-[#737373]'}`}
            />
            <span
              className={`font-mono text-[10px] ${err ? 'text-[#ef4444]' : live ? 'text-[#555]' : 'text-[#666]'}`}
            >
              {err ? 'OFFLINE' : live ? 'SYNCED DATA' : '…'}
            </span>
          </div>
        </div>
      </div>

      <div className="p-5">
        <div className="mb-5">
          <p className="font-mono text-[9px] text-[#999] tracking-[0.12em] mb-1">SPOT</p>
          <p className="font-mono text-[32px] font-bold text-white tracking-[-0.02em] leading-none tabular-nums">
            {signals?.spot != null ? Number(signals.spot).toFixed(4) : '—'}
          </p>
          {timestamp && (
            <p className="font-mono text-[9px] text-[#666] tracking-[0.06em] mt-2">SYNCED: {timestamp}</p>
          )}
        </div>

        <div className="mb-5 pb-4 border-b border-[#1a1a1a]">
          <p className="font-mono text-[9px] text-[#999] tracking-[0.12em] mb-1.5">REGIME</p>
          <p className="font-mono text-[13px] font-bold text-white tracking-[0.04em] leading-snug">
            {(call?.regime as string) ?? '—'}
          </p>
        </div>

        <div className="mb-5">
          <div className="flex justify-between items-baseline mb-1.5">
            <p className="font-mono text-[9px] text-[#444] tracking-[0.12em]">CONFIDENCE</p>
            <p className="font-mono text-[28px] font-bold tracking-[-0.03em] leading-none" style={{ color: BRAND.eurusd }}>
              {pct ?? '—'}
              <span className="text-sm font-normal text-[#555]">{pct != null ? '%' : ''}</span>
            </p>
          </div>
          <ConfidenceBar value={call?.confidence != null ? Number(call.confidence) : null} tone="dark" color={BRAND.eurusd} />
        </div>

        <div className="border-t border-[#141414]">
          {[
            ['RATE DIFF 2Y', fmt2(signals?.rate_diff_2y as number | null | undefined), 'rateDiff'],
            ['COT PERCENTILE', fmtInt(signals?.cot_percentile as number | null | undefined), 'cot'],
            ['REALIZED VOL 20D', fmt2(signals?.realized_vol_20d as number | null | undefined), 'realizedVol'],
            ['IMPLIED VOL 30D', fmt2(signals?.implied_vol_30d as number | null | undefined), null],
            ['SIGNAL COMPOSITE', fmt2(call?.signal_composite as number | null | undefined), 'composite'],
          ].map(([label, value, key]) => (
            <div key={label as string} className="flex justify-between items-center py-2.5 border-b border-[#111]">
              <span className="font-mono text-[10px] text-[#aaa] tracking-[0.06em] flex items-center">
                {label as string}
                {key && <MethodologyPopover metricKey={key as 'cot' | 'rateDiff' | 'realizedVol' | 'composite'} />}
              </span>
              <span className="font-mono text-xs text-white font-bold tabular-nums">{value as React.ReactNode}</span>
            </div>
          ))}
        </div>

        <div className="flex justify-between items-center mt-3 pt-3 border-t border-[#141414]">
          {call?.primary_driver ? (
            <p className="font-sans text-[11px] text-[#888] italic max-w-[70%] truncate" title={String(call.primary_driver)}>
              &quot;{String(call.primary_driver)}&quot;
            </p>
          ) : (
            <div />
          )}
          <p className="font-mono text-[9px] text-[#666]">{timeAgo(call?.created_at as string | undefined)}</p>
        </div>
      </div>
    </div>
  );
}
