import type { ValidationTableRow } from "@/lib/validation-format";

interface ValidationTableProps {
  rows: ValidationTableRow[];
  tone?: "light" | "dark";
}

export function ValidationTable({
  rows,
  tone = "light",
}: ValidationTableProps) {
  const isD = tone === "dark";
  const bg = isD ? "bg-terminal-bg" : "bg-white";
  const border = isD ? "border-terminal-border" : "border-shell-border";
  const hdr = isD ? "text-terminal-muted" : "text-[#999]";
  const text = isD ? "text-white" : "text-[#111]";
  const muted = isD ? "text-[#aaa]" : "text-[#555]";
  const stripe = isD ? "bg-terminal-surface" : "bg-[#fafafa]";
  const headBg = isD ? "bg-terminal-surface" : "bg-[#fafafa]";

  return (
    <div className={`border ${border} overflow-hidden`}>
      <table className="w-full border-collapse font-mono">
        <thead>
          <tr className={`border-b ${border} ${headBg}`}>
            {["DATE", "PAIR", "CALL", "OUTCOME", "RET %"].map((h) => (
              <th
                key={h}
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
                    ? "text-up-shell"
                    : "text-down-shell"
                }`}
              >
                {row.outcome === "correct" ? "✓ correct" : "✗ incorrect"}
              </td>
              <td
                className={`px-4 py-2 text-xs font-bold ${
                  row.return_pct >= 0 ? "text-up-shell" : "text-down-shell"
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
