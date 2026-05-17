"use client";

type ErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function TerminalError({ error, reset }: ErrorProps) {
  return (
    <div className="min-h-screen bg-[var(--terminal-bg)] text-[var(--terminal-fg)] flex items-center justify-center px-6">
      <div className="w-full max-w-2xl border border-[var(--terminal-border)] bg-[var(--terminal-bg)] p-6">
        <p className="font-mono text-[12px] tracking-widest text-[var(--terminal-warning)]">
          [ DATA OFFLINE ]
        </p>
        <p className="font-mono text-[11px] text-[var(--terminal-fg-dim)] mt-2 break-all">
          {error.message || "Terminal route failure"}
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="mt-4 border border-[var(--terminal-border-bright)] bg-[var(--terminal-bg)] px-3 py-2 font-mono text-[10px] text-[var(--terminal-fg-muted)] tracking-widest hover:text-[var(--terminal-fg)]"
        >
          [ RETRY TERMINAL ]
        </button>
      </div>
    </div>
  );
}
