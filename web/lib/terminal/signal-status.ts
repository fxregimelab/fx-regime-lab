export type SignalLevel = 'ELEVATED' | 'NORMAL' | 'LOW';

const levelText: Record<SignalLevel, string> = {
  ELEVATED: 'text-[#f59e0b]',
  NORMAL: 'text-[#737373]',
  LOW: 'text-[#3b82f6]',
};

export function statusClass(level: SignalLevel): string {
  return `font-mono text-[8px] ${levelText[level]}`;
}

export function cotLevel(pct: number): SignalLevel {
  if (pct >= 70) return 'ELEVATED';
  if (pct <= 30) return 'LOW';
  return 'NORMAL';
}

export function volLevel(vol: number): SignalLevel {
  if (vol >= 8) return 'ELEVATED';
  if (vol <= 4) return 'LOW';
  return 'NORMAL';
}

export function rateDiffLevel(x: number): SignalLevel {
  const a = Math.abs(x);
  if (a >= 3) return 'ELEVATED';
  if (a <= 0.5) return 'LOW';
  return 'NORMAL';
}

export function impliedLevel(v: number | null): SignalLevel {
  if (v == null) return 'LOW';
  if (v >= 8) return 'ELEVATED';
  if (v <= 4) return 'LOW';
  return 'NORMAL';
}
