import type { ValidationRow } from "@/lib/supabase/queries";

interface ValidationTableProps {
  rows: ValidationRow[];
  tone?: "light" | "dark";
}

export function ValidationTable({
  rows,
  tone = "dark",
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

  return (
    <div className={`border ${border} overflow-hidden`}>
      <table className="w-full border-collapse font-mono" aria-label="Validation log — all directional calls and outcomes">
        <thead>
          <tr className={`border-b ${border} ${headBg}`}>
            {["DATE", "PAIR", "REGIME", "OUTCOME", "RET %"].map((h) => (
              <th
                key={h}
                scope="col"
                className={`px-4 py-2.5 text-left text-[10px] ${hdr} tracking-[0.1em] font-semibold`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className={`border-b ${border} ${i % 2 === 1 ? stripe : bg}`}
            >
              <td className={`px-4 py-2 text-[11px] ${muted}`}>{row.date}</td>
              <td
                className={`px-4 py-2 text-[11px] ${text} font-bold`}
              >
                {row.pair}
              </td>
              <td
                className={`px-4 py-2 text-[10px] ${muted} max-w-[200px]`}
              >
                {row.call}
              </td>
              <td
                className={`px-4 py-2 text-[11px] font-bold ${
                  row.outcome === "correct"
                    ? upColor
                    : downColor
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
