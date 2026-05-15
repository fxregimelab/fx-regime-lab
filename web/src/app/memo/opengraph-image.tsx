import { createClient } from "@supabase/supabase-js";
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "FX Regime Lab — Research Memos";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  let title = "Weekly macro research memos";

  if (url && anon) {
    const supabase = createClient(url, anon);
    const { data } = await supabase
      .from("research_memos")
      .select("title")
      .order("date", { ascending: false })
      .limit(1)
      .maybeSingle();
    const row = data as { title?: string } | null;
    if (row?.title) title = row.title;
  }

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
          Research Memos
        </div>
        <div
          style={{
            fontSize: 32,
            color: "#a3a3a3",
            maxWidth: 1000,
            lineHeight: 1.3,
          }}
        >
          {title}
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
