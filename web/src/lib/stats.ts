/** Statistical utilities for FX Regime Lab.
 *  Wilson score interval for binomial proportions,
 *  normal-approximation CI for means.
 */

const Z_95 = 1.959963984540054; // exact z for 95% two-sided

/** Wilson score interval for a binomial proportion.
 *  More accurate than normal approximation, especially near 0/1.
 */
export function wilsonCI(
  successes: number,
  trials: number,
  confidence = 0.95,
): [number, number] {
  if (trials === 0 || !Number.isFinite(successes) || !Number.isFinite(trials)) {
    return [0, 0];
  }
  const p = Math.max(0, Math.min(1, successes / trials));
  const z = confidence === 0.95 ? Z_95 : 1.96;
  const denom = 1 + (z * z) / trials;
  const centre = (p + (z * z) / (2 * trials)) / denom;
  const halfWidth =
    (z * Math.sqrt((p * (1 - p)) / trials + (z * z) / (4 * trials * trials))) /
    denom;
  return [Math.max(0, centre - halfWidth), Math.min(1, centre + halfWidth)];
}

/** Normal-approximation confidence interval for a sample mean.
 *  Uses sample standard deviation with Bessel's correction.
 */
export function meanCI(values: number[], confidence = 0.95): [number, number] {
  const n = values.length;
  if (n === 0) return [0, 0];
  const mean = values.reduce((a, b) => a + b, 0) / n;
  if (n === 1) return [mean, mean];
  const variance =
    values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / (n - 1);
  const se = Math.sqrt(variance / n);
  const z = confidence === 0.95 ? Z_95 : 1.96;
  return [Math.max(0, mean - z * se), mean + z * se];
}

/** Format a proportion CI as "XX.X% [XX.X%–XX.X%]". */
export function fmtPropCI(
  point: number | null,
  ci: [number, number],
  digits = 1,
): string {
  const p = point != null ? (point * 100).toFixed(digits) : "—";
  const lo = (ci[0] * 100).toFixed(digits);
  const hi = (ci[1] * 100).toFixed(digits);
  return `${p}% [${lo}%–${hi}%]`;
}

/** Format a mean CI as "X.XXX [X.XXX–X.XXX]". */
export function fmtMeanCI(
  point: number | null,
  ci: [number, number],
  digits = 3,
): string {
  const p = point != null ? point.toFixed(digits) : "—";
  const lo = ci[0].toFixed(digits);
  const hi = ci[1].toFixed(digits);
  return `${p} [${lo}–${hi}]`;
}
