import { CROWD_SOFT_HI, CROWD_SOFT_LO } from "@/lib/config";
import { PAIRS } from "@/lib/constants";
import type { LatestRegimeCall, LatestSignal } from "@/lib/supabase/queries";

interface AlertStripProps {
  calls: Record<string, LatestRegimeCall>;
  signals: Record<string, LatestSignal>;
}

interface Alert {
  pair: string;
  display: string;
  message: string;
  severity: "red" | "amber" | "green";
}

export function AlertStrip({ calls, signals }: AlertStripProps) {
  const alerts: Alert[] = [];
  const trackedLabels = new Set<string>(PAIRS.map((p) => p.label));
  const displayMap = new Map<string, string>(
    PAIRS.map((p) => [p.label, p.display]),
  );

  for (const pair of Object.keys(signals)) {
    if (!trackedLabels.has(pair)) continue;
    const sig = signals[pair];
    const call = calls[pair];

    if (!sig) continue;

    // RVOL > 8
    if (sig.realized_vol_20d != null && sig.realized_vol_20d > 8) {
      alerts.push({
        pair,
        display: displayMap.get(pair) ?? pair,
        message: "RVOL ELEVATED",
        severity: "amber",
      });
    }

    // IV > RVOL
    if (
      sig.implied_vol_30d != null &&
      sig.realized_vol_20d != null &&
      sig.implied_vol_30d > sig.realized_vol_20d
    ) {
      alerts.push({
        pair,
        display: displayMap.get(pair) ?? pair,
        message: "IV PREMIUM",
        severity: "amber",
      });
    }

    // COT extreme (skip for USDINR — no liquid COT futures)
    if (
      pair !== "USDINR" &&
      sig.cot_percentile != null &&
      (sig.cot_percentile > CROWD_SOFT_HI || sig.cot_percentile < CROWD_SOFT_LO)
    ) {
      alerts.push({
        pair,
        display: displayMap.get(pair) ?? pair,
        message: "COT EXTREME",
        severity: "amber",
      });
    }

    // Rate divergence
    if (call?.rate_signal && call.rate_signal !== "NEUTRAL") {
      alerts.push({
        pair,
        display: displayMap.get(pair) ?? pair,
        message: "RATE DIVERGENCE",
        severity: "green",
      });
    }

    // Red stress
    if (call?.stress_level === "RED") {
      alerts.push({
        pair,
        display: displayMap.get(pair) ?? pair,
        message: "RED STRESS — SIGNALS WITHHELD",
        severity: "red",
      });
    }

    // DQS degraded
    if (call?.data_quality_score != null && call.data_quality_score < 0.75) {
      alerts.push({
        pair,
        display: displayMap.get(pair) ?? pair,
        message: "DQS DEGRADED",
        severity: "amber",
      });
    }
  }

  // Deduplicate by message+pair
  const seen = new Set<string>();
  const unique = alerts.filter((a) => {
    const key = `${a.pair}:${a.message}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  if (unique.length === 0) {
    return (
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-3 mb-6">
        <span className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider">
          SYSTEM NOMINAL
        </span>
      </div>
    );
  }

  const severityBorder: Record<string, string> = {
    red: "border-[var(--color-down)] text-[var(--color-down)]",
    amber: "border-[var(--color-warn)] text-[var(--color-warn)]",
    green: "border-[var(--color-up)] text-[var(--color-up)]",
  };

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {unique.map((a) => (
        <span
          key={`${a.pair}:${a.message}`}
          className={`font-mono text-[9px] tracking-[0.1em] border px-2 py-1 ${severityBorder[a.severity]}`}
        >
          {a.display} — {a.message}
        </span>
      ))}
    </div>
  );
}
