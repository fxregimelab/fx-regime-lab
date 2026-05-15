import { createClient } from "@supabase/supabase-js";
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "FX Regime Lab — Performance";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  let winRate: number | null = null;
  let sampleSize: number | null = null;

  if (url && anon) {
    const supabase = createClient(url, anon);
    const { data } = await supabase
      .from("validation_stats")
      .select("t5_win_rate, t5_total_calls")
      .eq("pair", "ALL")
      .order("as_of_date", { ascending: false })
      .limit(1)
      .maybeSingle();
    const row = data as { t5_win_rate?: number; t5_total_calls?: number } | null;
    if (row?.t5_win_rate != null) winRate = row.t5_win_rate;
    if (row?.t5_total_calls != null) sampleSize = row.t5_total_calls;
  }

  const wrStr = winRate != null ? `${(winRate * 100).toFixed(1)}%` : "—";
  const ssStr = sampleSize != null ? `${sampleSize.toLocaleString()}` : "—";

  return new ImageResponse(
    <div
      style={{
        width: size.width,
        height: size.height,
        background: "#000000",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: 48,
        color: "#ffffff",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            letterSpacing: -2,
            lineHeight: 1,
          }}
        >
          Performance
        </div>
        <div
          style={{
            fontSize: 38,
            color: "#a3a3a3",
            maxWidth: 1000,
            lineHeight: 1.2,
          }}
        >
          Track record & validation metrics
        </div>
        <div style={{ display: "flex", gap: 40, marginTop: 16 }}>
          <div>
            <div style={{ fontSize: 52, fontWeight: 700, color: "#10b981" }}>
              {wrStr}
            </div>
            <div style={{ fontSize: 22, color: "#666666", letterSpacing: "0.2em", textTransform: "uppercase" }}>
              T+5 Win Rate
            </div>
          </div>
          <div>
            <div style={{ fontSize: 52, fontWeight: 700, color: "#10b981" }}>
              {ssStr}
            </div>
            <div style={{ fontSize: 22, color: "#666666", letterSpacing: "0.2em", textTransform: "uppercase" }}>
              Validated Calls
            </div>
          </div>
        </div>
      </div>
      <div
        style={{
          fontSize: 24,
          color: "#666666",
          letterSpacing: "0.35em",
          textTransform: "uppercase",
        }}
      >
        FX Regime Lab
      </div>
    </div>,
    { ...size },
  );
}
