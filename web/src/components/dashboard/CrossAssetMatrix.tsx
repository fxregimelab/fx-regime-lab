import { fmt2 } from "@/components/ui/utils";
import type { CrossAssetSnapshot } from "@/lib/supabase/queries";

interface CrossAssetMatrixProps {
  data: CrossAssetSnapshot;
}

const TILES: {
  key: keyof CrossAssetSnapshot;
  label: string;
}[] = [
  { key: "vix", label: "VIX" },
  { key: "dxy", label: "DXY" },
  { key: "oil", label: "BRENT" },
  { key: "gold", label: "GOLD" },
  { key: "copper", label: "COPPER" },
  { key: "stoxx", label: "STOXX" },
  { key: "us10y", label: "US10Y" },
];

export function CrossAssetMatrix({ data }: CrossAssetMatrixProps) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
      <div className="px-5 py-3 border-b border-[var(--color-border)]">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Cross-Asset Context
        </p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-px bg-[var(--color-border)]">
        {TILES.map((t) => {
          const item = data[t.key];
          const value = item?.value;
          const change = item?.change;
          const changeColor =
            change == null
              ? "var(--color-text-muted)"
              : change >= 0
                ? "var(--color-up)"
                : "var(--color-down)";
          const changeSign = change != null && change >= 0 ? "+" : "";

          return (
            <div
              key={t.key}
              className="bg-[var(--color-surface)] p-4 flex flex-col justify-between"
            >
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
                {t.label}
              </p>
              <p className="font-mono text-[clamp(18px,2vw,22px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
                {value != null ? fmt2(value) : "—"}
              </p>
              {change != null && (
                <p
                  className="font-mono text-[10px] mt-1 tabular-nums"
                  style={{ color: changeColor }}
                >
                  {changeSign}
                  {change.toFixed(2)}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
