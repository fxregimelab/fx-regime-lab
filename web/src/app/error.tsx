"use client";

import { useEffect } from "react";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App-level Error caught:", error);
  }, [error]);

  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-[var(--terminal-bg)] p-6 font-mono shadow-none">
      <div className="border border-[var(--terminal-border)] bg-[var(--terminal-bg-sunken)] p-8 text-center shadow-none">
        <p className="mb-4 text-[10px] tracking-widest text-[var(--terminal-warning)] shadow-none">
          [ RENDER EXCEPTION ]
        </p>
        <h2 className="mb-4 text-xl font-light text-[var(--terminal-fg)] shadow-none">
          Component Failure Detected
        </h2>
        <p className="mb-8 text-[11px] text-[var(--terminal-fg-dim)] shadow-none">
          {error.message || "The terminal module failed to render correctly."}
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="border border-[var(--terminal-border-bright)] bg-transparent px-4 py-2 text-[10px] tracking-widest text-[var(--terminal-fg-muted)] transition-colors hover:bg-[var(--terminal-bg-elevated)] shadow-none"
        >
          [ RETRY MODULE ]
        </button>
      </div>
    </div>
  );
}
