import { ImageResponse } from "next/og";
import { createClient } from "@/lib/supabase/server";

export const alt = "Research Memos | FX Regime Lab";
export const size = { width: 1200, height: 630 };
export const runtime = "edge";
export const contentType = "image/png";

export default async function Image() {
  let latestTitle: string | null = null;
  let latestDate: string | null = null;

  try {
    const supabase = await createClient();
    const { data } = await supabase
      .from("research_memos")
      .select("title, date")
      .order("date", { ascending: false })
      .limit(1)
      .maybeSingle();

    const row = data as { title: string; date: string } | null;
    if (row) {
      latestTitle = row.title;
      latestDate = row.date;
    }
  } catch {
    // Fallback
  }

  return new ImageResponse(
    (
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
              fontSize: 24,
              color: "#525252",
              letterSpacing: "0.2em",
              textTransform: "uppercase",
            }}
          >
            FX Regime Lab
          </div>
          <div
            style={{
              fontSize: 56,
              fontWeight: 700,
              letterSpacing: -1,
              lineHeight: 1.1,
              color: "#ffffff",
            }}
          >
            Research Memos
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 12,
              marginTop: 32,
            }}
          >
            <div
              style={{
                fontSize: 20,
                color: "#525252",
                letterSpacing: "0.15em",
                textTransform: "uppercase",
              }}
            >
              Latest Memo
            </div>
            <div
              style={{
                fontSize: 32,
                color: "#d4d4d4",
                lineHeight: 1.3,
                maxWidth: 1000,
              }}
            >
              {latestTitle ?? "—"}
            </div>
            {latestDate && (
              <div
                style={{
                  fontSize: 22,
                  color: "#737373",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {latestDate}
              </div>
            )}
          </div>
        </div>
        <div
          style={{
            fontSize: 20,
            color: "#404040",
            letterSpacing: "0.15em",
            textTransform: "uppercase",
          }}
        >
          Weekly Macro Research Archive
        </div>
      </div>
    ),
    { ...size },
  );
}
