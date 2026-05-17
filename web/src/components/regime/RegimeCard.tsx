import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { fmt2, fmtConfidence, fmtInt } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import type { LatestRegimeCall, LatestSignal } from "@/lib/supabase/queries";

interface RegimeCardProps {
  call?: LatestRegimeCall | null;
  signals?: LatestSignal | null;
  pairDisplay?: string;
}

export function RegimeCard({ call, signals, pairDisplay }: RegimeCardProps) {
  const pairMeta = PAIRS.find(
    (p) => p.display === pairDisplay || p.label === call?.pair,
  );
  const regimeAccent =
    call &&
    call.confidence != null &&
    call.confidence >= 0.55 &&
    (call.regime.includes("STRENGTH") ||
      call.regime.includes("WEAKNESS") ||
      call.regime.includes("PRESSURE") ||
      call.regime === "VOL_EXPANDING");

  const chg = signals?.day_change_pct;

  return (
    <div
      className="bg-[var(--terminal-bg-sunken)] border border-terminal-border py-3.5 px-4"
      style={{
        borderLeft: `3px solid ${pairMeta?.pairColor ?? "var(--terminal-fg-dim)"}`,
      }}
    >
      <div className="flex justify-between items-center mb-2">
        <span
          className="font-mono text-[11px] font-bold"
          style={{ color: pairMeta?.pairColor ?? "var(--terminal-fg)" }}
        >
          {pairDisplay ?? call?.pair}
        </span>
        {chg != null && (
          <span
            className={`font-mono text-[10px] font-semibold ${
              chg >= 0 ? "text-bullish" : "text-bearish"
            }`}
          >
            {chg >= 0 ? "+" : ""}
            {chg.toFixed(2)}%
          </span>
        )}
      </div>
      <p className="font-mono text-lg font-bold text-terminal-text tracking-tight mb-2">
        {signals?.spot?.toFixed(pairMeta?.label === "USDJPY" ? 2 : 4) ?? "—"}
      </p>
      <p
        className={`font-mono text-[10px] font-bold tracking-wide leading-snug mb-2.5 ${
          regimeAccent ? "text-brand-accent" : "text-[var(--terminal-fg-muted)]"
        }`}
      >
        {(call?.regime ?? "—").replace(/_/g, " ")}
      </p>
      <ConfidenceBar
        value={call?.confidence}
        tone="dark"
        color={pairMeta?.pairColor}
      />
      <div className="flex justify-between mt-1">
        <span className="font-mono text-[9px] text-[var(--terminal-fg-dim)] tracking-[0.1em]">
          " CONF
        </span>
        <span className="font-mono text-[10px] text-[var(--terminal-fg)] font-bold">
          "{fmtConfidence(call?.confidence)}
        </span>
      </div>
      <div className="border-t border-[var(--color-border)] mt-2.5 pt-2.5 flex flex-col gap-1">
        "
        {[
          ["RATE DIFF", fmt2(signals?.rate_diff_2y)],
          [
            "COT PCT",
            pairMeta?.label === "USDINR"
              ? "N/A"
              : fmtInt(signals?.cot_percentile),
          ],
          ["RVOL 20D", fmt2(signals?.realized_vol_20d)],
        ].map(([lbl, val]) => (
          <div key={lbl} className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--terminal-fg-dim)] tracking-wider">
              "{lbl}
            </span>
            <span className="font-mono text-[10px] text-[var(--terminal-fg)] font-semibold">
              "{val}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
