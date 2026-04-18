'use client';

export default function TerminalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-lg bg-terminal-bg px-4 py-16 font-mono text-sm text-neutral-200">
      <h2 className="text-base font-semibold text-neutral-100">Terminal error</h2>
      <p className="mt-3 text-neutral-400">{error.message}</p>
      <button
        type="button"
        onClick={() => reset()}
        className="mt-6 rounded-md border border-neutral-700 bg-terminal-surface px-4 py-2 text-neutral-100 hover:border-accent"
      >
        Retry
      </button>
    </div>
  );
}
