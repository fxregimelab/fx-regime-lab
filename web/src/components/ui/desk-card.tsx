"use client";

import { BinaryResolve } from "@/components/ui/BinaryResolve";
import { GhostResolve } from "@/components/ui/GhostResolve";
import { DataLineage } from "@/components/ui/data-lineage";
import { ReproducibilityExport } from "@/components/ui/reproducibility-export";
import {
  crowdingUnavailableMessage,
  formatAlignment,
  formatSignedInteger,
  formatSignedPercent,
  readCrowdingDiagnostic,
} from "@/lib/crowding-diagnostic";
import type { DominanceItem, MarkovPayload } from "@/lib/queries";
import type { TelemetryAuditPayload } from "@/lib/queries";
import { formatRegimeShareNote } from "@/lib/regime-share";
import { AnimatePresence, motion } from "framer-motion";
import React from "react";
import { fmt2, normalizeProp } from "./utils";

const OMEGA_BEVEL =
  "border-0 border-t-[0.5px] border-t-[color-mix(in_srgb,var(--color-border)_8%,transparent)] border-l-[0.5px] border-l-[color-mix(in_srgb,var(--color-border)_3%,transparent)] bg-[var(--color-sunken)]";
const OMEGA_BEVEL_CRISIS =
  "border-0 border-t-[0.5px] border-t-[var(--color-warn)] border-l-[0.5px] border-l-[color-mix(in_srgb,var(--color-border)_3%,transparent)] bg-[var(--color-sunken)]";
const OMEGA_DIVIDER_Y =
  "border-b-[0.5px] border-b-[var(--color-border-subtle)]";

const PARTICIPANT_RISK_UNAVAILABLE =
  "Participant losses and squeeze probability unavailable";

/** Desk `ai_brief` JSON with unsupported risk assertions removed. */
export function parseDeskAiBriefRows(
  raw: string | null,
): { label: string; value: string }[] {
  if (!raw?.trim()) return [];
  const t = raw.trim();
  try {
    const parsed = JSON.parse(t) as unknown;
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      Array.isArray(parsed)
    ) {
      return [{ label: "DIAGNOSTICS", value: PARTICIPANT_RISK_UNAVAILABLE }];
    }
    const j = parsed as Record<string, unknown>;
    const rows: { label: string; value: string }[] = [];
    for (const [key, label] of [
      ["bias_summary", "BIAS"],
      ["regime_state", "BIAS"],
      ["catalyst_driver", "CATALYST"],
      ["key_divergence", "CATALYST"],
    ] as const) {
      if (rows.some((row) => row.label === label)) continue;
      const value = j[key];
      if (typeof value === "string" && value.trim()) {
        rows.push({ label, value: value.trim() });
      }
    }
    rows.push({ label: "DIAGNOSTICS", value: PARTICIPANT_RISK_UNAVAILABLE });
    return rows;
  } catch {
    return [{ label: "DIAGNOSTICS", value: PARTICIPANT_RISK_UNAVAILABLE }];
  }
}

function ModelInstabilityBadge({ className }: { className?: string }) {
  return (
    <span
      className={`font-mono text-[9px] uppercase tracking-widest text-[var(--color-warn)] border-[0.5px] border-[var(--color-warn)] bg-transparent px-1.5 py-0.5 whitespace-nowrap ${className ?? ""}`}
      aria-label="Model instability"
    >
      [ MODEL INSTABILITY ]
    </span>
  );
}

export type DeskCardTelemetryRowProps = {
  pairLabel: string;
  spot: number | null | undefined;
  structuralRegime: string;
  confidence: number | null | undefined;
  /** 0–100 apex display (from stored 0–1 apex_score). */
  apexScoreDisplay?: number | null;
  telemetryAudit?: TelemetryAuditPayload | null;
  /** Normalized from snapshot; overrides parsing ``telemetryAudit`` when set. */
  parameterInstability?: boolean;
  /** Skip flicker if the terminal is in a dimmed background state. */
  paused?: boolean;
};

