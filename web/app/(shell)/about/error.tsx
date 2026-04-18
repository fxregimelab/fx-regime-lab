'use client';

export default function AboutError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-3xl bg-shell-bg px-4 py-10 text-neutral-800">
      <h2 className="font-display text-xl font-semibold">About page error</h2>
      <p className="mt-3 text-sm text-neutral-600">{error.message}</p>
      <button
        type="button"
        onClick={() => reset()}
        className="mt-6 rounded-pill border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-900 hover:border-neutral-400"
      >
        Retry
      </button>
    </div>
  );
}
