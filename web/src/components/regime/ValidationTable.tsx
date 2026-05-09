import type { ValidationRow, ValidationRowT5 } from "@/lib/supabase/queries";

interface ValidationTableProps {
  rows: ValidationRow[] | ValidationRowT5[];
  tone?: "light" | "dark";
  mode?: "legacy" | "t5t20";
}

function isT5Row(row: ValidationRow | ValidationRowT5): row is ValidationRowT5 {
  return "t5Outcome" in row;
}

export function ValidationTable({
  rows,
  tone = "dark",
  mode = "legacy",
}: ValidationTableProps) {
  const isD = tone === "dark";
  const bg = isD ? "bg-[var(--color-surface)]" : "bg-white";
  const border = isD ? "border-[var(--color-border)]" : "border-shell-border";
  const hdr = isD ? "text-[var(--color-text-muted)]" : "text-[#999]";
  const text = isD ? "text-[var(--color-text)]" : "text-[#111]";
  const muted = isD ? "text-[var(--color-text-secondary)]" : "text-[#555]";
  const stripe = isD ? "bg-[var(--color-elevated)]" : "bg-[#fafafa]";
  const headBg = isD ? "bg-[var(--color-elevated)]" : "bg-[#fafafa]";

  const upColor = "text-[var(--color-up)]";
  const downColor = "text-[var(--color-down)]";
  const neutralColor = "text-[var(--color-text-muted)]";

  const outcomeColor = (outcome: string) => {
    if (outcome === "CORRECT") return upColor;
    if (outcome === "WRONG") return downColor;
    return neutralColor;
  };

  const legacyHeaders = ["DATE", "PAIR", "REGIME", "OUTCOME", "RET %"];
  const t5t20Headers = [
    "DATE",
    "PAIR",
    "PRED",
    "T+5 RET",
    "T+5 OUT",
    "T+5 BRIER",
    "T+20 RET",
    "T+20 OUT",
    "T+20 BRIER",
  ];

  const headers = mode === "t5t20" ? t5t20Headers : legacyHeaders;

  return (
    <div className={`border ${border} overflow-hidden`}>
      <table
        className="w-full border-collapse font-mono"
        aria-label="Validation log"
      >
        <thead>
          <tr className={`border-b ${border} ${headBg}`}>
            {headers.map((h) => (
              <th
                key={h}
                scope="col"
                className={`px-4 py-2.5 text-left text-[10px] ${hdr} tracking-[0.1em] font-semibold whitespace-nowrap`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const isT5 = isT5Row(row);
            return (
              <tr
                key={`${row.date}-${row.pair}-${i}`}
                className={`border-b ${border} ${i % 2 === 1 ? stripe : bg}`}
              >
                <td
                  className={`px-4 py-2 text-[11px] ${muted} whitespace-nowrap`}
                >
                  {row.date}
                </td>
                <td
                  className={`px-4 py-2 text-[11px] ${text} font-bold whitespace-nowrap`}
                >
                  {row.pair}
                </td>

                {mode === "legacy" && !isT5 && (
                  <>
                    <td
                      className={`px-4 py-2 text-[10px] ${muted} max-w-[200px]`}
                    >
                      {row.call}
                    </td>
                    <td
                      className={`px-4 py-2 text-[11px] font-bold ${
                        row.outcome === "correct" ? upColor : downColor
                      }`}
                    >
                      {row.outcome === "correct" ? "✓ CORRECT" : "✗ INCORRECT"}
                    </td>
                    <td
                      className={`px-4 py-2 text-xs font-bold ${
                        row.return_pct >= 0 ? upColor : downColor
                      }`}
                    >
                      {row.return_pct >= 0 ? "+" : ""}
                      {row.return_pct.toFixed(2)}%
                    </td>
                  </>
                )}

                {mode === "t5t20" && isT5 && (
                  <>
                    <td className={`px-4 py-2 text-[10px] ${muted}`}>
                      {row.predicted}
                    </td>
                    <td
                      className={`px-4 py-2 text-[11px] tabular-nums ${
                        row.t5ReturnBps != null && row.t5ReturnBps >= 0
                          ? upColor
                          : downColor
                      }`}
                    >
                      {row.t5ReturnBps != null
                        ? `${row.t5ReturnBps >= 0 ? "+" : ""}${row.t5ReturnBps.toFixed(1)}`
                        : "—"}
                    </td>
                    <td
                      className={`px-4 py-2 text-[11px] font-bold ${outcomeColor(row.t5Outcome)}`}
                    >
                      {row.t5Outcome}
                    </td>
                    <td
                      className={`px-4 py-2 text-[11px] tabular-nums ${text}`}
                    >
                      {row.t5Brier != null ? row.t5Brier.toFixed(3) : "—"}
                    </td>
                    <td
                      className={`px-4 py-2 text-[11px] tabular-nums ${
                        row.t20ReturnBps != null && row.t20ReturnBps >= 0
                          ? upColor
                          : downColor
                      }`}
                    >
                      {row.t20ReturnBps != null
                        ? `${row.t20ReturnBps >= 0 ? "+" : ""}${row.t20ReturnBps.toFixed(1)}`
                        : "—"}
                    </td>
                    <td
                      className={`px-4 py-2 text-[11px] font-bold ${outcomeColor(row.t20Outcome)}`}
                    >
                      {row.t20Outcome}
                    </td>
                    <td
                      className={`px-4 py-2 text-[11px] tabular-nums ${text}`}
                    >
                      {row.t20Brier != null ? row.t20Brier.toFixed(3) : "—"}
                    </td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
