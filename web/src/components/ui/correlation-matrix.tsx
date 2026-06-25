"use client";

import { GhostResolve } from "@/components/ui/GhostResolve";
import {
  FX_MATRIX_ORDER,
  type FxCorrelationJson,
  correlationFromJson,
} from "@/lib/fxCorrelation";
import React, { useMemo, type CSSProperties } from "react";

function cellStyle(c: number): CSSProperties {
  const t = Math.max(-1, Math.min(1, c));
  const a = 0.12 + 0.55 * Math.abs(t);
  if (t >= 0) {
    return {
      backgroundColor: `color-mix(in srgb, var(--color-up) ${Math.round(a * 100)}%, transparent)`,
    };
  }
  return {
    backgroundColor: `color-mix(in srgb, var(--color-down) ${Math.round(a * 100)}%, transparent)`,
  };
}

const BEVEL =
  "border-[0.5px] border-t border-l border-t-[color-mix(in_srgb,var(--color-border)_12%,transparent)] border-l-[color-mix(in_srgb,var(--color-border)_6%,transparent)] border-r border-b border-r-[color-mix(in_srgb,var(--color-void)_40%,transparent)] border-b-[color-mix(in_srgb,var(--color-void)_50%,transparent)]";

type CorrelationMatrixProps = {
  matrix: FxCorrelationJson | null;
  pending?: boolean;
  className?: string;
};

export function CorrelationMatrix({
  matrix,
  pending,
  className = "",
}: CorrelationMatrixProps) {
  const labels = useMemo(() => [...FX_MATRIX_ORDER], []);

  return (
    <div
      className={`flex min-h-[140px] flex-col overflow-hidden border-0 border-t-[0.5px] border-t-[color-mix(in_srgb,var(--color-border)_8%,transparent)] border-l-[0.5px] border-l-[color-mix(in_srgb,var(--color-border)_3%,transparent)] bg-[var(--color-sunken)] p-2 ${className}`.trim()}
    >
      <p className="m-0 mb-1.5 font-mono text-[8px] tracking-[0.2em] text-[var(--color-text-dim)]">
        FX · CORR(120D)
      </p>
      {pending ? (
        <div className="flex flex-1 animate-pulse items-center justify-center font-mono text-[9px] text-[var(--color-text-dim)]">
          LOADING_MATRIX…
        </div>
      ) : (
        <div className="min-w-0 flex-1 overflow-x-auto">
          <div
            className="inline-grid gap-px"
            style={{
              gridTemplateColumns: `28px repeat(${labels.length}, minmax(14px, 1fr))`,
              gridTemplateRows: `16px repeat(${labels.length}, minmax(12px, 1fr))`,
            }}
          >
            <div className="min-h-[16px]" />
            {labels.map((lb) => (
              <div
                key={`h-${lb}`}
                className="flex min-h-[16px] items-end justify-center pb-0.5 overflow-hidden"
              >
                <GhostResolve
                  value={lb}
                  resolveKey={lb}
                  className="!text-[7px] !tracking-tighter"
                />
              </div>
            ))}
            {labels.map((row) => (
              <React.Fragment key={row}>
                <div className="flex min-h-[12px] items-center justify-end pr-0.5 overflow-hidden">
                  <GhostResolve
                    value={row}
                    resolveKey={`y-${row}`}
                    className="!text-[7px] !tracking-tighter"
                  />
                </div>
                {labels.map((col) => {
                  const c =
                    row === col
                      ? 1
                      : matrix
                        ? correlationFromJson(matrix, row, col)
                        : 0;
                  return (
                    <div
                      key={`${row}-${col}`}
                      className={`min-h-[12px] min-w-[12px] ${BEVEL}`}
                      style={cellStyle(c)}
                      title={`${row} vs ${col}: ${c.toFixed(3)}`}
                    />
                  );
                })}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
