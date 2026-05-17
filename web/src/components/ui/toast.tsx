"use client";

import { X } from "lucide-react";
import type { ToastType } from "./toast-context";

interface ToastProps {
  id: string;
  message: string;
  type: ToastType;
  onDismiss: (id: string) => void;
}

function toastBorder(type: ToastType): string {
  switch (type) {
    case "success":
      return "border-[var(--terminal-success)]";
    case "error":
      return "border-[var(--terminal-danger)]";
    case "warning":
      return "border-[var(--terminal-warning)]";
    default:
      return "border-[var(--terminal-border-bright)]";
  }
}

function toastIcon(type: ToastType): string {
  switch (type) {
    case "success":
      return "✓";
    case "error":
      return "✕";
    case "warning":
      return "!";
    default:
      return "›";
  }
}

export function ToastItem({ id, message, type, onDismiss }: ToastProps) {
  return (
    <div
      role="alert"
      className={`flex items-center gap-3 border ${toastBorder(type)} bg-[var(--terminal-bg-elevated)] px-4 py-3 shadow-lg pointer-events-auto`}
      style={{ borderRadius: 2 }}
    >
      <span
        className="flex-shrink-0 font-mono text-[10px]"
        style={{
          color:
            type === "success"
              ? "var(--terminal-success)"
              : type === "error"
                ? "var(--terminal-danger)"
                : type === "warning"
                  ? "var(--terminal-warning)"
                  : "var(--terminal-fg-muted)",
        }}
      >
        {toastIcon(type)}
      </span>
      <p className="flex-1 font-mono text-[11px] text-[var(--terminal-fg)] leading-snug">
        {message}
      </p>
      <button
        type="button"
        onClick={() => onDismiss(id)}
        className="flex-shrink-0 text-[var(--terminal-fg-dim)] hover:text-[var(--terminal-fg)] transition-colors"
        aria-label="Dismiss notification"
      >
        <X size={12} />
      </button>
    </div>
  );
}
