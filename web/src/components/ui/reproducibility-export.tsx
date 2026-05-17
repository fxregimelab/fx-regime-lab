"use client";

import { useToast } from "@/components/ui/toast-context";
import { useCallback } from "react";

export interface ReproducibilityPayload {
  query: string;
  parameters: Record<string, unknown>;
  timestamp: string;
  dataVersion?: string;
  sourceTable?: string;
}

interface ReproducibilityExportProps {
  payload: ReproducibilityPayload;
  label?: string;
  variant?: "icon" | "text";
}

/** Small reproduce button that exports query provenance as JSON.
 *  Copies to clipboard; shows toast confirmation.
 */
export function ReproducibilityExport({
  payload,
  label = "REPRODUCE",
  variant = "icon",
}: ReproducibilityExportProps) {
  const { addToast } = useToast();

  const handleCopy = useCallback(() => {
    const json = JSON.stringify(
      {
        ...payload,
        exportedAt: new Date().toISOString(),
        platform: "FX Regime Lab",
      },
      null,
      2,
    );

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(json).then(() => {
        addToast("Query parameters copied to clipboard", "success");
      });
    } else {
      // Fallback: create temporary textarea
      const ta = document.createElement("textarea");
      ta.value = json;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      addToast("Query parameters copied to clipboard", "success");
    }
  }, [payload, addToast]);

  const handleDownload = useCallback(() => {
    const json = JSON.stringify(
      {
        ...payload,
        exportedAt: new Date().toISOString(),
        platform: "FX Regime Lab",
      },
      null,
      2,
    );
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fxrl-reproduce-${payload.timestamp.slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    addToast("Reproducibility bundle downloaded", "success");
  }, [payload, addToast]);

  if (variant === "icon") {
    return (
      <span className="inline-flex items-center gap-1">
        <button
          type="button"
          onClick={handleCopy}
          className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] hover:text-[var(--terminal-fg-muted)] transition-colors"
          aria-label="Copy reproducibility parameters"
          title="Copy reproducibility parameters"
        >
          [↗]
        </button>
        <button
          type="button"
          onClick={handleDownload}
          className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] hover:text-[var(--terminal-fg-muted)] transition-colors"
          aria-label="Download reproducibility JSON"
          title="Download reproducibility JSON"
        >
          [↓]
        </button>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={handleCopy}
        className="border border-[var(--terminal-border-bright)] bg-transparent px-2 py-1 font-mono text-[9px] tracking-widest text-[var(--terminal-fg-muted)] hover:text-[var(--terminal-fg)] hover:border-[var(--terminal-fg)] transition-colors"
        style={{ borderRadius: 2 }}
      >
        {label}
      </button>
      <button
        type="button"
        onClick={handleDownload}
        className="border border-[var(--terminal-border-bright)] bg-transparent px-2 py-1 font-mono text-[9px] tracking-widest text-[var(--terminal-fg-muted)] hover:text-[var(--terminal-fg)] hover:border-[var(--terminal-fg)] transition-colors"
        style={{ borderRadius: 2 }}
      >
        JSON
      </button>
    </span>
  );
}
