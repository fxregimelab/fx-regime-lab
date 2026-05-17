import { SampleSizeBadge } from "@/components/ui/sample-size-badge";
import { normalizeProp } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import type { ValidationStats } from "@/lib/supabase/queries";

interface PairBreakdownTableProps {
  statsT5: ValidationStats[];
  statsT20: ValidationStats[];
}

function fmtPctDigits(n: number | null | undefined, digits = 1) {
  if (n == null) return "—";
  const prop = normalizeProp(n) ?? 0;
  const sign = prop >= 0 ? "+" : "";
  return `${sign}${(prop * 100).toFixed(digits)}%`;
}

function fmtBrier(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toFixed(3);
}

function fmtNum(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toFixed(0);
}

function fmtAcc(n: number | null | undefined) {
  if (n == null) return "—";
  const prop = normalizeProp(n) ?? 0;
  return `${(prop * 100).toFixed(1)}%`;
}

export function PairBreakdownTable({
  statsT5,
  statsT20,
}: PairBreakdownTableProps) {
  const t5Map = new Map(statsT5.map((s) => [s.pair, s]));
  const t20Map = new Map(statsT20.map((s) => [s.pair, s]));

  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      <div className="px-5 py-3 border-b border-[var(--color-border)]">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Per-Pair Breakdown
        </p>
      </div>
      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse font-mono text-[11px]"
          aria-label="Per-pair performance breakdown"
        >
          <thead>
            <tr className="border-b border-[var(--color-border)] bg-[var(--color-elevated)]">
              {[
                "PAIR",
                "T+5 WIN",
                "T+5 BRIER",
                "T+5 90D",
                "T+5 N",
                "T+20 WIN",
                "T+20 BRIER",
                "T+20 90D",
                "T+20 N",
              ].map((h) => (
                <th
                  key={h}
                  scope="col"
                  className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PAIRS.map((p, i) => {
              const label = p.label;
              const t5 = t5Map.get(label);
              const t20 = t20Map.get(label);
              return (
                <tr
                  key={p.label}
                  className={`border-b border-[var(--color-border-subtle)] last:border-b-0 ${i % 2 === 1 ? "bg-[var(--color-elevated)]" : "bg-[var(--color-surface)]"} hover:bg-[var(--color-elevated)] transition-colors`}
                >
                  <th
                    scope="row"
                    className="px-4 py-2.5 text-[var(--color-text-secondary)] whitespace-nowrap font-medium text-left"
                  >
                    {p.display}
                  </th>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtPctDigits(t5?.winRate)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtBrier(t5?.brierScore)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtAcc(t5?.rolling90dAccuracy)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text-muted)]">
                    <SampleSizeBadge n={t5?.sampleSize} />
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtPctDigits(t20?.winRate)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtBrier(t20?.brierScore)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtAcc(t20?.rolling90dAccuracy)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text-muted)]">
                    <SampleSizeBadge n={t20?.sampleSize} />
                  </td>
                </tr>
              );
            })}
            {/* ALL aggregate row */}
            {(() => {
              const allT5 = t5Map.get("ALL");
              const allT20 = t20Map.get("ALL");
              if (!allT5 && !allT20) return null;
              return (
                <tr className="border-t-2 border-[var(--color-border)] bg-[var(--color-elevated)] font-bold">
                  <td className="px-4 py-2.5 text-[var(--color-text)] whitespace-nowrap uppercase">
                    ALL
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtPctDigits(allT5?.winRate)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtBrier(allT5?.brierScore)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtAcc(allT5?.rolling90dAccuracy)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text-muted)]">
                    <SampleSizeBadge n={allT5?.sampleSize} />
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtPctDigits(allT20?.winRate)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtBrier(allT20?.brierScore)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text)]">
                    {fmtAcc(allT20?.rolling90dAccuracy)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-[var(--color-text-muted)]">
                    <SampleSizeBadge n={allT20?.sampleSize} />
                  </td>
                </tr>
              );
            })()}
          </tbody>
        </table>
      </div>
    </div>
  );
}
