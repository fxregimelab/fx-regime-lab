"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface ErrorRetryProps {
  error: Error | null;
  retry: () => void;
  lastSuccessAt?: Date | null;
  label?: string;
}

/** Terminal-styled error retry UI with exponential backoff countdown.
 *  Shows last successful fetch timestamp and retry button.
 */
export function ErrorRetry({
  error,
  retry,
  lastSuccessAt,
  label = "DATA FETCH FAILED",
}: ErrorRetryProps) {
  const [attempt, setAttempt] = useState(1);
  const [countdown, setCountdown] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const delayMs = Math.min(1000 * 2 ** attempt, 30000); // max 30s

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleRetry = useCallback(() => {
    setAttempt((a) => a + 1);
    retry();
  }, [retry]);

  const handleAutoRetry = useCallback(() => {
    if (countdown > 0) return;
    setCountdown(Math.ceil(delayMs / 1000));

    const tick = () => {
      setCountdown((c) => {
        if (c <= 1) {
          handleRetry();
          return 0;
        }
        timerRef.current = setTimeout(tick, 1000);
        return c - 1;
      });
    };

    timerRef.current = setTimeout(tick, 1000);
  }, [countdown, delayMs, handleRetry]);

  const timeAgo = (d: Date) => {
    const s = Math.floor((Date.now() - d.getTime()) / 1000);
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    return `${Math.floor(s / 3600)}h ago`;
  };

  return (
    <div
      className="border border-[var(--terminal-danger)] bg-[var(--terminal-bg)] p-6 font-mono"
      role="alert"
      aria-live="assertive"
    >
      <p className="text-[10px] tracking-widest text-[var(--terminal-danger)] uppercase mb-2">
        [ {label} ]
      </p>
      <p className="text-[11px] text-[var(--terminal-fg)] mb-2">
        {error?.message || "Unable to reach data source."}
      </p>

      {lastSuccessAt && (
        <p className="text-[10px] text-[var(--terminal-fg-dim)] mb-4">
          Last successful fetch: {timeAgo(lastSuccessAt)}
        </p>
      )}

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleRetry}
          disabled={countdown > 0}
          className="border border-[var(--terminal-border-bright)] bg-transparent px-4 py-2 text-[10px] tracking-widest text-[var(--terminal-fg-muted)] transition-colors hover:text-[var(--terminal-fg)] hover:border-[var(--terminal-fg)] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {countdown > 0 ? `RETRY IN ${countdown}s` : "[ RETRY NOW ]"}
        </button>

        {countdown === 0 && (
          <button
            type="button"
            onClick={handleAutoRetry}
            className="text-[10px] tracking-widest text-[var(--terminal-fg-dim)] hover:text-[var(--terminal-fg-muted)] transition-colors"
          >
            AUTO-RETRY ({Math.ceil(delayMs / 1000)}s)
          </button>
        )}
      </div>

      <p className="text-[9px] text-[var(--terminal-fg-dim)] mt-3">
        Attempt {attempt} · Backoff: {Math.ceil(delayMs / 1000)}s max
      </p>
    </div>
  );
}
