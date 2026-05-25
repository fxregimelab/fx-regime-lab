import { fmt2 } from "@/components/ui/utils";
import type { CrossAssetSnapshot, LatestSignal } from "@/lib/supabase/queries";

interface CrossAssetMatrixProps {
  data: CrossAssetSnapshot;
  signals?: Record<string, LatestSignal>;
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

export function CrossAssetMatrix({ data, signals }: CrossAssetMatrixProps) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
      <div className="px-5 py-3 border-b border-[var(--color-border)] flex items-center justify-between">
        <p className="font-sans text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Cross-Asset Context
        </p>
        <span className="font-sans text-[9px] text-[var(--color-text-dim)]">
          Live market proxies
        </span>
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
              {value != null ? (
                <p className="font-mono text-[clamp(18px,2vw,22px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
                  {fmt2(value)}
                </p>
              ) : (
                <div className="py-1">
                  <span className="font-sans text-[10px] text-[var(--color-text-dim)]">
                    Awaiting data
                  </span>
                </div>
              )}
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
      {signals && (
        <div className="px-5 py-3 border-t border-[var(--color-border)]">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-3">
            Pair Macro
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-px bg-[var(--color-border)]">
            {Object.entries(signals).map(([pair, sig]) => {
              const tiles: { label: string; value: string | null }[] = [];
              if (pair === "EURUSD") {
                if (sig.ecb_balance_sheet != null)
                  tiles.push({
                    label: "ECB BS",
                    value: fmt2(sig.ecb_balance_sheet),
                  });
                if (sig.bund_btp_spread != null)
                  tiles.push({
                    label: "Bund-BTP",
                    value: fmt2(sig.bund_btp_spread),
                  });
              }
              if (pair === "USDJPY") {
                if (sig.boj_policy_rate != null)
                  tiles.push({
                    label: "BoJ Rate",
                    value: fmt2(sig.boj_policy_rate),
                  });
              }
              if (pair === "USDINR") {
                if (sig.india_vix != null)
                  tiles.push({
                    label: "India VIX",
                    value: fmt2(sig.india_vix),
                  });
                if (sig.inr_forward_premium != null)
                  tiles.push({
                    label: "INR Fwd",
                    value: fmt2(sig.inr_forward_premium),
                  });
              }
              return tiles.map((t) => (
                <div
                  key={`${pair}-${t.label}`}
                  className="bg-[var(--color-surface)] p-3"
                >
                  <p className="font-mono text-[9px] text-[var(--color-text-muted)] uppercase">
                    {t.label}
                  </p>
                  <p className="font-mono text-[11px] text-[var(--color-text)]">
                    {t.value}
                  </p>
                </div>
              ));
            })}
          </div>
        </div>
      )}
    </div>
  );
}