/** Compact row: pair, price, regime, confidence only (no brief / math). */
export function DeskCardTelemetryRow({
  pairLabel,
  spot,
  structuralRegime,
  confidence,
  telemetryAudit,
  parameterInstability,
  paused = false,
}: DeskCardTelemetryRowProps) {
  const pct =
    confidence != null
      ? Math.min(
          100,
          Math.max(0, Math.round((normalizeProp(confidence) ?? 0) * 100)),
        )
      : null;
  const modelUnstable =
    parameterInstability ?? Boolean(telemetryAudit?.parameter_instability);
  return (
    <div
      className={`relative ${OMEGA_BEVEL} px-2 py-2 grid grid-cols-[auto_minmax(0,1fr)_auto] gap-x-3 gap-y-1 items-baseline text-[var(--color-text)]`}
    >
      <span className="font-mono text-[11px] tracking-wide shrink-0">
        {pairLabel}
      </span>
      <span className="font-mono text-[11px] text-[var(--color-text)] tabular-nums min-w-0 text-right">
        <BinaryResolve
          value={spot != null ? fmt2(spot) : "—"}
          resolveKey={spot ?? 0}
          paused={paused}
        />
      </span>
      <DataLineage
        lineage={{
          source: "FX Regime Lab model v3",
          transformation: "Signal dispersion → confidence score (0–1)",
        }}
      >
        <span className="font-mono text-[10px] text-[var(--color-text)] tabular-nums shrink-0">
          {pct != null ? `${pct}%` : "—"}
        </span>
      </DataLineage>
      <div className="relative col-span-3 min-w-0 pr-[168px]">
        <DataLineage
          lineage={{
            source: "FX Regime Lab model v3",
            transformation: "Weighted composite → regime classifier",
          }}
        >
          <span className="font-mono text-[10px] text-[var(--color-text-secondary)] block truncate leading-snug">
            {structuralRegime.replace(/_/g, " ")}
          </span>
        </DataLineage>
        {modelUnstable ? (
          <ModelInstabilityBadge className="absolute top-0 right-0 z-10" />
        ) : null}
      </div>
    </div>
  );
}

type DeskCardProps = {
  variant?: "default" | "hero";
  pairDisplay?: string;
  spot?: number | null;
  confidence?: number | null;
  rankJump?: number;
  regimeAge?: number | null;
  /** 0–100 apex display (Rank #1 hero). */
  apexScoreDisplay?: number | null;
  structuralRegime: string;
  invalidationTriggered: boolean;
  telemetryStatus: string;
  dominanceArray: DominanceItem[];
  painIndex: number | null;
  markovProbabilities: MarkovPayload | null;
  aiBrief: string | null;
  telemetryAudit: TelemetryAuditPayload | null;
  /** Normalized from snapshot; falls back to ``telemetry_audit.parameter_instability``. */
  parameterInstability?: boolean;
  /** [∫] inspector — falls back to ``telemetry_audit`` MAD fields when null. */
  mathRateZTactical?: number | null;
  mathRateZStructural?: number | null;
  mathDynamicBeta?: number | null;
  /** If true, pauses BinaryResolve flicker. */
  pausedBinaryResolve?: boolean;
  /** Optional systemic whisper — materializes via GhostResolve on hero or hover. */
  whisper?: string | null;
  /** Correlation handshake line — shown on hover when set (e.g. `[ CORR_LOCKED: USDJPY ]`). */
  corrLockedWhisper?: string | null;
};

