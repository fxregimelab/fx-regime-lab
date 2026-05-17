"use client";

import { X } from "lucide-react";
import { useEffect } from "react";

interface InspectorDrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

/** Side drawer on desktop, bottom sheet on mobile.
 *  Uses terminal design tokens, max 2px radius.
 */
export function InspectorDrawer({
  open,
  onClose,
  title,
  children,
}: InspectorDrawerProps) {
  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // Close on Escape
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
      className="fixed inset-0 z-[var(--z-modal)] bg-transparent p-0 open:flex"
      aria-modal="true"
      open
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Enter" && onClose()}
        role="button"
        tabIndex={-1}
        aria-hidden="true"
      />

      {/* Drawer: right side on md+, bottom on mobile */}
      <div
        className="absolute top-0 right-0 bottom-0 w-full md:w-[480px] max-w-full bg-[var(--terminal-bg)] border-l-0 md:border-l border-t border-t-[var(--terminal-border)] md:border-t-0 border-[var(--terminal-border)] flex flex-col shadow-xl"
        style={{ borderRadius: 0 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--terminal-border-subtle)] shrink-0">
          <p className="font-mono text-[10px] tracking-widest text-[var(--terminal-fg-muted)] uppercase">
            {title}
          </p>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--terminal-fg-dim)] hover:text-[var(--terminal-fg)] transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Close inspector"
          >
            <X size={14} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4 terminal-scroll">
          {children}
        </div>
      </div>
    </dialog>
  );
}
