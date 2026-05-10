"use client";

import { BinaryResolve } from "@/components/ui/BinaryResolve";
import { GhostResolve } from "@/components/ui/GhostResolve";
import { TerminalLabel } from "@/components/ui/TerminalLabel";
import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { CorrelationMatrix } from "@/components/ui/correlation-matrix";
import { DeskCard } from "@/components/ui/desk-card";
import { MacroDriftEngine } from "@/components/ui/macro-drift-engine";
import { fmt2, fmtPct } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import { G10_MATRIX_ORDER, topCorrelatedPeer } from "@/lib/g10Correlation";
import {
  type DeskOpenCardSnapshotRow,
  type DeskOpenCardsSnapshot,
  useG10CorrelationMatrix,
  useLatestDeskOpenCardsSnapshot,
  useLatestRegimeCalls,
  useLatestSignals,
} from "@/lib/queries";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type ReactNode, useMemo, useState } from "react";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};
const item = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2, ease: "easeOut" as const },
  },
};

function pairMeta(label: string) {
  return PAIRS.find((p) => p.label === label) ?? PAIRS[0];
}

function cardAtRank(
  cards: DeskOpenCardSnapshotRow[],
  rank: number,
): DeskOpenCardSnapshotRow | undefined {
  return cards.find((c) => c.global_rank === rank);
}

type MosaicTier = "apex" | "bench" | "outlier";

const G10_SET = new Set<string>(G10_MATRIX_ORDER);

function MosaicCell({
  tier,
  card,
  calls,
  sigs,
  onOpen,
  isDimmed,
  onHover,
  corrGlow,
  corrLockedWhisper,
  pausedBinaryResolve,
}: {
  tier: MosaicTier;
  card: DeskOpenCardSnapshotRow | undefined;
  calls: ReturnType<typeof useLatestRegimeCalls>["data"];
  sigs: ReturnType<typeof useLatestSignals>["data"];
  onOpen: (slug: string) => void;
  isDimmed: boolean;
  onHover: (hover: boolean) => void;
  corrGlow?: boolean;
  corrLockedWhisper?: string | null;
  pausedBinaryResolve?: boolean;
}) {
  const lum =
    tier === "apex"
      ? {
          title: "text-[var(--color-text)]",
          spot: "text-[var(--color-text)]",
          regime: "text-[var(--color-text-secondary)]",
          meta: "text-[var(--color-text-muted)]",
        }
      : tier === "bench"
        ? {
            title: "text-[var(--color-text-secondary)]",
            spot: "text-[var(--color-text-secondary)]",
            regime: "text-[var(--color-text-secondary)]",
            meta: "text-[var(--color-text-dim)]",
          }
        : {
            title: "text-[var(--color-text-muted)]",
            spot: "text-[var(--color-text-muted)]",
            regime: "text-[var(--color-text-muted)]",
            meta: "text-[var(--color-text-dim)]",
          };

  if (!card) {
    return (
      <div
        className={`relative flex min-h-[120px] flex-1 flex-col justify-center border-0 border-t-[0.5px] border-t-white/[0.06] border-l-[0.5px] border-l-white/[0.03] px-3 py-3 transition-colors duration-200 ${
          corrGlow ? "bg-[var(--color-up)]/[0.06]" : "bg-[var(--color-void)]"
        }`}
      />
    );
  }

  const p = pairMeta(card.pair);
  const call = calls?.[card.pair];
  const sig = sigs?.[card.pair];
  const chg = sig?.day_change_pct as number | undefined;
  const spotNum = sig?.spot != null ? Number(sig.spot) : null;

  return (
    <motion.button
      variants={item}
      type="button"
      onClick={() => onOpen(p.urlSlug)}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      className={`flex min-h-[120px] flex-1 flex-col overflow-hidden border-0 border-l-[0.5px] border-l-white/[0.03] text-left shadow-none transition-all duration-200 hover:bg-[var(--color-surface)] will-change-transform omega-haptic ${
        corrGlow ? "bg-[var(--color-up)]/[0.06]" : "bg-[var(--color-void)]"
      }`}
    >
      <div
        className="h-[2px] w-full shrink-0"
        style={{ backgroundColor: p.pairColor }}
        aria-hidden
      />
      <div className="flex min-h-0 flex-1 flex-col border-t-[0.5px] border-t-white/[0.08] px-3 py-3 grid grid-rows-[auto_16px_auto_auto_1fr] gap-y-0.5">
        <div className="flex items-center justify-between gap-2">
          <span
            className={`font-mono text-[10px] font-bold tracking-wide ${lum.title}`}
            style={{ color: p.pairColor }}
          >
            {p.display}
          </span>
          <span className={`font-mono text-[9px] tabular-nums ${lum.meta}`}>
            #{card.global_rank ?? "—"}
          </span>
        </div>

        <div className="min-h-[16px]">
          {chg != null && (
            <span
              className={`font-mono text-[10px] font-bold tabular-nums ${chg >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]"}`}
            >
              {chg >= 0 ? "+" : ""}
              {chg.toFixed(2)}%
            </span>
          )}
        </div>

        <p
          className={`font-mono text-xl font-bold tabular-nums leading-none ${lum.spot}`}
        >
          <BinaryResolve
            value={spotNum != null ? fmt2(spotNum) : "—"}
            resolveKey={spotNum ?? 0}
            paused={pausedBinaryResolve ?? isDimmed}
          />
        </p>
        <TerminalLabel className={`font-bold ${lum.regime}`} limit={24}>
          {(call?.regime as string) ?? card.structural_regime ?? "—"}
        </TerminalLabel>
        <div className="mt-2 self-end w-full">
          <ConfidenceBar
            value={call?.confidence != null ? Number(call.confidence) : null}
            tone="dark"
            color={p.pairColor}
          />
          <p className={`font-mono text-[8px] tabular-nums ${lum.meta} mt-1`}>
            CONF {fmtPct(call?.confidence as number | undefined)}
          </p>
        </div>
      </div>
      {corrLockedWhisper ? (
        <div className="shrink-0 border-t-[0.5px] border-t-[var(--color-border)] px-2 py-1.5">
          <GhostResolve
            value={corrLockedWhisper}
            resolveKey={corrLockedWhisper}
            active
            paused={isDimmed}
            className="!text-[8px]"
          />
        </div>
      ) : null}
    </motion.button>
  );
}

