"use client";

import { useCallback, useMemo, useState } from "react";

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
    x: 130,
    y: 55,
    width: 140,
    height: 50,
    color: "#888888",
    detail:
      "Daily ingestion of yield curves, COT positioning, FX spot, implied vol, and macro calendar. Explicit fallback chain; no interpolation.",
  },
  {
    id: "signals",
    label: "SIGNAL ENGINE",
    sublabel: "z-scores · percentiles · ranks",
    x: 330,
    y: 55,
    width: 140,
    height: 50,
    color: "#9ca3af",
    detail:
      "Each input is scored against causal windows only (t−1 lookback). Rate z-score, COT percentile, vol rank, OI delta, and special signals.",
  },
  {
    id: "gate",
    label: "REGIME GATE",
    sublabel: "Overrides · hysteresis",
    x: 530,
    y: 55,
    width: 140,
    height: 50,
    color: "#a78bfa",
    detail:
      "Layer 1: Policy-breakout, liquidity-shock, and carry-collapse overrides. Composite snap function with 5 tiers and memory of prior day.",
  },
  {
    id: "composite",
    label: "COMPOSITE",
    sublabel: "S ∈ [−2, 2]",
    x: 730,
    y: 55,
    width: 140,
    height: 50,
    color: "#60a5fa",
    detail:
      "Weighted sum of signal families (rate 30–45%, COT 10–25%, vol 20%, special 5–20%). Adaptive precision weighting + redundancy penalty.",
  },
  {
    id: "bias",
    label: "DIRECTIONAL BIAS",
    sublabel: "LONG · SHORT · NEUTRAL",
    x: 730,
    y: 145,
    width: 140,
    height: 50,
    color: "#34d399",
    detail:
      "Layer 2: Composite magnitude drives bias. Marcus B (rate vs COT clash) and Marcus C (composite vs rate clash) vetoes force NEUTRAL.",
  },
  {
    id: "conviction",
    label: "CONVICTION",
    sublabel: "0.0–1.0 probability",
    x: 730,
    y: 235,
    width: 140,
    height: 50,
    color: "#22d3ee",
    detail:
      "Scaled by positioning multiplier m_π, crowding penalty, and alignment bonus. Hard-capped at 0.50 when vetoes fire.",
  },
  {
    id: "output",
    label: "REGIME OUTPUT",
    sublabel: "Classification + Confidence",
    x: 530,
    y: 235,
    width: 140,
    height: 50,
    color: "#fbbf24",
    detail:
      "Final regime classification output with directional bias and calibrated confidence. This is research output — not a trading signal. No positions are executed.",
  },
  {
    id: "validation",
    label: "VALIDATION",
    sublabel: "T+5 · T+20 · Brier",
    x: 330,
    y: 235,
    width: 140,
    height: 50,
    color: "#f87171",
    detail:
      "Out-of-sample at two horizons. Directional correctness only (excludes neutral). Append-only ledger; never mutated.",
  },
  {
    id: "feedback",
    label: "CALIBRATION",
    sublabel: "Platt scaling · accuracy gates",
    x: 130,
    y: 235,
    width: 140,
    height: 50,
    color: "#b91c1c",
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
  { from: "conviction", to: "output", label: "classify" },
  { from: "output", to: "validation", label: "log" },
  { from: "validation", to: "feedback", label: "score" },
  { from: "feedback", to: "raw", label: "audit" },
];

/* ── geometry helpers ──────────────────────────────────────────────── */

function getEdgeGeometry(from: FlowNode, to: FlowNode) {
  const x1 = from.x;
  const y1 = from.y;
  const x2 = to.x;
  const y2 = to.y;

  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const nx = dx / dist;
  const ny = dy / dist;

  const startX = x1 + nx * (from.width / 2 + 6);
  const startY = y1 + ny * (from.height / 2 + 6);
  const endX = x2 - nx * (to.width / 2 + 10);
  const endY = y2 - ny * (to.height / 2 + 10);

  const midX = (startX + endX) / 2;
  const midY = (startY + endY) / 2;

  // Offset label perpendicular to edge direction
  const perpX = -ny * 10;
  const perpY = nx * 10;

  return { startX, startY, endX, endY, midX, midY, perpX, perpY, nx, ny };
}

