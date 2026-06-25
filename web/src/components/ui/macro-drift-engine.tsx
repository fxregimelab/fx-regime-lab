"use client";

import { useBriefLogDominanceSeries, useLatestBrief } from "@/lib/queries";
import { motion } from "framer-motion";
import { useMemo } from "react";

function padDominanceSeries(
  rows: Array<{ dollar_dominance: number | null }>,
  targetLen: number,
): number[] {
  const raw = rows.map((r) =>
    r.dollar_dominance != null && Number.isFinite(r.dollar_dominance)
      ? r.dollar_dominance
      : Number.NaN,
  );
  const nums = raw.filter((n) => !Number.isNaN(n));
  if (nums.length === 0) return Array.from({ length: targetLen }, () => 50);
  let s = nums.slice(-targetLen);
  const padVal = s[0] ?? 50;
  while (s.length < targetLen) {
    s = [padVal, ...s];
  }
  return s;
}

type MacroDriftEngineProps = {
  className?: string;
};

export function MacroDriftEngine({ className = "" }: MacroDriftEngineProps) {
  const briefQ = useLatestBrief();
  const seriesQ = useBriefLogDominanceSeries(5);

  const values = useMemo(
    () => padDominanceSeries(seriesQ.data ?? [], 5),
    [seriesQ.data],
  );

  const last = values.length >= 2 ? values[values.length - 1] : undefined;
  const prev = values.length >= 2 ? values[values.length - 2] : undefined;
  const delta = last !== undefined && prev !== undefined ? last - prev : null;
  const latest =
    briefQ.data?.dollar_dominance ?? values[values.length - 1] ?? null;
  const outlier = briefQ.data?.idiosyncratic_outlier?.trim() || null;

  const pending = briefQ.isPending || seriesQ.isPending;

  const pathD = useMemo(() => {
    const w = 100;
    const h = 36;
    const pad = 4;
    if (values.length === 0) return "";
    let min = Math.min(...values);
    let max = Math.max(...values);
    if (max === min) {
      min -= 1;
      max += 1;
    }
    const denom = Math.max(1, values.length - 1);
    const pts = values.map((v, i) => {
      const x = pad + (i / denom) * (w - pad * 2);
      const y = pad + (1 - (v - min) / (max - min)) * (h - pad * 2);
      return `${x},${y}`;
    });
    return `M ${pts.join(" L ")}`;
  }, [values]);

  return (
    <div
      className={`flex min-h-[140px] flex-col overflow-hidden border-0 border-t-[0.5px] border-t-[color-mix(in_srgb,var(--color-border)_8%,transparent)] border-l-[0.5px] border-l-[color-mix(in_srgb,var(--color-border)_3%,transparent)] bg-[var(--color-sunken)] p-2 ${className}`.trim()}
    >
      <p className="m-0 mb-2 font-mono text-[8px] tracking-[0.2em] text-[var(--color-text-dim)]">
        MACRO · DRIFT
      </p>
      {pending ? (
        <div className="flex flex-1 animate-pulse items-center justify-center font-mono text-[9px] text-[var(--color-text-dim)]">
          SYNCING_BRIEF_LOG…
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <p className="m-0 font-mono text-[8px] tracking-widest text-[var(--color-text-muted)]">
                USD_DOMINANCE_DELTA
              </p>
              <p className="m-0 mt-0.5 font-mono text-[11px] tabular-nums text-[var(--color-text-secondary)]">
                {delta != null && Number.isFinite(delta) ? (
                  <>
                    <span
                      className={
                        delta >= 0
                          ? "text-[var(--color-up)]"
                          : "text-[var(--color-down)]"
                      }
                    >
                      {delta >= 0 ? "+" : ""}
                      {delta.toFixed(1)}
                    </span>
                    <span className="text-[var(--color-text-dim)]">
                      {" "}
                      pts / 1d
                    </span>
                  </>
                ) : (
                  <span className="text-[var(--color-text-dim)]">—</span>
                )}
              </p>
              {latest != null ? (
                <p className="m-0 mt-1 font-mono text-[9px] tabular-nums text-[var(--color-text-muted)]">
                  NOW{" "}
                  <span className="text-[var(--color-text)]">
                    {latest.toFixed(0)}
                  </span>{" "}
                  / 100
                </p>
              ) : null}
            </div>
            <svg
              viewBox="0 0 100 36"
              className="h-10 w-[44%] shrink-0 text-[var(--color-up)]"
              preserveAspectRatio="none"
              aria-hidden
            >
              <title>Drift Engine</title>
              <path
                d={pathD}
                fill="none"
                stroke="currentColor"
                strokeWidth="0.8"
                vectorEffect="non-scaling-stroke"
              />
            </svg>
          </div>
          <div className="border-t-[0.5px] border-t-[var(--color-border-subtle)] pt-2">
            <p className="m-0 font-mono text-[8px] tracking-widest text-[var(--color-text-muted)]">
              FX_IDIO_OUTLIER
            </p>
            {outlier ? (
              <motion.span
                className="mt-1 inline-block font-mono text-[10px] font-bold tracking-widest text-[var(--color-text)]"
                animate={{ opacity: [1, 0.35, 1] }}
                transition={{
                  duration: 1.4,
                  repeat: Number.POSITIVE_INFINITY,
                  ease: "easeInOut",
                }}
              >
                {outlier}
              </motion.span>
            ) : (
              <p className="m-0 mt-1 font-mono text-[9px] text-[var(--color-text-dim)]">
                NULL
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
