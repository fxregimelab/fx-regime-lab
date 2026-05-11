"use client";

import type React from "react";
import { TerminalLabel } from "./TerminalLabel";

interface SystemicClusterBannerProps {
  label?: string;
  detail?: string;
}

export const SystemicClusterBanner: React.FC<SystemicClusterBannerProps> = ({
  label = "SYSTEMIC CLUSTER FLAG",
  detail,
}) => {
  return (
    <div
      role="alert"
      style={{
        background: "rgba(245, 158, 11, 0.08)",
        border: "1px solid var(--terminal-warning, #f59e0b)",
        borderRadius: "var(--radius-2, 2px)",
        padding: "var(--space-3, 0.75rem) var(--space-4, 1rem)",
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3, 0.75rem)",
      }}
    >
      <span
        style={{
          display: "inline-block",
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "var(--terminal-warning, #f59e0b)",
          animation: "gentle-pulse 2s ease-in-out infinite",
          flexShrink: 0,
        }}
      />
      <div>
        <TerminalLabel limit={30} prefix="⚠ ">
          {label}
        </TerminalLabel>
        {detail && (
          <p
            style={{
              margin: "var(--space-1, 0.25rem) 0 0",
              fontSize: "var(--text-xs, 0.6875rem)",
              color: "var(--terminal-fg-muted, #a8a29e)",
              lineHeight: 1.4,
            }}
          >
            {detail}
          </p>
        )}
      </div>
    </div>
  );
};

export default SystemicClusterBanner;
