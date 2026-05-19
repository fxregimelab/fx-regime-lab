// === PAIR COMPOSITE WEIGHTS (from pipeline/src/regime/composite.py) ===
export const PAIR_COMPOSITE_WEIGHTS = {
  EURUSD: {
    rate: 0.45,
    cot: 0.25,
    vol: 0.2,
    oi: 0.05,
    special: 0.05,
    fpi: 0.0,
  },
  USDJPY: { rate: 0.4, cot: 0.2, vol: 0.25, oi: 0.05, special: 0.1, fpi: 0.0 },
  USDINR: { rate: 0.3, cot: 0.1, vol: 0.2, oi: 0.05, special: 0.2, fpi: 0.15 },
} as const;

// === CROWDING THRESHOLDS (from pipeline/src/signals/cot.py) ===
export const CROWD_SOFT_HI = 90;
export const CROWD_SOFT_LO = 10;

// === CONFIDENCE CALIBRATION (from pipeline/src/regime/confidence.py) ===
export const PLATT_SCALE = 0.4;
export const PLATT_INTERCEPT = 0.35;

// === BIAS THRESHOLD ===
export const BIAS_THRESHOLD = 0.3;

// === ACCENT THRESHOLD (visual only) ===
export const CONFIDENCE_ACCENT = 0.55;

// === STALE THRESHOLD ===
export const STALE_THRESHOLD_DAYS = 10;

// === EUR/USD ACCURACY GATE ===
export const EURUSD_ACCURACY_GATE = 0.55;
export const DEFAULT_ACCURACY_GATE = 0.5;

// === SPOT DECIMALS ===
export function spotDecimals(pair: string): number {
  return pair === "USDJPY" ? 2 : 4;
}
