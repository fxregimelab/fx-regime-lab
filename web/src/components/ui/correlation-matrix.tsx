"use client";

import { GhostResolve } from "@/components/ui/GhostResolve";
import {
  type G10CorrelationJson,
  G10_MATRIX_ORDER,
  correlationFromJson,
} from "@/lib/g10Correlation";
import React, { useMemo, type CSSProperties } from "react";

function cellStyle(c: number): CSSProperties {
  const t = Math.max(-1, Math.min(1, c));
  const a = 0.12 + 0.55 * Math.abs(t);
  if (t >= 0) {
    return { backgroundColor: `rgba(16, 185, 129, ${a})` };
  }
  return { backgroundColor: `rgba(244, 63, 94, ${a})` };
}

const BEVEL =
  "border-[0.5px] border-t border-l border-t-white/[0.12] border-l-white/[0.06] border-r border-b border-r-black/40 border-b-black/50";

type CorrelationMatrixProps = {
  matrix: G10CorrelationJson | null;
  pending?: boolean;
  className?: string;
};

export function CorrelationMatrix({
  matrix,
  pending,
  className = "",
}: CorrelationMatrixProps) {
  const labels = useMemo(() => [...G10_MATRIX_ORDER], []);

  return (
    <div
      className={`flex min-h-[140px] flex-col overflow-hidden border-0 border-t-[0.5px] border-t-white/[0.08] border-l-[0.5px] border-l-white/[0.03] bg-[#050505] p-2 ${className}`.trim()}
    >
      <p className="m-0 mb-1.5 font-mono text-[8px] tracking-[0.2em] text-[#555]">
        G10 · CORR(120D)
      </p>
      {pending ? (
        <div className="flex flex-1 animate-pulse items-center justify-center font-mono text-[9px] text-[#444]">
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
