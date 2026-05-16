import { PAIRS } from "@/lib/constants";
import { createClient } from "@/lib/supabase/server";
import { ImageResponse } from "next/og";

export const alt = "FX Regime Lab — Pair Regime";
export const size = { width: 1200, height: 630 };
export const runtime = "edge";
export const contentType = "image/png";

function getRegimeColor(regime: string): string {
  const r = regime.toUpperCase();
  if (
    r.includes("STRENGTH") ||
    r.includes("BULLISH") ||
    r.includes("APPRECIATION")
  ) {
    return "#10b981";
  }
  if (
    r.includes("WEAKNESS") ||
    r.includes("BEARISH") ||
    r.includes("DEPRECIATION") ||
    r.includes("PRESSURE")
  ) {
    return "#ef4444";
  }
  return "#6b7280";
}

function getDisplayPair(pairSlug: string) {
  const pair = PAIRS.find((p) => p.urlSlug === pairSlug.toLowerCase());
  return pair ?? PAIRS[0];
}

export default async function Image({
  params,
}: {
  params: Promise<{ pair: string }>;
}) {
  const { pair: pairSlug } = await params;
  const pair = getDisplayPair(pairSlug);

  let regime = "—";
  let confidence: number | null = null;
  let rolling90d: number | null = null;

  try {
    const supabase = await createClient();

    const { data: regimeData } = await supabase
      .from("regime_calls")
      .select("regime, confidence")
      .eq("pair", pair.label)
      .order("date", { ascending: false })
      .limit(1)
      .maybeSingle();

    const regimeRow = regimeData as {
      regime: string;
      confidence: number;
    } | null;
    if (regimeRow) {
      regime = regimeRow.regime;
      confidence = regimeRow.confidence;
    }

    const { data: statsData } = await supabase
      .from("validation_stats")
      .select("t5_rolling_90d_accuracy")
      .eq("pair", pair.label)
      .order("as_of_date", { ascending: false })
      .limit(1)
      .maybeSingle();

    const statsRow = statsData as { t5_rolling_90d_accuracy: number } | null;
    if (statsRow) {
      rolling90d = statsRow.t5_rolling_90d_accuracy;
    }
  } catch {
    // Fallback to defaults
  }

  const regimeColor = getRegimeColor(regime);
  const confPct =
    confidence != null
      ? Math.min(100, Math.max(0, Math.round(confidence * 100)))
      : null;
  const accPct =
    rolling90d != null
      ? Math.min(100, Math.max(0, Math.round(rolling90d * 100)))
      : null;

  return new ImageResponse(
    <div
      style={{
        width: size.width,
        height: size.height,
        background: "#0a0a0a",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: 48,
        color: "#ffffff",
        border: "4px solid #10b981",
        fontFamily:
          "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        <div
          style={{
            fontSize: 96,
            fontWeight: 700,
            letterSpacing: -2,
            lineHeight: 1,
            color: "#ffffff",
          }}
        >
          {pair.display}
        </div>
        <div
          style={{
            fontSize: 48,
            fontWeight: 600,
            lineHeight: 1.2,
            color: regimeColor,
            textTransform: "uppercase",
          }}
        >
          {regime}
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            marginTop: 16,
          }}
        >
          <div
            style={{
              fontSize: 28,
              color: "#d4d4d4",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            CONFIDENCE {confPct != null ? `${confPct}%` : "—"}
          </div>
          <div
            style={{
              fontSize: 28,
              color: "#a3a3a3",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            90-DAY ROLLING ACCURACY {accPct != null ? `${accPct}%` : "—"}
          </div>
        </div>
      </div>
      <div
        style={{
          fontSize: 22,
          color: "#525252",
          letterSpacing: "0.3em",
          textTransform: "uppercase",
        }}
      >
        FX Regime Lab
      </div>
    </div>,
    { ...size },
  );
}
