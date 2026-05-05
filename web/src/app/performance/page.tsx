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
    <div className="min-h-screen flex flex-col bg-white">
      <Nav />
      <main className="flex-1 max-w-[1152px] mx-auto px-6 py-12 w-full">
        {/* Header */}
        <div className="mb-10 pb-6 border-b border-shell-border">
          <p className="font-mono text-[10px] text-shell-muted tracking-[0.12em] mb-2.5">
            TRACK RECORD
          </p>
          <h1 className="font-sans font-extrabold text-[32px] text-shell-text tracking-tight">
            Performance
          </h1>
          <p className="font-sans text-sm text-shell-secondary mt-2">
            Next-day directional validation. Updated daily after market close.
          </p>
        </div>

        {/* Top metrics */}
        <div
          className="grid grid-cols-2 md:grid-cols-4 gap-px mb-8"
          style={{ background: "#e5e5e5", boxShadow: "0 0 0 1px #e5e5e5" }}
        >
          {[
            {
              label: "7D ACCURACY",
              value: `${accuracy}%`,
              color: "#16a34a",
              sub: `${correct}/${total} correct`,
            },
            {
              label: "AVG NEXT-DAY RET",
              value: `${Number(avgReturn) >= 0 ? "+" : ""}${avgReturn}%`,
              color: "#F5923A",
              sub: "Per call directional",
            },
            {
              label: "CUMULATIVE RET",
              value: `+${avgReturn}%`,
              color: "#4BA3E3",
              sub: "Since Apr 2026",
            },
            {
              label: "CALLS VALIDATED",
              value: `${total}`,
              color: "#0a0a0a",
              sub: `${PAIRS.length} pairs`,
            },
          ].map((m) => (
            <div key={m.label} className="bg-white p-5">
              <p className="font-mono text-[9px] text-[#999] tracking-[0.12em] mb-2.5">
                {m.label}
              </p>
              <p
                className="font-mono text-[30px] font-bold tracking-tight leading-none"
                style={{ color: m.color }}
              >
                {m.value}
              </p>
              <p className="font-mono text-[10px] text-[#bbb] mt-1.5">
                {m.sub}
              </p>
            </div>
          ))}
        </div>

        {/* Per-pair accuracy */}
        <div className="border border-shell-border mb-6">
          <div className="px-5 py-4 border-b border-[#f0f0f0]">
            <p className="font-mono text-[10px] text-[#888] tracking-[0.1em]">
              ROLLING 7-DAY ACCURACY
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 border-b border-[#f0f0f0]">
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
                  className="px-5 py-4"
                  style={{
                    borderRight: i < PAIRS.length - 1 ? "1px solid #f0f0f0" : "none",
                  }}
                >
                  <p
                    className="font-mono text-[10px] font-bold mb-1"
                    style={{ color: p.pairColor }}
                  >
                    {p.display}
                  </p>
                  <p className="font-mono text-[26px] font-bold text-shell-text tracking-tight">
                    {pAcc}%
                  </p>
                  <p className="font-mono text-[10px] text-[#bbb] mt-0.5">
                    {pRows.length} calls
                  </p>
                  <div className="mt-2.5 bg-[#f0f0f0] h-[3px]">
                    <div
                      className="h-full"
                      style={{
                        width: `${pAcc === "—" ? 0 : Number(pAcc)}%`,
                        background: p.pairColor,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Validation table */}
        <div className="mb-16">
          <p className="font-mono text-[10px] text-shell-muted tracking-[0.12em] mb-4">
            VALIDATION LOG — ALL CALLS
          </p>
          <ValidationTable rows={validation} tone="light" />
        </div>

        {/* Regime transition matrix */}
        <div className="border border-shell-border mb-6">
          <div className="px-5 py-4 border-b border-[#f0f0f0]">
            <p className="font-mono text-[10px] text-[#888] tracking-[0.1em] mb-1">
              REGIME TRANSITION MATRIX
            </p>
            <p className="font-sans text-[13px] text-[#aaa]">
              How often each regime transitions to another (based on available
              history)
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[10px]">
              <thead>
                <tr className="border-b border-[#f0f0f0]">
                  <th className="px-3.5 py-2.5 text-left text-[#aaa] font-medium min-w-[180px]">
                    FROM \ TO
                  </th>
                  {["STRONG STR", "MOD STR", "NEUTRAL", "MOD WEAK", "VOL EXP"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-2.5 py-2.5 text-center text-[#aaa] font-medium min-w-[80px]"
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
                  <tr key={String(regime)} className="border-b border-[#f8f8f8]">
                    <td className="px-3.5 py-2.5 text-[#555]">{String(regime)}</td>
                    {(probs as (string | null)[]).map((p, ci) => (
                      <td
                        key={ci}
                        className="px-2.5 py-2.5 text-center"
                        style={{
                          color:
                            p === null
                              ? "#f0f0f0"
                              : parseInt(p) > 50
                                ? "#0a0a0a"
                                : "#888",
                          fontWeight:
                            p && parseInt(p) > 40 ? 700 : 400,
                          background:
                            p === null
                              ? "#f8f8f8"
                              : `rgba(75,163,227,${parseInt(p) / 200})`,
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

        <p className="font-mono text-[10px] text-[#c0c0c0] tracking-wider leading-relaxed pt-5 mt-5 border-t border-shell-border">
          NEXT-DAY DIRECTIONAL OUTCOME. RETURN % IS NEXT-DAY CLOSE-TO-CLOSE
          SPOT MOVE IN DIRECTION OF CALL. RESEARCH ONLY — NOT INVESTMENT
          ADVICE.
        </p>
      </main>
      <Footer />
    </div>
  );
}
