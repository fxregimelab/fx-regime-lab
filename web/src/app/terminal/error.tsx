"use client";

import { useEffect } from "react";

type ErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function TerminalError({ error, reset }: ErrorProps) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("Terminal route error:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[var(--color-void)] text-[var(--color-text)] flex items-center justify-center px-6">
      <div className="w-full max-w-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <p className="font-mono text-[12px] tracking-widest text-[var(--color-brand-amber)]">
          [ DATA OFFLINE ]
        </p>
        <p className="font-mono text-[11px] text-[var(--color-text-secondary)] mt-2 break-all">
          {error.message || "Terminal route failure"}
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="mt-4 border border-[var(--color-border-bright)] bg-[var(--color-void)] px-3 py-2 font-mono text-[10px] text-[var(--color-text-muted)] tracking-widest hover:text-[var(--color-text)]"
        >
          [ RETRY ]
        </button>
      </div>
    </div>
  );
}