function tierForRank(rank: number): MosaicTier {
  if (rank <= 1) return "apex";
  if (rank <= 4) return "bench";
  return "outlier";
}

const sectorMotion = { duration: 0.2, ease: "easeOut" as const };

function SectorCell({
  col,
  focusedSector,
  onSectorEnter,
  children,
}: {
  col: 0 | 1 | 2;
  focusedSector: 0 | 1 | 2;
  onSectorEnter: (c: 0 | 1 | 2) => void;
  children: ReactNode;
}) {
  const isFocused = col === focusedSector;
  return (
    <motion.div
      variants={item}
      className="flex min-h-0 min-w-0 flex-col will-change-[opacity,filter]"
      onMouseEnter={() => onSectorEnter(col)}
      animate={{
        opacity: isFocused ? 1 : 0.3,
        filter: isFocused ? "grayscale(0%)" : "grayscale(100%)",
      }}
      transition={sectorMotion}
    >
      {children}
    </motion.div>
  );
}

/** 3×3 spatial grid: ranks 1–7, correlation matrix, macro drift — lenticular column luminance. */
export default function FxRegimePairSelectionPage() {
  const router = useRouter();
  const [hoveredLabel, setHoveredLabel] = useState<string | null>(null);
  const [focusedSector, setFocusedSector] = useState<0 | 1 | 2>(0);
  const regimeQ = useLatestRegimeCalls();
  const signalsQ = useLatestSignals();
  const deskSnapQ = useLatestDeskOpenCardsSnapshot();
  const matrixQ = useG10CorrelationMatrix();
  const deskData = deskSnapQ.data as DeskOpenCardsSnapshot | undefined;

  const calls = regimeQ.data;
  const sigs = signalsQ.data;
  const err = regimeQ.isError || signalsQ.isError || deskSnapQ.isError;
  const pending =
    regimeQ.isPending ||
    signalsQ.isPending ||
    (deskSnapQ.isPending && !deskData?.cards?.length);

  const cards = useMemo(() => {
    const raw = deskData?.cards ?? [];
    return [...raw].sort(
      (a, b) => (a.global_rank ?? 999) - (b.global_rank ?? 999),
    );
  }, [deskData?.cards]);

  const rank1 = cardAtRank(cards, 1);

  const validHover = useMemo(() => {
    if (!hoveredLabel || hoveredLabel === "apex-empty") return null;
    return G10_SET.has(hoveredLabel) ? hoveredLabel : null;
  }, [hoveredLabel]);

  const topPeer = useMemo(() => {
    if (!validHover) return null;
    const m = matrixQ.data;
    if (!m || Object.keys(m).length === 0) return null;
    return topCorrelatedPeer(m, validHover);
  }, [validHover, matrixQ.data]);

  const glowPeer =
    validHover && topPeer && topPeer !== validHover ? topPeer : null;
  const cellGlow = (pair: string | undefined) =>
    !!(glowPeer && pair === glowPeer);

  const corrLockWhisper = (forPair: string | null | undefined) => {
    if (!forPair || !validHover || !topPeer) return null;
    if (forPair !== validHover) return null;
    return `[ CORR_LOCKED: ${topPeer} ]`;
  };

  const openPair = (slug: string) => {
    router.push(`/terminal/fx-regime/${slug}`);
  };

  const rankSlot = (rank: number) => {
    const c = cardAtRank(cards, rank);
    return (
      <MosaicCell
        key={rank}
        tier={tierForRank(rank)}
        card={c}
        calls={calls}
        sigs={sigs}
        onOpen={openPair}
        isDimmed={!!validHover && validHover !== c?.pair}
        onHover={(h) => setHoveredLabel(h && c ? c.pair : null)}
        corrGlow={cellGlow(c?.pair)}
        corrLockedWhisper={corrLockWhisper(c?.pair)}
        pausedBinaryResolve={!!validHover && validHover !== c?.pair}
      />
    );
  };

  const rank1Block = rank1 ? (
    <div
      className={`flex min-h-0 flex-1 flex-col overflow-hidden border-0 border-t-[0.5px] border-t-white/[0.08] border-l-[0.5px] border-l-white/[0.03] transition-colors duration-200 ${
        cellGlow(rank1.pair)
          ? "bg-[var(--color-up)]/[0.06]"
          : "bg-[var(--color-void)]"
      }`}
      onMouseEnter={() => setHoveredLabel(rank1.pair)}
      onMouseLeave={() => setHoveredLabel(null)}
    >
      <DeskCard
        variant="hero"
        pairDisplay={pairMeta(rank1.pair).display}
        spot={
          sigs?.[rank1.pair]?.spot != null
            ? Number(sigs[rank1.pair]?.spot)
            : null
        }
        confidence={
          calls?.[rank1.pair]?.confidence != null
            ? Number(calls[rank1.pair]?.confidence)
            : null
        }
        rankJump={deskData?.rankJumpByPair[rank1.pair]}
        regimeAge={rank1.regime_age}
        apexScoreDisplay={
          rank1.apex_score != null ? Math.round(rank1.apex_score * 100) : null
        }
        structuralRegime={rank1.structural_regime}
        invalidationTriggered={rank1.invalidation_triggered}
        telemetryStatus={rank1.telemetry_status}
        dominanceArray={rank1.dominance_array}
        painIndex={rank1.pain_index}
        markovProbabilities={rank1.markov_probabilities}
        aiBrief={rank1.ai_brief}
        telemetryAudit={rank1.telemetry_audit}
        parameterInstability={rank1.parameter_instability}
        mathRateZTactical={
          sigs?.[rank1.pair]?.rate_z_tactical != null
            ? Number(sigs[rank1.pair]?.rate_z_tactical)
            : null
        }
        mathRateZStructural={
          sigs?.[rank1.pair]?.rate_z_structural != null
            ? Number(sigs[rank1.pair]?.rate_z_structural)
            : rank1.telemetry_audit?.rate_z_structural_mad ?? null
        }
        mathDynamicBeta={rank1.dominance_array[0]?.beta ?? null}
        pausedBinaryResolve={!!validHover && validHover !== rank1.pair}
        whisper={`GHOST_CHANNEL_${rank1.pair}`}
        corrLockedWhisper={corrLockWhisper(rank1.pair)}
      />
      <button
        type="button"
        onClick={() => openPair(pairMeta(rank1.pair).urlSlug)}
        className="border-0 border-t-[0.5px] border-t-[var(--color-border)] bg-[var(--color-void)] px-3 py-2 font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] shadow-none hover:bg-[var(--color-surface)] hover:text-[var(--color-text-secondary)]"
      >
        [ OPEN DESK → ]
      </button>
    </div>
  ) : (
    <MosaicCell
      tier="apex"
      card={undefined}
      calls={calls}
      sigs={sigs}
      onOpen={openPair}
      isDimmed={!!validHover}
      onHover={(h) => setHoveredLabel(h ? "apex-empty" : null)}
    />
  );

  const matrixCell = (
    <CorrelationMatrix
      matrix={matrixQ.data ?? null}
      pending={matrixQ.isPending}
      className="min-h-[140px] h-full"
    />
  );
  const macroCell = <MacroDriftEngine className="min-h-[140px] h-full" />;

  return (
    <div className="h-screen max-h-screen overflow-hidden bg-[var(--color-void)] font-sans text-[var(--color-text-secondary)]">
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="flex h-full w-full flex-col px-6 md:px-8 py-6"
        style={{ paddingTop: "calc(var(--terminal-nav-h, 76px) + 24px)" }}
      >
        <div className="mb-6 flex shrink-0 flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="mb-1.5 font-mono text-[9px] tracking-widest text-[var(--color-text-dim)]">
              FX REGIME · MOSAIC
            </p>
            <h1 className="font-mono text-lg font-bold tracking-tight text-[var(--color-text)] uppercase">
              G10 Systemic Pulse
            </h1>
            <p className="mt-1 max-w-md font-mono text-[10px] text-[var(--color-text-dim)]">
              3×3 lattice: ranks 1–7 + correlation ingress + macro drift.
            </p>
          </div>
          <Link
            href="/terminal"
            className="shrink-0 font-mono text-[10px] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)]"
          >
            ← Terminal overview
          </Link>
        </div>

        <div className="flex-1 min-h-0">
          {pending ? (
            <div className="grid h-full grid-cols-3 grid-rows-3 gap-px">
              {["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"].map(
                (k) => (
                  <div
                    key={k}
                    className="animate-pulse border-0 border-t-[0.5px] border-t-white/[0.06] border-l-[0.5px] border-l-white/[0.03] bg-[var(--color-void)]"
                  />
                ),
              )}
            </div>
          ) : (
            <div
              className="grid h-full grid-cols-1 gap-px lg:grid-cols-3 lg:grid-rows-3"
              onMouseLeave={() => {
                setFocusedSector(0);
                setHoveredLabel(null);
              }}
            >
              <SectorCell
                col={0}
                focusedSector={focusedSector}
                onSectorEnter={setFocusedSector}
              >
                {rank1Block}
              </SectorCell>
              <SectorCell
                col={1}
                focusedSector={focusedSector}
                onSectorEnter={setFocusedSector}
              >
                {rankSlot(2)}
              </SectorCell>
              <SectorCell
                col={2}
                focusedSector={focusedSector}
                onSectorEnter={setFocusedSector}
              >
                {rankSlot(3)}
              </SectorCell>
              <SectorCell
                col={0}
                focusedSector={focusedSector}
                onSectorEnter={setFocusedSector}
              >
                {rankSlot(4)}
              </SectorCell>
              <SectorCell
                col={1}
                focusedSector={focusedSector}
                onSectorEnter={setFocusedSector}
              >
                {rankSlot(5)}
              </SectorCell>
              <SectorCell
                col={2}
                focusedSector={focusedSector}
                onSectorEnter={setFocusedSector}
              >
                {rankSlot(6)}
              </SectorCell>
              <SectorCell
                col={0}
                focusedSector={focusedSector}
                onSectorEnter={setFocusedSector}
              >
                {rankSlot(7)}
              </SectorCell>
              <SectorCell
                col={1}
                focusedSector={focusedSector}
                onSectorEnter={setFocusedSector}
              >
                {matrixCell}
              </SectorCell>
              <SectorCell
                col={2}
                focusedSector={focusedSector}
                onSectorEnter={setFocusedSector}
              >
                {macroCell}
              </SectorCell>
            </div>
          )}
        </div>

        {err ? (
          <p className="mt-4 shrink-0 font-mono text-[10px] text-[var(--color-down)]">
            [ DATA_FLOW_INTERRUPTED: SYSTEMIC_SYNC_FAILED ]
          </p>
        ) : null}
      </motion.div>
    </div>
  );
}
