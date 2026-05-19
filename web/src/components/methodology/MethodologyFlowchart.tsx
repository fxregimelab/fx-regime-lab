"use client";

import { useState } from "react";

interface FlowNode {
  id: string;
  label: string;
  sublabel?: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  detail?: string;
}

interface FlowEdge {
  from: string;
  to: string;
  label?: string;
}

const NODES: FlowNode[] = [
  {
    id: "raw",
    label: "RAW DATA",
    sublabel: "FRED · CFTC · Alpha Vantage",
    x: 60,
    y: 20,
    width: 140,
    height: 50,
    color: "#555",
    detail:
      "Daily ingestion of yield curves, COT positioning, FX spot, implied vol, and macro calendar. Explicit fallback chain; no interpolation.",
  },
  {
    id: "signals",
    label: "SIGNAL ENGINE",
    sublabel: "z-scores · percentiles · ranks",
    x: 260,
    y: 20,
    width: 140,
    height: 50,
    color: "#6b7280",
    detail:
      "Each input is scored against causal windows only (t−1 lookback). Rate z-score, COT percentile, vol rank, OI delta, and special signals.",
  },
  {
    id: "gate",
    label: "REGIME GATE",
    sublabel: "Overrides · hysteresis",
    x: 460,
    y: 20,
    width: 140,
    height: 50,
    color: "#7c3aed",
    detail:
      "Layer 1: Policy-breakout, liquidity-shock, and carry-collapse overrides. Composite snap function with 5 tiers and memory of prior day.",
  },
  {
    id: "composite",
    label: "COMPOSITE",
    sublabel: "S ∈ [−2, 2]",
    x: 660,
    y: 20,
    width: 120,
    height: 50,
    color: "#2563eb",
    detail:
      "Weighted sum of signal families (rate 30–45%, COT 10–25%, vol 20%, special 5–20%). Adaptive precision weighting + redundancy penalty.",
  },
  {
    id: "bias",
    label: "DIRECTIONAL BIAS",
    sublabel: "LONG · SHORT · NEUTRAL",
    x: 660,
    y: 110,
    width: 140,
    height: 50,
    color: "#059669",
    detail:
      "Layer 2: Composite magnitude drives bias. Marcus B (rate vs COT clash) and Marcus C (composite vs rate clash) vetoes force NEUTRAL.",
  },
  {
    id: "conviction",
    label: "CONVICTION",
    sublabel: "1–5 score",
    x: 660,
    y: 200,
    width: 120,
    height: 50,
    color: "#0891b2",
    detail:
      "Scaled by positioning multiplier m_π, crowding penalty, and alignment bonus. Hard-capped at 3 when vetoes fire.",
  },
  {
    id: "execution",
    label: "EXECUTION",
    sublabel: "Timing · Size · Stop",
    x: 460,
    y: 200,
    width: 140,
    height: 50,
    color: "#d97706",
    detail:
      "Layer 3: ENTER/WAIT from vol rank and skew alignment. FULL/HALF from conviction + vol gate. Stop = max(1.5·ADR₂₀, MIE_proxy).",
  },
  {
    id: "validation",
    label: "VALIDATION",
    sublabel: "T+5 · T+20 · Brier",
    x: 260,
    y: 200,
    width: 140,
    height: 50,
    color: "#dc2626",
    detail:
      "Out-of-sample at two horizons. Directional correctness only (excludes neutral). Append-only ledger; never mutated.",
  },
  {
    id: "feedback",
    label: "CALIBRATION",
    sublabel: "Platt scaling · accuracy gates",
    x: 60,
    y: 200,
    width: 140,
    height: 50,
    color: "#991b1b",
    detail:
      "Rolling accuracy monitoring per pair. Platt-scaled confidence. Alerts when accuracy falls below pair-specific gate thresholds.",
  },
];

const NODE_MAP = new Map(NODES.map((n) => [n.id, n]));

const EDGES: FlowEdge[] = [
  { from: "raw", to: "signals", label: "ingest" },
  { from: "signals", to: "gate", label: "score" },
  { from: "gate", to: "composite", label: "snap" },
  { from: "composite", to: "bias", label: "|S| > 0.30" },
  { from: "bias", to: "conviction", label: "m_π" },
  { from: "conviction", to: "execution", label: "size" },
  { from: "execution", to: "validation", label: "log" },
  { from: "validation", to: "feedback", label: "score" },
  { from: "feedback", to: "raw", label: "audit" },
];

