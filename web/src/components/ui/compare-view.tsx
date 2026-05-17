"use client";

import { DeskCard } from "@/components/ui/desk-card";
import { SignalCardSkeleton } from "@/components/ui/skeletons";
import { fmtConfidence } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import {
  useLatestDeskOpenCardsSnapshot,
  useLatestRegimeCalls,
  useLatestSignals,
} from "@/lib/queries";
import Link from "next/link";

interface CompareViewProps {
  /** Comma-separated pair labels: "eurusd,usdjpy" */
  pairsParam: string;
}

/**
 * Side-by-side pair comparison view.
 * Synchronized scroll via shared container.
 */
export function CompareView({ pairsParam }: CompareViewProps) {
  const selectedLabels = pairsParam
    .split(",")
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);

  const pairMetas = PAIRS.filter((p) => selectedLabels.includes(p.label));

  const { data: calls } = useLatestRegimeCalls();
  const { data: sigs } = useLatestSignals();
  const { data: deskData } = useLatestDeskOpenCardsSnapshot();

  const cards = deskData?.cards ?? [];

  if (pairMetas.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-10 text-center max-w-md">
          <p className="font-mono text-[10px] tracking-widest text-[var(--color-warn)] uppercase mb-3">
            [ NO PAIRS SELECTED ]
          </p>
          <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-relaxed mb-4">
            Cmd+Click (or Ctrl+Click) two pair cards on the FX Regime Mosaic to
            compare them side-by-side.
          </p>
          <Link
            href="/terminal/fx-regime"
            className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] hover:text-[var(--color-text)] underline underline-offset-2"
          >
            ← BACK TO MOSAIC
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[9px] tracking-[0.2em] text-[var(--color-text-dim)] uppercase">
          Pair Comparison
        </p>
        <Link
          href="/terminal/fx-regime"
          className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] hover:text-[var(--color-text)] underline underline-offset-2"
        >
          ← BACK TO MOSAIC
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)]">
        {pairMetas.map((meta) => {
          const card = cards.find((c) => c.pair === meta.label);
          const call = calls?.[meta.label];
          const sig = sigs?.[meta.label];

          if (!card) {
            return (
              <div
                key={meta.label}
                className="bg-[var(--color-void)] p-4 min-h-[300px]"
              >
                <SignalCardSkeleton />
              </div>
            );
          }

          return (
            <div
              key={meta.label}
              className="bg-[var(--color-void)] p-4 overflow-y-auto max-h-[80vh]"
            >
              <div className="mb-3">
                <p className="font-mono text-[10px] tracking-widest text-[var(--color-text-muted)] uppercase">
                  {meta.display}
                </p>
                <p className="font-mono text-[11px] text-[var(--color-text-dim)]">
                  Spot:{" "}
                  {sig?.spot != null
                    ? Number(sig.spot).toFixed(meta.label === "USDJPY" ? 2 : 4)
                    : "—"}{" "}
                  <span
                    className={
                      (sig?.day_change_pct as number) >= 0
                        ? "text-[var(--color-up)]"
                        : "text-[var(--color-down)]"
                    }
                  >
                    {(sig?.day_change_pct as number) >= 0 ? "+" : ""}
                    {(sig?.day_change_pct as number)?.toFixed(2) ?? "—"}%
                  </span>
                </p>
              </div>

              <DeskCard
                variant="default"
                pairDisplay={meta.display}
                spot={sig?.spot != null ? Number(sig.spot) : null}
                confidence={
                  call?.confidence != null ? Number(call.confidence) : null
                }
                structuralRegime={card.structural_regime}
                invalidationTriggered={card.invalidation_triggered}
                telemetryStatus={card.telemetry_status}
                dominanceArray={card.dominance_array}
                painIndex={card.pain_index}
                markovProbabilities={card.markov_probabilities}
                aiBrief={card.ai_brief}
                telemetryAudit={card.telemetry_audit}
                parameterInstability={card.parameter_instability}
              />

              <div className="mt-4 space-y-2">
                <p className="font-mono text-[9px] tracking-widest text-[var(--color-text-muted)] uppercase">
                  Confidence
                </p>
                <p className="font-mono text-[18px] text-[var(--color-text)] tabular-nums">
                  {fmtConfidence(call?.confidence)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
