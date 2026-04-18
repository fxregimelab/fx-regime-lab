// Regime badge for persisted `regime_calls.regime` strings
import type { RegimeLabel } from '@/lib/types/regime';
import { REGIME_COLORS, isRegimeLabel } from '@/lib/constants/regimes';

type Props = { regime: string };

export function Badge({ regime }: Props) {
  const cls = isRegimeLabel(regime) ? REGIME_COLORS[regime as RegimeLabel] : 'bg-neutral-700 text-neutral-100';
  return (
    <span className={`inline-flex rounded-pill px-2 py-0.5 font-mono text-[10px] font-semibold ${cls}`}>
      {regime}
    </span>
  );
}
