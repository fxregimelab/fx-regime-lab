"use client";

type ErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function PairDeskError({ error, reset }: ErrorProps) {
  return (
    <div className="min-h-screen bg-[var(--color-void)] text-[var(--color-text)] flex items-center justify-center px-6">
      <div className="w-full max-w-2xl border border-[var(--color-border)] bg-[var(--color-void)] p-6">
        <p className="font-mono text-[12px] tracking-widest text-[var(--color-warn)]">
          [ PAIR DESK OFFLINE ]
        </p>
        <p className="font-mono text-[11px] text-[var(--color-text-dim)] mt-2 break-all">
          {error.message || "Pair desk route failure"}
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="mt-4 border border-[var(--color-border)] bg-[var(--color-void)] px-3 py-2 font-mono text-[10px] text-[var(--color-text-muted)] tracking-widest hover:text-[var(--color-text)]"
        >
          [ RETRY ]
        </button>
      </div>
    </div>
  );
}
