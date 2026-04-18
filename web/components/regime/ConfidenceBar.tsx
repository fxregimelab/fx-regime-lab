// Confidence progress bar — greyscale fill; width reflects value (0–100).
'use client';

import type { CSSProperties } from 'react';

type Props = {
  value: number | null | undefined;
  /** Light track/fill for shell cards; dark for terminal surfaces. */
  tone?: 'light' | 'dark';
  /** When false, render only the track + fill (no label row). */
  showCaption?: boolean;
  /**
   * Shell pair cards: tiered grey opacity (low / moderate) and accent fill only for high conviction.
   */
  tieredConviction?: boolean;
};

export function ConfidenceBar({
  value,
  tone = 'dark',
  showCaption = true,
  tieredConviction = false,
}: Props) {
  const pct = value == null ? 0 : Math.min(100, Math.max(0, value * 100));
  const track = tone === 'light' ? 'bg-neutral-200' : 'bg-neutral-800';
  const fill = tone === 'light' ? 'bg-neutral-600' : 'bg-neutral-300';

  const tieredFillStyle = (): CSSProperties => {
    if (value == null) return { width: `${pct}%` };
    if (pct <= 30) {
      return { width: `${pct}%`, opacity: 0.4, backgroundColor: '#525252' };
    }
    if (pct <= 60) {
      return { width: `${pct}%`, opacity: 0.7, backgroundColor: '#525252' };
    }
    return { width: `${pct}%`, opacity: 1, backgroundColor: '#e8a045' };
  };

  return (
    <div>
      {showCaption ? (
        <div className="mb-1 flex justify-between font-mono text-[10px] text-neutral-500">
          <span>Confidence</span>
          <span>{value == null ? '—' : `${pct.toFixed(0)}%`}</span>
        </div>
      ) : null}
      <div className={`h-1.5 w-full overflow-hidden rounded-full ${track}`}>
        {tieredConviction && tone === 'light' ? (
          <div className="h-full transition-all" style={tieredFillStyle()} />
        ) : (
          <div className={`h-full ${fill} transition-all`} style={{ width: `${pct}%` }} />
        )}
      </div>
    </div>
  );
}
