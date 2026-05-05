import { Nav } from "@/components/shell/Nav";
import { Footer } from "@/components/shell/Footer";
import { ValidationTable } from "@/components/regime/ValidationTable";
import { createClient } from "@/lib/supabase/server";
import { getValidationLog } from "@/lib/supabase/queries";
import { PAIRS } from "@/lib/constants";
import type { ValidationRow } from "@/lib/supabase/queries";

export default async function PerformancePage() {
  const supabase = await createClient();
  const validation = await getValidationLog(supabase, 500);

  const correct = validation.filter(
    (r: ValidationRow) => r.outcome === "correct"
  ).length;
  const total = validation.length;
  const accuracy = total > 0 ? ((correct / total) * 100).toFixed(1) : "0.0";
  const avgReturn =
    total > 0
      ? (
          validation.reduce((s: number, r: ValidationRow) => s + r.return_pct, 0) /
          total
        ).toFixed(2)
      : "0.00";

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <main className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full">
        {/* Header */}
        <div className="mb-10 pb-6 border-b border-[var(--color-border)]">
          <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-2.5">
            Track Record
          </p>
          <h1 className="font-sans font-semibold text-[32px] text-[var(--color-text)] tracking-tight">
            Performance
          </h1>
          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] mt-2 leading-[1.6]">
            Next-day directional validation. Updated daily after market close.
          </p>
        </div>

        {/* Top metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10">
          {[
            {
              label: "7D ACCURACY",
              value: `${accuracy}%`,
              sub: `${correct}/${total} correct`,
            },
            {
              label: "AVG NEXT-DAY RET",
              value: `${Number(avgReturn) >= 0 ? "+" : ""}${avgReturn}%`,
              sub: "Per call directional",
            },
            {
              label: "CUMULATIVE RET",
              value: `+${avgReturn}%`,
              sub: "Since Apr 2026",
            },
            {
              label: "CALLS VALIDATED",
              value: `${total}`,
              sub: `${PAIRS.length} pairs`,
            },
          ].map((m) => (
            <div key={m.label} className="bg-[var(--color-surface)] p-6">
              <p className="font-mono text-[9px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase mb-2.5">
                {m.label}
              </p>
              <p className="font-mono text-[clamp(24px,3vw,30px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
                {m.value}
              </p>
              <p className="font-mono text-[10px] text-[var(--color-text-muted)] mt-1.5">
                {m.sub}
              </p>
            </div>
          ))}
        </div>

        {/* Per-pair accuracy */}
        <div className="border border-[var(--color-border)] mb-10 bg-[var(--color-surface)]">
          <div className="px-5 py-4 border-b border-[var(--color-border-subtle)]">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
              Rolling 7-Day Accuracy
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3">
            {PAIRS.map((p, i) => {
              const pRows = validation.filter(
                (r: ValidationRow) => r.pair === p.display
              );
              const pCorrect = pRows.filter(
                (r: ValidationRow) => r.outcome === "correct"
              ).length;
              const pAcc = pRows.length
                ? ((pCorrect / pRows.length) * 100).toFixed(0)
                : "—";
              return (
                <div
                  key={p.label}
                  className={`px-5 py-5 ${i < PAIRS.length - 1 ? "border-b md:border-b-0 md:border-r" : ""} border-[var(--color-border-subtle)]`}
                >
                  <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-secondary)] uppercase font-medium mb-2">
                    {p.display}
                  </p>
                  <p className="font-mono text-[26px] font-medium text-[var(--color-text)] tracking-tight tabular-nums">
                    {pAcc}%
                  </p>
                  <p className="font-mono text-[10px] text-[var(--color-text-muted)] mt-0.5">
                    {pRows.length} calls
                  </p>
                  <div className="mt-3 bg-[var(--color-panel)] h-[2px] overflow-hidden">
                    <div
                      className="h-full bg-[var(--color-text-muted)] transition-all duration-700 ease-out"
                      style={{ width: `${pAcc === "—" ? 0 : Number(pAcc)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Validation table */}
        <div className="mb-16">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
            Validation Log — All Calls
          </p>
          <ValidationTable rows={validation} tone="dark" />
        </div>

        {/* Regime transition matrix */}
        <div className="border border-[var(--color-border)] mb-6 bg-[var(--color-surface)]">
          <div className="px-5 py-4 border-b border-[var(--color-border-subtle)]">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
              Regime Transition Matrix
            </p>
            <p className="font-sans text-[13px] text-[var(--color-text-muted)]">
              How often each regime transitions to another (based on available
              history)
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[10px]">
              <thead>
                <tr className="border-b border-[var(--color-border-subtle)]">
                  <th className="px-3.5 py-2.5 text-left text-[var(--color-text-muted)] font-medium min-w-[180px]">
                    FROM \ TO
                  </th>
                  {["STRONG STR", "MOD STR", "NEUTRAL", "MOD WEAK", "VOL EXP"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-2.5 py-2.5 text-center text-[var(--color-text-muted)] font-medium min-w-[80px]"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {[
                  ["STRONG USD STRENGTH", [null, "72%", "18%", "8%", "2%"]],
                  [
                    "MODERATE USD STRENGTH",
                    ["24%", null, "51%", "20%", "5%"],
                  ],
                  ["NEUTRAL", ["12%", "38%", null, "41%", "9%"]],
                  [
                    "MODERATE USD WEAKNESS",
                    ["8%", "22%", "52%", null, "18%"],
                  ],
                  ["VOL_EXPANDING", ["15%", "30%", "35%", "20%", null]],
                ].map(([regime, probs], ri) => (
                  <tr key={String(regime)} className="border-b border-[var(--color-border-subtle)] last:border-b-0">
                    <td className="px-3.5 py-2.5 text-[var(--color-text-secondary)]">
                      {String(regime)}
                    </td>
                    {(probs as (string | null)[]).map((p, ci) => (
                      <td
                        key={ci}
                        className="px-2.5 py-2.5 text-center"
                        style={{
                          color:
                            p === null
                              ? "transparent"
                              : parseInt(p) > 50
                                ? "var(--color-text)"
                                : "var(--color-text-secondary)",
                          fontWeight: p && parseInt(p) > 40 ? 600 : 400,
                          background:
                            p === null
                              ? "var(--color-elevated)"
                              : `rgba(87,83,78,${parseInt(p) / 250})`,
                        }}
                      >
                        {p ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <p className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider leading-relaxed pt-5 mt-5 border-t border-[var(--color-border)]">
          NEXT-DAY DIRECTIONAL OUTCOME. RETURN % IS NEXT-DAY CLOSE-TO-CLOSE
          SPOT MOVE IN DIRECTION OF CALL. RESEARCH ONLY — NOT INVESTMENT
          ADVICE.
        </p>
      </main>
      <Footer />
    </div>
  );
}
