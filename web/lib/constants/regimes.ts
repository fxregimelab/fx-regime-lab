import type { RegimeLabel } from '@/lib/types/regime';

/** Short display title for each persisted `regime_calls.regime` value */
export const REGIME_LABELS: Record<RegimeLabel, string> = {
  UNKNOWN: 'Unknown',
  'STRONG USD STRENGTH': 'Strong USD strength',
  'MODERATE USD STRENGTH': 'Moderate USD strength',
  NEUTRAL: 'Neutral',
  'MODERATE USD WEAKNESS': 'Moderate USD weakness',
  'STRONG USD WEAKNESS': 'Strong USD weakness',
  VOL_EXPANDING: 'Vol expanding',
  'STRONG DEPRECIATION PRESSURE': 'Strong INR depreciation pressure',
  'MODERATE DEPRECIATION PRESSURE': 'Moderate INR depreciation pressure',
  'MODERATE APPRECIATION PRESSURE': 'Moderate INR appreciation pressure',
  'STRONG APPRECIATION PRESSURE': 'Strong INR appreciation pressure',
  DIRECTIONAL_ONLY: 'Directional only (INR)',
};

/** Tailwind utility class strings for regime chips */
export const REGIME_COLORS: Record<RegimeLabel, string> = {
  UNKNOWN: 'bg-neutral-600 text-white',
  'STRONG USD STRENGTH': 'bg-neutral-900 text-white',
  'MODERATE USD STRENGTH': 'bg-neutral-700 text-white',
  NEUTRAL: 'bg-neutral-500 text-white',
  'MODERATE USD WEAKNESS': 'bg-neutral-600 text-white',
  'STRONG USD WEAKNESS': 'bg-neutral-800 text-white',
  VOL_EXPANDING: 'bg-amber-600 text-neutral-950',
  'STRONG DEPRECIATION PRESSURE': 'bg-rose-800 text-white',
  'MODERATE DEPRECIATION PRESSURE': 'bg-rose-600 text-white',
  'MODERATE APPRECIATION PRESSURE': 'bg-emerald-700 text-white',
  'STRONG APPRECIATION PRESSURE': 'bg-emerald-900 text-white',
  DIRECTIONAL_ONLY: 'bg-neutral-700 text-amber-100',
};

export const REGIME_DESCRIPTIONS: Record<RegimeLabel, string> = {
  UNKNOWN: 'Composite or INR label missing for this row.',
  'STRONG USD STRENGTH': 'EUR or JPY composite strongly favors USD.',
  'MODERATE USD STRENGTH': 'Composite favors USD at moderate strength.',
  NEUTRAL: 'Composite near neutral band for G10 pairs.',
  'MODERATE USD WEAKNESS': 'Composite moderately favors USD selling pressure.',
  'STRONG USD WEAKNESS': 'Composite strongly favors USD weakness.',
  VOL_EXPANDING: 'Implied vol above 90th percentile; iv_gate applied and label forced.',
  'STRONG DEPRECIATION PRESSURE': 'INR composite strongly favors USD/INR higher.',
  'MODERATE DEPRECIATION PRESSURE': 'INR composite moderately favors USD/INR higher.',
  'MODERATE APPRECIATION PRESSURE': 'INR composite moderately favors USD/INR lower.',
  'STRONG APPRECIATION PRESSURE': 'INR composite strongly favors USD/INR lower.',
  DIRECTIONAL_ONLY: 'INR composite label missing; USDINR row is directional-only fallback.',
};

export const REGIME_LABELS_LIST = Object.keys(REGIME_LABELS) as RegimeLabel[];

export function isRegimeLabel(value: string): value is RegimeLabel {
  return (REGIME_LABELS_LIST as string[]).includes(value);
}
