"use client";

import { normalizeProp } from "@/components/ui/utils";
import { CONFIDENCE_ACCENT, PAIR_COMPOSITE_WEIGHTS } from "@/lib/config";
import { useMemo } from "react";
import { InspectorDrawer } from "./inspector-drawer";

/* ─── types ─────────────────────────────────────────────────────────── */

interface SignalInspectorProps {
  open: boolean;
  onClose: () => void;
  pairLabel: string;
  pairColor?: string;

  // Regime call data
  regime: string | null;
  confidence: number | null;
  signalComposite: number | null;
  rateSignal: string | null;
  cotSignal: string | null;
  volSignal: string | null;
  rrSignal: string | null;
  oiSignal: string | null;
  primaryDriver: string | null;

  // Raw signal data
  spot: number | null;
  rateDiff2y: number | null;
  rateDiff10y: number | null;
  rateZTactical: number | null;
  rateZStructural: number | null;
  realizedVol20d: number | null;
  realizedVol5d: number | null;
  impliedVol30d: number | null;
  dayChangePct: number | null;
  crossAssetUs10y: number | null;
  skewAlignment: number | null;
  breakevenInflation10y: number | null;
  zBlended?: number | null;
  ecbBalanceSheet?: number | null;
  bundBtpSpread?: number | null;
  bojPolicyRate?: number | null;
  indiaVix?: number | null;
  inrForwardPremium?: number | null;
  oiDelta?: number | null;
  volumeRvol?: number | null;
  structuralInstability?: boolean;
  specialSignalValue?: number | null;
  specialSignalLabel?: string | null;
}

/* ─── helpers ───────────────────────────────────────────────────────── */

function fmt2(n: number | null) {
  return n == null ? "—" : n.toFixed(2);
}

function fmt1(n: number | null) {
  return n == null ? "—" : n.toFixed(1);
}

function fmtPct(n: number | null) {
  if (n == null) return "—";
  const prop = normalizeProp(n) ?? 0;
  return `${(prop * 100).toFixed(1)}%`;
}

function signalBadgeClass(v: string | null): string {
  if (!v) return "text-[var(--terminal-fg-dim)]";
  const u = v.toUpperCase();
  if (u.includes("BULL")) return "text-[var(--terminal-success)]";
  if (u.includes("BEAR")) return "text-[var(--terminal-danger)]";
  if (u.includes("ELEV") || u.includes("HIGH"))
    return "text-[var(--terminal-warning)]";
  return "text-[var(--terminal-fg-muted)]";
}

function scoreToLabel(score: number | null): string {
  if (score == null) return "NEUTRAL";
  if (score > 0.4) return "STRONGLY BULLISH";
  if (score > 0.1) return "BULLISH";
  if (score < -0.4) return "STRONGLY BEARISH";
  if (score < -0.1) return "BEARISH";
  return "NEUTRAL";
}

function flipThreshold(
  confidence: number | null,
  composite: number | null,
): string {
  if (confidence == null || composite == null) return "—";
  // Threshold to flip regime: if confidence is high, need large composite swing
  const threshold =
    confidence > CONFIDENCE_ACCENT
      ? composite > 0
        ? "Composite < 0.10"
        : "Composite > -0.10"
      : composite > 0
        ? "Composite < -0.10"
        : "Composite > 0.10";
  return threshold;
}

/* ─── weighted composite bar ────────────────────────────────────────── */

