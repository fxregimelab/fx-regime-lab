import type { PairMeta } from './types';

export const PAIR_LABELS: PairMeta['label'][] = ['EURUSD', 'USDJPY', 'USDINR'];

const pairText: Record<PairMeta['label'], string> = {
  EURUSD: 'text-[#4BA3E3]',
  USDJPY: 'text-[#F5923A]',
  USDINR: 'text-[#D94030]',
};

const pairBorderL: Record<PairMeta['label'], string> = {
  EURUSD: 'border-l-2 border-l-[#4BA3E3]',
  USDJPY: 'border-l-2 border-l-[#F5923A]',
  USDINR: 'border-l-2 border-l-[#D94030]',
};

const pairBg: Record<PairMeta['label'], string> = {
  EURUSD: 'bg-[#4BA3E3]',
  USDJPY: 'bg-[#F5923A]',
  USDINR: 'bg-[#D94030]',
};

/** SVG / non-Tailwind fill stroke hex */
const pairHex: Record<PairMeta['label'], string> = {
  EURUSD: '#4BA3E3',
  USDJPY: '#F5923A',
  USDINR: '#D94030',
};

export function pairTextClass(label: PairMeta['label']): string {
  return pairText[label];
}

export function pairBorderLClass(label: PairMeta['label']): string {
  return pairBorderL[label];
}

export function pairBgClass(label: PairMeta['label']): string {
  return pairBg[label];
}

export function pairFillHex(label: PairMeta['label']): string {
  return pairHex[label];
}

/** Regime string → Tailwind bg class for heatmap cells */
export function regimeHeatmapCellClass(regime: string, colors: Record<string, string>): string {
  const key = regime.trim();
  const hex = colors[key] ?? colors.UNKNOWN ?? '#1a1a1a';
  const map: Record<string, string> = {
    '#1e3a5f': 'bg-[#1e3a5f]',
    '#2d5a8e': 'bg-[#2d5a8e]',
    '#3a3a3a': 'bg-[#3a3a3a]',
    '#7a3f1f': 'bg-[#7a3f1f]',
    '#a0522d': 'bg-[#a0522d]',
    '#7a5c00': 'bg-[#7a5c00]',
    '#6b1a1a': 'bg-[#6b1a1a]',
    '#8b2a2a': 'bg-[#8b2a2a]',
    '#1a5a2a': 'bg-[#1a5a2a]',
    '#0d3a1a': 'bg-[#0d3a1a]',
    '#333': 'bg-[#333]',
    '#1a1a1a': 'bg-[#1a1a1a]',
  };
  return map[hex] ?? 'bg-[#1a1a1a]';
}