export default function MethodologyFlowchart() {
  const [activeNode, setActiveNode] = useState<string | null>(null);

  const active = activeNode ? NODE_MAP.get(activeNode) : undefined;

  return (
    <div className="mb-10 border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      <div className="px-5 py-3 border-b border-[var(--color-border)]">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Pipeline Architecture
        </p>
      </div>

      <div className="p-5 md:p-6">
        <svg
          viewBox="0 0 840 280"
          className="w-full h-auto max-h-[320px]"
          role="img"
          aria-label="FX Regime Lab pipeline flowchart"
        >
          <title>Pipeline Flowchart</title>
          <rect width="840" height="280" fill="var(--color-void)" />

          {/* Edges */}
          {EDGES.map((edge) => {
            const from = NODE_MAP.get(edge.from);
            const to = NODE_MAP.get(edge.to);
            if (!from || !to) return null;

            const x1 = from.x + from.width / 2;
            const y1 = from.y + from.height / 2;
            const x2 = to.x + to.width / 2;
            const y2 = to.y + to.height / 2;

            // Adjust endpoints to edge of boxes
            const dx = x2 - x1;
            const dy = y2 - y1;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const nx = dx / dist;
            const ny = dy / dist;

            const startX = x1 + nx * (from.width / 2 + 4);
            const startY = y1 + ny * (from.height / 2 + 4);
            const endX = x2 - nx * (to.width / 2 + 6);
            const endY = y2 - ny * (to.height / 2 + 6);

            // Arrowhead
            const arrowSize = 5;
            const ax1 = endX - arrowSize * nx + arrowSize * ny * 0.5;
            const ay1 = endY - arrowSize * ny - arrowSize * nx * 0.5;
            const ax2 = endX - arrowSize * nx - arrowSize * ny * 0.5;
            const ay2 = endY - arrowSize * ny + arrowSize * nx * 0.5;

            const isActive = activeNode === edge.from || activeNode === edge.to;

            return (
              <g key={`${edge.from}-${edge.to}`}>
                <line
                  x1={startX}
                  y1={startY}
                  x2={endX}
                  y2={endY}
                  stroke={
                    isActive ? "var(--color-text)" : "var(--color-border)"
                  }
                  strokeWidth={isActive ? 2 : 1}
                  opacity={isActive ? 1 : 0.6}
                />
                <polygon
                  points={`${endX},${endY} ${ax1},${ay1} ${ax2},${ay2}`}
                  fill={isActive ? "var(--color-text)" : "var(--color-border)"}
                  opacity={isActive ? 1 : 0.6}
                />
              </g>
            );
          })}

          {/* Nodes */}
          {NODES.map((node) => {
            const isActive = activeNode === node.id;
            const rx = isActive ? 3 : 2;
            return (
              <g key={node.id}>
                <rect
                  x={node.x - node.width / 2}
                  y={node.y - node.height / 2}
                  width={node.width}
                  height={node.height}
                  rx={rx}
                  fill={isActive ? `${node.color}22` : "var(--color-elevated)"}
                  stroke={isActive ? node.color : "var(--color-border)"}
                  strokeWidth={isActive ? 2 : 1}
                  className="cursor-pointer"
                  onMouseEnter={() => setActiveNode(node.id)}
                  onMouseLeave={() => setActiveNode(null)}
                />
                <text
                  x={node.x}
                  y={node.y - 4}
                  textAnchor="middle"
                  fill={
                    isActive
                      ? "var(--color-text)"
                      : "var(--color-text-secondary)"
                  }
                  fontSize={11}
                  fontFamily="JetBrains Mono, monospace"
                  fontWeight={600}
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {node.label}
                </text>
                {node.sublabel && (
                  <text
                    x={node.x}
                    y={node.y + 12}
                    textAnchor="middle"
                    fill="var(--color-text-muted)"
                    fontSize={8}
                    fontFamily="JetBrains Mono, monospace"
                    style={{ fontVariantNumeric: "tabular-nums" }}
                  >
                    {node.sublabel}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* Detail panel */}
        <div className="mt-4 min-h-[3rem]">
          {active ? (
            <div className="border border-[var(--color-border)] bg-[var(--color-elevated)] px-4 py-3">
              <p
                className="font-mono text-[10px] tracking-[0.15em] uppercase mb-1"
                style={{ color: active.color }}
              >
                {active.label}
              </p>
              <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
                {active.detail}
              </p>
            </div>
          ) : (
            <p className="font-mono text-[10px] text-[var(--color-text-dim)] tracking-wider text-center py-2">
              HOVER OR CLICK A NODE FOR DETAILS
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
