import { REGIME_COLORS, isRegimeLabel } from '@/lib/constants/regimes';
import type { RegimeLabel } from '@/lib/types/regime';

export function getRegimeColor(regime: string): string {
  return isRegimeLabel(regime) ? REGIME_COLORS[regime] : 'bg-neutral-700 text-white';
}

/** Rough directional hint for sparklines or arrows (not a trade signal). */
export function getRegimeDirection(regime: string): 'up' | 'down' | 'flat' {
  if (!isRegimeLabel(regime)) return 'flat';
  const r = regime as RegimeLabel;
  if (
    r === 'STRONG USD STRENGTH' ||
    r === 'MODERATE USD STRENGTH' ||
    r === 'STRONG DEPRECIATION PRESSURE' ||
    r === 'MODERATE DEPRECIATION PRESSURE'
  ) {
    return 'up';
  }
  if (
    r === 'STRONG USD WEAKNESS' ||
    r === 'MODERATE USD WEAKNESS' ||
    r === 'STRONG APPRECIATION PRESSURE' ||
    r === 'MODERATE APPRECIATION PRESSURE'
  ) {
    return 'down';
  }
  return 'flat';
}

export function isPredictive(direction: string | null | undefined): boolean {
  return direction === 'LONG' || direction === 'SHORT';
}