function CompositeBar({
  pairColor,
  pairLabel,
}: {
  pairColor?: string;
  pairLabel: string;
}) {
  const c = pairColor || "var(--terminal-fg-muted)";
  const w =
    PAIR_COMPOSITE_WEIGHTS[pairLabel as keyof typeof PAIR_COMPOSITE_WEIGHTS];
  const arch = [
    { label: "RATE", weight: Math.round(w.rate * 100) },
    ...(pairLabel !== "USDINR"
      ? [{ label: "COT", weight: Math.round(w.cot * 100) }]
      : []),
    { label: "VOL", weight: Math.round(w.vol * 100) },
    { label: "OI", weight: Math.round(w.oi * 100) },
    ...(w.special > 0
      ? [{ label: "SPECIAL", weight: Math.round(w.special * 100) }]
      : []),
    ...(w.fpi > 0 ? [{ label: "FPI", weight: Math.round(w.fpi * 100) }] : []),
  ];
  return (
    <div className="space-y-2">
      <div className="flex h-[6px] w-full overflow-hidden">
        {arch.map((s) => (
          <div
            key={s.label}
            style={{
              width: `${s.weight}%`,
              background: `color-mix(in srgb, ${c} 80%, transparent)`,
            }}
            title={`${s.label} ~${s.weight}%`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {arch.map((s) => (
          <span
            key={s.label}
            className="font-mono text-[9px] text-[var(--terminal-fg-muted)]"
          >
            {s.label} {s.weight}%
          </span>
        ))}
      </div>
    </div>
  );
}

/* ─── row builder ───────────────────────────────────────────────────── */

function Row({
  label,
  value,
  sub,
  highlight = false,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[var(--terminal-border-subtle)]">
      <div>
        <p className="font-mono text-[9px] tracking-wider text-[var(--terminal-fg-dim)] uppercase">
          {label}
        </p>
        {sub && (
          <p className="font-mono text-[8px] text-[var(--terminal-fg-dim)]">
            {sub}
          </p>
        )}
      </div>
      <p
        className={`font-mono text-[11px] tabular-nums ${highlight ? "text-[var(--terminal-fg)] font-bold" : "text-[var(--terminal-fg-muted)]"}`}
      >
        {value}
      </p>
    </div>
  );
}

function SignalRow({
  label,
  signal,
  raw,
}: {
  label: string;
  signal: string | null;
  raw?: string;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[var(--terminal-border-subtle)]">
      <p className="font-mono text-[9px] tracking-wider text-[var(--terminal-fg-dim)] uppercase">
        {label}
      </p>
      <div className="text-right">
        <p
          className={`font-mono text-[11px] font-bold ${signalBadgeClass(signal)}`}
        >
          {signal || "—"}
        </p>
        {raw && (
          <p className="font-mono text-[9px] text-[var(--terminal-fg-dim)]">
            {raw}
          </p>
        )}
      </div>
    </div>
  );
}

/* ─── main component ────────────────────────────────────────────────── */

export function SignalInspector({
  open,
  onClose,
  pairLabel,
  pairColor,
  regime,
  confidence,
  signalComposite,
  rateSignal,
  cotSignal,
  volSignal,
  rrSignal,
  oiSignal,
  primaryDriver,
  spot,
  rateDiff2y,
  rateDiff10y,
  rateZTactical,
  rateZStructural,
  realizedVol20d,
  realizedVol5d,
  impliedVol30d,
  dayChangePct,
  crossAssetUs10y,
  skewAlignment,
  breakevenInflation10y,
  zBlended,
  ecbBalanceSheet,
  bundBtpSpread,
  bojPolicyRate,
  indiaVix,
  inrForwardPremium,
  oiDelta,
  volumeRvol,
  structuralInstability,
  specialSignalValue,
  specialSignalLabel,
}: SignalInspectorProps) {
  const compLabel = useMemo(
    () => scoreToLabel(signalComposite),
    [signalComposite],
  );
  const compPct = useMemo(() => {
    if (signalComposite == null) return null;
    return Math.min(100, Math.max(0, ((signalComposite + 2) / 4) * 100));
  }, [signalComposite]);

  const confPct = useMemo(() => {
    if (confidence == null) return null;
    const prop = normalizeProp(confidence) ?? 0;
    return Math.min(100, Math.max(0, Math.round(prop * 100)));
  }, [confidence]);

  return (
    <InspectorDrawer
      open={open}
      onClose={onClose}
      title={`${pairLabel} · Signal Inspector`}
    >
      <div className="space-y-6">
        {/* ── Regime Header ───────────────────────────────────── */}
        <div>
          <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase mb-1">
            Current Regime
          </p>
          <p className="font-mono text-[18px] font-bold text-[var(--terminal-fg)] leading-tight">
            {(regime || "—").replace(/_/g, " ")}
          </p>
          {primaryDriver && (
            <p className="font-mono text-[10px] text-[var(--terminal-fg-muted)] mt-1 truncate">
              {primaryDriver}
            </p>
          )}
        </div>

        {/* ── Confidence ──────────────────────────────────────── */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase">
              Confidence
            </p>
            <p className="font-mono text-[14px] font-bold text-[var(--terminal-fg)] tabular-nums">
              {confPct != null ? `${confPct}%` : "—"}
            </p>
          </div>
          <div className="h-[3px] w-full bg-[var(--terminal-border-subtle)]">
            <div
              className="h-full bg-[var(--terminal-fg)] transition-all duration-500"
              style={{ width: `${compPct ?? 50}%` }}
            />
          </div>
        </div>

        {/* ── Composite Score ─────────────────────────────────── */}
        <div className="border border-[var(--terminal-border-subtle)] bg-[var(--terminal-bg-sunken)] p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase">
              Weighted Composite
            </p>
            <p className="font-mono text-[14px] font-bold tabular-nums">
              <span
                className={
                  signalComposite != null && signalComposite > 0
                    ? "text-[var(--terminal-success)]"
                    : signalComposite != null && signalComposite < 0
                      ? "text-[var(--terminal-danger)]"
                      : "text-[var(--terminal-fg-muted)]"
                }
              >
                {signalComposite != null
                  ? `${signalComposite > 0 ? "+" : ""}${signalComposite.toFixed(2)}`
                  : "—"}
              </span>
              <span className="text-[10px] text-[var(--terminal-fg-dim)] ml-1">
                {compLabel}
              </span>
            </p>
          </div>
          <CompositeBar pairColor={pairColor} pairLabel={pairLabel} />
        </div>

        {/* ── Signal Breakdown ────────────────────────────────── */}
        <div>
          <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase mb-2">
            Signal Breakdown
          </p>
          <div className="border border-[var(--terminal-border-subtle)] bg-[var(--terminal-bg-sunken)]">
            <SignalRow label="Rate Signal" signal={rateSignal} />
            {pairLabel !== "USDINR" && (
              <SignalRow label="COT Signal" signal={cotSignal} />
            )}
            <SignalRow label="Volatility" signal={volSignal} />
            <SignalRow label="Risk Reversal" signal={rrSignal} />
            <SignalRow label="Open Interest" signal={oiSignal} />
          </div>
        </div>

        {/* ── Raw Inputs ──────────────────────────────────────── */}
        <div>
          <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase mb-2">
            Raw Inputs
          </p>
          <div className="border border-[var(--terminal-border-subtle)] bg-[var(--terminal-bg-sunken)]">
            <Row label="Spot" value={fmt2(spot)} highlight />
            <Row label="Rate Diff 2Y" value={fmt2(rateDiff2y)} sub="bps" />
            <Row label="Rate Diff 10Y" value={fmt2(rateDiff10y)} sub="bps" />
            <Row label="Rate Z (Tactical)" value={fmt2(rateZTactical)} />
            <Row label="Rate Z (Structural)" value={fmt2(rateZStructural)} />
            <Row
              label="Realized Vol 20D"
              value={fmt2(realizedVol20d)}
              sub="%"
            />
            <Row label="Realized Vol 5D" value={fmt2(realizedVol5d)} sub="%" />
            <Row label="Implied Vol 30D" value={fmt2(impliedVol30d)} sub="%" />
            <Row label="Day Change" value={fmtPct(dayChangePct)} />
            <Row label="Cross-Asset US10Y" value={fmt2(crossAssetUs10y)} />
            <Row label="Skew Alignment" value={fmt2(skewAlignment)} />
            <Row
              label="Breakeven Inflation 10Y"
              value={fmt2(breakevenInflation10y)}
              sub="%"
            />
            {zBlended != null && (
              <Row label="Rate Z (Blended)" value={fmt2(zBlended)} />
            )}
            {ecbBalanceSheet != null && (
              <Row label="ECB Balance Sheet" value={fmt2(ecbBalanceSheet)} />
            )}
            {bundBtpSpread != null && (
              <Row label="Bund-BTP Spread" value={fmt2(bundBtpSpread)} />
            )}
            {bojPolicyRate != null && (
              <Row label="BoJ Policy Rate" value={fmt2(bojPolicyRate)} />
            )}
            {indiaVix != null && (
              <Row label="India VIX" value={fmt2(indiaVix)} />
            )}
            {inrForwardPremium != null && (
              <Row
                label="INR Forward Premium"
                value={fmt2(inrForwardPremium)}
              />
            )}
            {oiDelta != null && <Row label="OI Delta" value={fmt2(oiDelta)} />}
            {volumeRvol != null && (
              <Row label="Volume RVOL" value={fmt2(volumeRvol)} />
            )}
            <Row
              label="Structural Instability"
              value={structuralInstability ? "YES" : "NO"}
            />
            {specialSignalValue != null && specialSignalLabel != null && (
              <Row
                label={specialSignalLabel}
                value={specialSignalValue.toFixed(2)}
              />
            )}
          </div>
        </div>

        {/* ── Flip Threshold ──────────────────────────────────── */}
        <div className="border border-[var(--terminal-warning)] bg-[var(--terminal-bg-sunken)] p-4">
          <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-warning)] uppercase mb-2">
            Regime Flip Threshold
          </p>
          <p className="font-mono text-[11px] text-[var(--terminal-fg)]">
            Current confidence: {confPct != null ? `${confPct}%` : "—"}
          </p>
          <p className="font-mono text-[10px] text-[var(--terminal-fg-muted)] mt-1">
            To flip regime: {flipThreshold(confidence, signalComposite)}
          </p>
        </div>
      </div>
    </InspectorDrawer>
  );
}
