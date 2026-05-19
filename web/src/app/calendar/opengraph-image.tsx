import { ImageResponse } from "next/og";

export const alt = "Calendar | FX Regime Lab";
export const size = { width: 1200, height: 630 };
export const runtime = "edge";
export const contentType = "image/png";

export default function Image() {
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
        border: "4px solid #e8a045",
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
            fontSize: 72,
            fontWeight: 700,
            letterSpacing: -2,
            lineHeight: 1,
            color: "#ffffff",
          }}
        >
          Calendar
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
        Macro Event Risk Tracker
      </div>
    </div>,
    { ...size },
  );
}