export function DeskCard({
  variant = "default",
  pairDisplay,
  spot,
  confidence,
  regimeAge,
  structuralRegime,
  invalidationTriggered,
  telemetryStatus,
  dominanceArray,
  markovProbabilities,
  aiBrief,
  telemetryAudit,
  parameterInstability,
  mathRateZTactical,
  mathRateZStructural,
  mathDynamicBeta,
  pausedBinaryResolve = false,
  whisper = null,
  corrLockedWhisper = null,
}: DeskCardProps) {
  type LiPhase = "idle" | "copying" | "success";
  const [liPhase, setLiPhase] = React.useState<LiPhase>("idle");
  const [liErr, setLiErr] = React.useState<string | null>(null);
  const [mathOpen, setMathOpen] = React.useState(false);
  const [cardHover, setCardHover] = React.useState(false);
  const liSuccessTimer = React.useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  React.useEffect(() => {
    return () => {
      if (liSuccessTimer.current) clearTimeout(liSuccessTimer.current);
    };
  }, []);

  const modelUnstable =
    parameterInstability ?? Boolean(telemetryAudit?.parameter_instability);
  const isOffline = telemetryStatus === "OFFLINE";
  const isCrisis = invalidationTriggered && !isOffline;
  const surfaceBevel = isCrisis ? OMEGA_BEVEL_CRISIS : OMEGA_BEVEL;
  const muted = isOffline
    ? "text-[var(--color-text-dim)]"
    : "text-[var(--color-text)]";
  const top = dominanceArray[0];
  const rest = dominanceArray.slice(1);
  const markovN = markovProbabilities?.weighted_sample_size ?? 0;
  const markovLowSample = markovN < 20;
  const isHero = variant === "hero";
  const whisperActive = Boolean(whisper && (isHero || cardHover));
  const corrActive =
    Boolean(corrLockedWhisper) && cardHover && !pausedBinaryResolve;
  const showGhostStrip =
    (whisper != null && whisper !== "") ||
    (corrLockedWhisper != null && corrLockedWhisper !== "");
  const confPct =
    confidence != null
      ? Math.min(
          100,
          Math.max(0, Math.round((normalizeProp(confidence) ?? 0) * 100)),
        )
      : null;
  const aiRows = parseDeskAiBriefRows(aiBrief);
  const crowding = readCrowdingDiagnostic(
    telemetryAudit?.crowding_diagnostic,
    pairDisplay,
  );

  const zT =
    mathRateZTactical ??
    (telemetryAudit?.rate_z_tactical_mad != null
      ? telemetryAudit.rate_z_tactical_mad
      : null);
  const zS =
    mathRateZStructural ??
    (telemetryAudit?.rate_z_structural_mad != null
      ? telemetryAudit.rate_z_structural_mad
      : null);
  const dynBeta =
    mathDynamicBeta ??
    (telemetryAudit?.dynamic_beta != null
      ? telemetryAudit.dynamic_beta
      : top?.beta != null
        ? top.beta
        : null);

  const fmtM = (n: number | null | undefined) =>
    n == null || Number.isNaN(n) ? "—" : n.toFixed(4);

  return (
    <section
      className={`relative ${surfaceBevel} ${muted} omega-haptic`}
      onMouseEnter={() => setCardHover(true)}
      onMouseLeave={() => setCardHover(false)}
    >
      <div
        className={`${OMEGA_DIVIDER_Y} px-4 py-3 flex items-center justify-between gap-2`}
      >
        <p className="font-mono text-[10px] tracking-widest">
          {isHero
            ? `[ FX DESK · ${pairDisplay ?? "—"} ]`
            : "[ DESK OPEN CARD ]"}
          {regimeAge != null && regimeAge >= 0 ? (
            <span className="text-[var(--color-text-dim)] tabular-nums">
              {" "}
              [ AGE: {regimeAge}D ]
            </span>
          ) : null}
        </p>
        <ReproducibilityExport
          payload={{
            query: "DeskCard snapshot",
            parameters: {
              pair: pairDisplay ?? "—",
              regime: structuralRegime,
              confidence: confidence ?? null,
            },
            timestamp: new Date().toISOString(),
            sourceTable: "regime_calls, signals",
          }}
          variant="icon"
        />
        <button
          type="button"
          onClick={() => setMathOpen((o) => !o)}
          aria-expanded={mathOpen}
          className="shrink-0 rounded-none border-0 border-t-[0.5px] border-t-[color-mix(in_srgb,var(--color-border)_8%,transparent)] border-l-[0.5px] border-l-[color-mix(in_srgb,var(--color-border)_3%,transparent)] bg-[var(--color-void)] px-2 py-1 font-mono text-[11px] text-[var(--color-text)] shadow-none hover:text-[var(--color-text)] omega-haptic"
          aria-label="Toggle math inspector"
        >
          [ ∫ ]
        </button>
      </div>
      {isOffline ? (
        <div className="border-b-[0.5px] border-b-[var(--color-border)] px-4 py-2 font-mono text-[11px] tracking-widest text-[var(--color-text-muted)]">
          [ TELEMETRY OFFLINE ]
        </div>
      ) : null}
      {isCrisis ? (
        <div className="border-b-[0.5px] border-b-[var(--color-warn)] px-4 py-2 font-mono text-[11px] tracking-widest text-[var(--color-warn)]">
          [ OVERNIGHT INVALIDATION TRIGGERED ]
        </div>
      ) : null}

      <AnimatePresence initial={false}>
        {mathOpen ? (
          <motion.div
            key="math-inspector"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.25, 0.1, 0.25, 1] }}
            className={`overflow-hidden ${OMEGA_DIVIDER_Y} bg-[var(--color-sunken)] shadow-none`}
          >
            <div className="grid grid-cols-2 gap-x-3 gap-y-2 px-4 py-3 md:grid-cols-3">
              <div className="min-w-0">
                <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)]">
                  RATE Z (T)
                </p>
                <p className="font-mono text-[10px] tabular-nums text-[var(--color-text)]">
                  <BinaryResolve
                    value={fmtM(zT)}
                    resolveKey={zT ?? 0}
                    paused={pausedBinaryResolve}
                  />
                </p>
              </div>
              <div className="min-w-0">
                <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)]">
                  RATE Z (S)
                </p>
                <p className="font-mono text-[10px] tabular-nums text-[var(--color-text)]">
                  <BinaryResolve
                    value={fmtM(zS)}
                    resolveKey={zS ?? 0}
                    paused={pausedBinaryResolve}
                  />
                </p>
              </div>
              <div className="min-w-0">
                <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)]">
                  DYN BETA
                </p>
                <p className="font-mono text-[10px] tabular-nums text-[var(--color-text)]">
                  <BinaryResolve
                    value={fmtM(dynBeta)}
                    resolveKey={dynBeta ?? 0}
                    paused={pausedBinaryResolve}
                  />
                </p>
              </div>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      {isHero && !isOffline ? (
        <div
          className={`${OMEGA_DIVIDER_Y} px-4 py-4 flex flex-wrap items-end justify-between gap-3`}
        >
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            {confPct != null ? (
              <DataLineage
                lineage={{
                  source: "FX Regime Lab model v3",
                  transformation: "Signal dispersion → confidence score (0–1)",
                }}
              >
                <span className="font-mono text-[10px] tabular-nums text-[var(--color-text)] tracking-widest">
                  CONF {confPct}%
                </span>
              </DataLineage>
            ) : null}
          </div>
          <p
            className={`font-mono font-extrabold tabular-nums tracking-tight shrink-0 ${
              isCrisis
                ? "line-through text-[var(--color-text)] text-[22px]"
                : "text-[var(--color-text)] text-[30px] leading-none"
            }`}
          >
            <BinaryResolve
              value={spot != null ? fmt2(spot) : "—"}
              resolveKey={spot ?? 0}
              paused={pausedBinaryResolve}
            />
          </p>
        </div>
      ) : null}

      <div className="px-4 py-4">
        <div className="relative pr-[168px] min-h-[14px]">
          <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-widest uppercase">
            STRUCTURAL REGIME
          </p>
          {modelUnstable ? (
            <ModelInstabilityBadge className="absolute top-0 right-0 z-10" />
          ) : null}
        </div>
        <p
          className={`mt-1 font-mono font-extrabold ${
            isHero ? "text-[28px] leading-tight" : "text-[20px]"
          } ${isCrisis ? "line-through text-[var(--color-text)]" : "text-[var(--color-text)]"}`}
        >
          <DataLineage
            lineage={{
              source: "FX Regime Lab model v3",
              transformation: "Weighted composite → regime classifier",
            }}
          >
            <span className="inline-block">
              {structuralRegime.replace(/_/g, " ")}
            </span>
          </DataLineage>
        </p>
      </div>

      <div className="border-t-[0.5px] border-t-[var(--color-border-subtle)] grid grid-cols-1 md:grid-cols-2">
        <div className="border-r-[0.5px] border-r-[var(--color-border-subtle)] p-4">
          <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] mb-2">
            DOMINANCE ARRAY
          </p>
          {top ? (
            <div className="border-0 border-t-[0.5px] border-t-[color-mix(in_srgb,var(--color-border)_6%,transparent)] bg-[var(--color-void)] p-3 mb-2">
              <p className="font-mono text-[9px] text-[var(--color-text-secondary)]">
                RANK #1
              </p>
              <p className="font-mono text-[13px] text-[var(--color-text-muted)] mt-1 tabular-nums">
                {top.signal_family.toUpperCase()} (
                {top.dominance_score.toFixed(3)})
              </p>
            </div>
          ) : null}
          <div className="space-y-2">
            {rest.map((row) => (
              <div
                key={`${row.rank}-${row.signal_family}`}
                className="border-0 border-t-[0.5px] border-t-[color-mix(in_srgb,var(--color-border)_4%,transparent)] bg-[var(--color-void)] p-2"
              >
                <p className="font-mono text-[10px] text-[var(--color-text-secondary)]">
                  #{row.rank} {row.signal_family.toUpperCase()}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className={`p-4 ${markovLowSample ? "opacity-50" : ""}`}>
          <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] mb-2">
            MARKOV PROBABILITIES
          </p>
          {markovLowSample ? (
            <p className="font-mono text-[10px] tracking-widest text-[var(--color-warn)] mb-2">
              {"[ LOW CONFIDENCE SAMPLE (N < 20) ]"}
            </p>
          ) : null}
          <p className="font-mono text-[11px] text-[var(--color-text-secondary)] tabular-nums">
            CONTINUATION:{" "}
            {markovProbabilities?.continuation_probability != null
              ? `${markovProbabilities.continuation_probability.toFixed(2)}%`
              : "N/A"}
          </p>
          <div className="mt-2 space-y-1">
            {Object.entries(markovProbabilities?.transitions ?? {}).map(
              ([regime, value]) => (
                <p
                  key={regime}
                  className="font-mono text-[10px] text-[var(--color-text-muted)] tabular-nums"
                >
                  {regime}: {value.toFixed(2)}%
                </p>
              ),
            )}
          </div>
        </div>
      </div>

      <div className="border-t-[0.5px] border-t-[var(--color-border-subtle)] px-4 py-3">
        <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] mb-2">
          DIAGNOSTICS
        </p>
        {crowding.kind === "valid" ? (
          <div className="space-y-1 font-mono text-[10px] text-[var(--color-text-muted)]">
            <p>
              {crowding.diagnostic.cot.status === "PROVISIONAL" &&
              crowding.diagnostic.cot.net_long !== null
                ? `Reported net (provisional): ${formatSignedInteger(crowding.diagnostic.cot.net_long)} contracts · ${formatAlignment(crowding.diagnostic.cot.alignment)}.`
                : "Reported net: unavailable."}
            </p>
            {crowding.diagnostic.cot.report_date ? (
              <p>
                Report date: {crowding.diagnostic.cot.report_date} · category
                definition unknown.
              </p>
            ) : null}
            <p>Source availability: unverified.</p>
            {crowding.diagnostic.price.status === "PROVISIONAL" &&
            crowding.diagnostic.price.spot !== null &&
            crowding.diagnostic.price.latest_date ? (
              <p>
                Latest supplied close:{" "}
                {crowding.diagnostic.price.spot.toLocaleString("en-US", {
                  maximumFractionDigits: 6,
                })}{" "}
                · date: {crowding.diagnostic.price.latest_date} · observations:{" "}
                {crowding.diagnostic.price.observation_count}.
              </p>
            ) : null}
            <p>
              {crowding.diagnostic.price.relative_to_mean_pct !== null &&
              crowding.diagnostic.price.latest_date
                ? `Close vs 40-observation mean: ${formatSignedPercent(crowding.diagnostic.price.relative_to_mean_pct)} · latest close date: ${crowding.diagnostic.price.latest_date}.`
                : "Close vs 40-observation mean: unavailable."}
            </p>
            <p>{PARTICIPANT_RISK_UNAVAILABLE}.</p>
          </div>
        ) : (
          <p className="font-mono text-[10px] text-[var(--color-text-muted)]">
            {crowdingUnavailableMessage(crowding.kind)}{" "}
            {PARTICIPANT_RISK_UNAVAILABLE}.
          </p>
        )}
      </div>

      {!isCrisis && !isOffline ? (
        <div className="border-t-[0.5px] border-t-[var(--color-border-subtle)] px-4 py-3">
          <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] mb-2">
            AI BRIEF
          </p>
          {aiRows.length === 0 ? (
            <p className="font-mono text-[11px] text-[var(--color-text-muted)] m-0">
              No desk brief available.
            </p>
          ) : (
            <div className="grid gap-2.5 font-mono text-[11px] leading-snug">
              {aiRows.map(({ label, value }) => (
                <div
                  key={label}
                  className="grid grid-cols-[minmax(0,92px)_minmax(0,1fr)] gap-x-3 items-baseline"
                >
                  <span className="text-[var(--color-text-muted)] tracking-widest shrink-0">
                    [ {label} ]
                  </span>
                  <span className="text-[var(--color-text)] min-w-0 break-words">
                    {value}
                  </span>
                </div>
              ))}
            </div>
          )}
          {pairDisplay ? (
            <div className="mt-3">
              <button
                type="button"
                disabled={liPhase === "copying"}
                onClick={async () => {
                  setLiErr(null);
                  if (liSuccessTimer.current) {
                    clearTimeout(liSuccessTimer.current);
                    liSuccessTimer.current = null;
                  }
                  setLiPhase("copying");
                  try {
                    const pair = pairDisplay
                      .toUpperCase()
                      .replace(/[\s/]/gu, "");
                    const text = formatRegimeShareNote({
                      pair,
                      regime: structuralRegime,
                      url: `https://fxregimelab.com/terminal/fx-regime/${pair.toLowerCase()}`,
                      spot: spot ?? null,
                      confidencePercent: confPct,
                      dominantSignal: top?.signal_family ?? null,
                      dominantScore: top?.dominance_score ?? null,
                    });
                    await navigator.clipboard.writeText(text);
                    setLiPhase("success");
                    liSuccessTimer.current = setTimeout(() => {
                      setLiPhase("idle");
                      liSuccessTimer.current = null;
                    }, 2000);
                  } catch (e) {
                    setLiPhase("idle");
                    setLiErr(e instanceof Error ? e.message : "Copy failed");
                  }
                }}
                className={`border-0 border-t-[0.5px] border-t-[color-mix(in_srgb,var(--color-border)_10%,transparent)] border-l-[0.5px] border-l-[color-mix(in_srgb,var(--color-border)_4%,transparent)] bg-[var(--color-void)] px-2 py-1.5 font-mono text-[9px] tracking-widest cursor-pointer transition-opacity disabled:cursor-not-allowed active:opacity-90 omega-haptic ${
                  liPhase === "success"
                    ? "border-t-[var(--color-up)]/50 text-[var(--color-up)]"
                    : "text-[var(--color-text)] hover:border-t-[color-mix(in_srgb,var(--color-border)_20%,transparent)] hover:text-[var(--color-text)]"
                } ${liPhase === "copying" ? "animate-pulse opacity-70" : ""}`}
              >
                {liPhase === "copying"
                  ? "[ COPYING... ]"
                  : liPhase === "success"
                    ? "[ COPIED! ✓ ]"
                    : "[ SHARE REGIME NOTE ]"}
              </button>
              {liErr ? (
                <p className="mt-2 font-mono text-[9px] text-[var(--color-down)] m-0">
                  {liErr}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {showGhostStrip ? (
        <div className="border-t-[0.5px] border-t-[var(--color-border-subtle)] px-4 py-2.5 min-h-[48px] flex flex-col justify-center gap-1">
          <p className="m-0 mb-0 font-mono text-[8px] tracking-widest text-[var(--color-text-dim)]">
            GHOST WHISPER
          </p>
          {whisper ? (
            whisperActive ? (
              <GhostResolve
                value={whisper}
                resolveKey={whisper ?? ""}
                active
                paused={pausedBinaryResolve}
              />
            ) : (
              <p className="m-0 font-mono text-[9px] tracking-widest text-[var(--color-text-dim)]">
                [ HOVER_FOR_SIGNAL ]
              </p>
            )
          ) : null}
          {corrActive && corrLockedWhisper ? (
            <GhostResolve
              value={corrLockedWhisper}
              resolveKey={corrLockedWhisper ?? ""}
              active
              paused={pausedBinaryResolve}
            />
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