/* ── lock icon SVG ─────────────────────────────────────────────────── */

function LockIcon({ color }: { color: string }) {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <title>Locked</title>
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

/* ── component ─────────────────────────────────────────────────────── */

export default function MethodologyFlowchart() {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [lockedNode, setLockedNode] = useState<string | null>(null);

  const activeNodeId = lockedNode || hoveredNode;
  const active = activeNodeId ? NODE_MAP.get(activeNodeId) : undefined;
  const isLocked = lockedNode != null;

  const toggleLock = useCallback((id: string) => {
    setLockedNode((prev) => (prev === id ? null : id));
  }, []);

  const handleNodeClick = useCallback(
    (id: string) => {
      toggleLock(id);
    },
    [toggleLock],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, id: string) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggleLock(id);
      }
    },
    [toggleLock],
  );

  const activeConnections = useMemo(() => {
    if (!activeNodeId) return new Set<string>();
    const connected = new Set<string>();
    for (const edge of EDGES) {
      if (edge.from === activeNodeId || edge.to === activeNodeId) {
        connected.add(`${edge.from}-${edge.to}`);
      }
    }
    return connected;
  }, [activeNodeId]);

  return (
    <div className="mb-10 border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden">
      <div className="px-5 py-3 border-b border-[var(--color-border)]">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Pipeline Architecture
        </p>
      </div>

      <div className="p-5 md:p-6">
        <style>{`
          .flow-node {
            transition: transform 250ms ease, filter 250ms ease;
            cursor: pointer;
            outline: none;
          }
          .flow-node:focus {
            outline: 2px solid var(--color-text-muted);
            outline-offset: 2px;
          }
          .flow-edge {
            transition: stroke-width 250ms ease, opacity 250ms ease, stroke 250ms ease;
          }
          .flow-edge-label {
            transition: opacity 250ms ease;
          }
          .lock-pulse {
            animation: lockPulse 2s ease-in-out infinite;
          }
          @keyframes lockPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }
        `}</style>

        <svg
          viewBox="0 0 920 340"
          className="w-full h-auto max-h-[380px]"
          role="img"
          aria-label="FX Regime Lab pipeline flowchart"
        >
          <title>Pipeline Flowchart</title>

          {/* Background */}
          <rect width="920" height="340" fill="var(--color-void)" rx="2" />

          {/* Markers */}
          <defs>
            <marker
              id="arrow-default"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="var(--color-border)" />
            </marker>
            <marker
              id="arrow-active"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="var(--color-text)" />
            </marker>
          </defs>

          {/* Edges */}
          {EDGES.map((edge) => {
            const from = NODE_MAP.get(edge.from);
            const to = NODE_MAP.get(edge.to);
            if (!from || !to) return null;

            const { startX, startY, endX, endY, midX, midY, perpX, perpY } =
              getEdgeGeometry(from, to);

            const isConnected = activeConnections.has(
              `${edge.from}-${edge.to}`,
            );
            const isActive = isConnected && activeNodeId != null;

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
                  strokeWidth={isActive ? 2.5 : 1}
                  opacity={
                    activeNodeId && !isActive ? 0.25 : isActive ? 1 : 0.6
                  }
                  className="flow-edge"
                  markerEnd={
                    isActive ? "url(#arrow-active)" : "url(#arrow-default)"
                  }
                />
                {edge.label && (
                  <g className="flow-edge-label" opacity={isActive ? 1 : 0.55}>
                    <rect
                      x={midX + perpX - 22}
                      y={midY + perpY - 8}
                      width={44}
                      height={16}
                      rx="3"
                      fill="var(--color-void)"
                    />
                    <text
                      x={midX + perpX}
                      y={midY + perpY + 3}
                      textAnchor="middle"
                      fill={
                        isActive
                          ? "var(--color-text)"
                          : "var(--color-text-muted)"
                      }
                      fontSize={8}
                      fontFamily="JetBrains Mono, monospace"
                      style={{ fontVariantNumeric: "tabular-nums" }}
                    >
                      {edge.label}
                    </text>
                  </g>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {NODES.map((node) => {
            const isNodeActive = activeNodeId === node.id;
            const isNodeLocked = lockedNode === node.id;
            const cx = node.x - node.width / 2;
            const cy = node.y - node.height / 2;

            return (
              <g
                key={node.id}
                className="flow-node"
                style={{
                  transformOrigin: `${node.x}px ${node.y}px`,
                  transform: isNodeActive ? "scale(1.03)" : "scale(1)",
                  filter: isNodeActive
                    ? `drop-shadow(0 0 ${isNodeLocked ? 16 : 12}px ${node.color}55)`
                    : "none",
                }}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => handleNodeClick(node.id)}
                onKeyDown={(e) => handleKeyDown(e, node.id)}
                tabIndex={0}
                aria-pressed={isNodeLocked}
                aria-label={`${node.label}${node.sublabel ? ` — ${node.sublabel}` : ""}`}
              >
                {/* Node body */}
                <rect
                  x={cx}
                  y={cy}
                  width={node.width}
                  height={node.height}
                  rx={isNodeActive ? 4 : 2}
                  fill={
                    isNodeActive ? `${node.color}18` : "var(--color-elevated)"
                  }
                  stroke={isNodeActive ? node.color : "var(--color-border)"}
                  strokeWidth={isNodeActive ? 2 : 1}
                />

                {/* Locked indicator — pulsing border */}
                {isNodeLocked && (
                  <rect
                    x={cx - 2}
                    y={cy - 2}
                    width={node.width + 4}
                    height={node.height + 4}
                    rx={6}
                    fill="none"
                    stroke={node.color}
                    strokeWidth={1.5}
                    strokeDasharray="4 3"
                    className="lock-pulse"
                    opacity={0.8}
                  />
                )}

                {/* Label */}
                <text
                  x={node.x}
                  y={node.y - 5}
                  textAnchor="middle"
                  fill={
                    isNodeActive
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

                {/* Sublabel */}
                {node.sublabel && (
                  <text
                    x={node.x}
                    y={node.y + 11}
                    textAnchor="middle"
                    fill="var(--color-text-muted)"
                    fontSize={8}
                    fontFamily="JetBrains Mono, monospace"
                    style={{ fontVariantNumeric: "tabular-nums" }}
                  >
                    {node.sublabel}
                  </text>
                )}

                {/* Lock icon */}
                {isNodeLocked && (
                  <g
                    transform={`translate(${cx + node.width - 14}, ${cy + 4})`}
                  >
                    <LockIcon color={node.color} />
                  </g>
                )}
              </g>
            );
          })}
        </svg>

        {/* Detail panel */}
        <div className="mt-4 min-h-[3.5rem]">
          {active ? (
            <div
              className="border px-4 py-3 relative"
              style={{
                borderColor: isLocked
                  ? `${active.color}66`
                  : "var(--color-border)",
                backgroundColor: isLocked
                  ? `${active.color}08`
                  : "var(--color-elevated)",
              }}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <p
                  className="font-mono text-[10px] tracking-[0.15em] uppercase"
                  style={{ color: active.color }}
                >
                  {active.label}
                </p>
                {isLocked && (
                  <span
                    className="inline-flex items-center gap-1 font-mono text-[9px] tracking-wider px-1.5 py-0.5 border rounded-sm"
                    style={{
                      borderColor: `${active.color}44`,
                      color: active.color,
                    }}
                  >
                    <LockIcon color={active.color} />
                    LOCKED
                  </span>
                )}
              </div>
              <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
                {active.detail}
              </p>
            </div>
          ) : (
            <p className="font-mono text-[10px] text-[var(--color-text-dim)] tracking-wider text-center py-2.5">
              HOVER OR CLICK A NODE FOR DETAILS
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
