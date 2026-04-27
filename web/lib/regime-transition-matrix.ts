/** Five coarse buckets used in the performance transition matrix (shell-aligned). */
export const TRANSITION_BUCKET_LABELS = [
  'STRONG USD STRENGTH',
  'MODERATE USD STRENGTH',
  'NEUTRAL',
  'MODERATE USD WEAKNESS',
  'VOL_EXPANDING',
] as const;

export const TRANSITION_COL_SHORT = ['STRONG STR', 'MOD STR', 'NEUTRAL', 'MOD WEAK', 'VOL EXP'] as const;

const N = 5;

function bucketIndex(regime: string): number | null {
  const r = regime.trim().toUpperCase();
  if (!r) return null;
  if (r.includes('VOL') || r.includes('EXPANDING') || r.includes('VOL_')) return 4;
  if (r.includes('STRONG') && r.includes('STRENGTH')) return 0;
  if (r.includes('MODERATE') && r.includes('STRENGTH')) return 1;
  if (r.includes('WEAKNESS')) return 3;
  if (r.includes('NEUTRAL')) return 2;
  if (r.includes('PRESSURE') || r.includes('DEPRECIATION') || r.includes('APPRECIATION')) return 2;
  return 2;
}

type Row = { date: string; pair: string; regime: string };

/** Build transition % matrix from consecutive same-pair regime rows. */
export function buildRegimeTransitionMatrix(rows: Row[]): (string | null)[][] {
  const counts: number[][] = Array.from({ length: N }, () => Array(N).fill(0));
  const byPair = new Map<string, Row[]>();
  for (const row of rows) {
    const list = byPair.get(row.pair) ?? [];
    list.push(row);
    byPair.set(row.pair, list);
  }
  for (const list of byPair.values()) {
    list.sort((a, b) => a.date.localeCompare(b.date));
    for (let i = 0; i < list.length - 1; i++) {
      const from = bucketIndex(list[i].regime);
      const to = bucketIndex(list[i + 1].regime);
      if (from == null || to == null) continue;
      counts[from][to] += 1;
    }
  }
  const matrix: (string | null)[][] = [];
  for (let i = 0; i < N; i++) {
    const rowOut: (string | null)[] = [];
    const rowSum = counts[i].reduce((s, v) => s + v, 0);
    for (let j = 0; j < N; j++) {
      if (i === j) {
        rowOut.push(null);
        continue;
      }
      if (!rowSum) {
        rowOut.push('—');
        continue;
      }
      const pct = Math.round((counts[i][j] / rowSum) * 100);
      rowOut.push(`${pct}%`);
    }
    matrix.push(rowOut);
  }
  return matrix;
}
