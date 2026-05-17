"use client";

import { useEffect } from "react";

interface KeyboardHelpProps {
  open: boolean;
  onClose: () => void;
}

const SHORTCUTS = [
  { key: "j", desc: "Scroll down" },
  { key: "k", desc: "Scroll up" },
  { key: "g", desc: "Goto pair (command palette)" },
  { key: "/", desc: "Search (command palette)" },
  { key: "?", desc: "Show this help" },
  { key: "r", desc: "Refresh data" },
  { key: "1", desc: "EUR/USD desk" },
  { key: "2", desc: "USD/JPY desk" },
  { key: "3", desc: "USD/INR desk" },
  { key: "Esc", desc: "Close overlay / dialog" },
  { key: "⌘K", desc: "Command palette" },
];

/**
 * Keyboard shortcuts help overlay — triggered by ? key on terminal pages.
 */
export function KeyboardHelp({ open, onClose }: KeyboardHelpProps) {
  useEffect(() => {
    if (!open) return;
    const down = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <dialog
      className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center bg-transparent p-0 open:flex"
      aria-label="Keyboard shortcuts"
      open
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Enter" && onClose()}
        role="button"
        tabIndex={0}
        aria-label="Close"
      />

      {/* Modal */}
      <div
        className="relative w-full max-w-sm border border-[var(--terminal-border)] bg-[var(--terminal-bg-elevated)] p-5"
        role="document"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-mono text-[11px] tracking-[0.2em] text-[var(--terminal-fg-muted)] uppercase">
            Keyboard Shortcuts
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="font-mono text-[9px] text-[var(--terminal-fg-dim)] hover:text-[var(--terminal-fg)] cursor-pointer"
          >
            [ESC]
          </button>
        </div>

        <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
          {SHORTCUTS.map(({ key, desc }) => (
            <div key={key} className="contents">
              <kbd className="font-mono text-[10px] border border-[var(--terminal-border)] bg-[var(--terminal-bg-sunken)] px-1.5 py-0.5 text-[var(--terminal-fg-muted)] text-center min-w-[24px]">
                {key}
              </kbd>
              <span className="font-mono text-[10px] text-[var(--terminal-fg-dim)]">
                {desc}
              </span>
            </div>
          ))}
        </div>

        <p className="mt-4 font-mono text-[9px] text-[var(--terminal-fg-dim)] tracking-wider">
          Shortcuts active on terminal pages only. Disabled while typing in
          inputs.
        </p>
      </div>
    </dialog>
  );
}
