function retryButtonClass(pairColor: string): string {
  if (pairColor === '#4BA3E3') {
    return 'border-[#4BA3E3]/40 bg-[#4BA3E3]/10 text-[#4BA3E3]';
  }
  if (pairColor === '#D94030') {
    return 'border-[#D94030]/40 bg-[#D94030]/10 text-[#D94030]';
  }
  return 'border-[#F5923A]/40 bg-[#F5923A]/10 text-[#F5923A]';
}

export function AiErrorState({
  onRetry,
  pairColor = '#F5923A',
}: {
  onRetry?: () => void;
  pairColor?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-3.5 border border-[#1e1e1e] border-t-2 border-t-[#ef4444] bg-[#0c0c0c] px-4 py-5 text-center">
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden>
        <title>AI error</title>
        <polygon points="14,4 26,24 2,24" stroke="#ef4444" strokeWidth="1.5" fill="none" />
        <line x1="14" y1="11" x2="14" y2="17" stroke="#ef4444" strokeWidth="1.5" />
        <circle cx="14" cy="20" r="1" fill="#ef4444" />
      </svg>
      <div>
        <p className="mb-1.5 font-mono text-[10px] font-bold tracking-wide text-[#ef4444]">
          GENERATION FAILED
        </p>
        <p className="font-sans text-[12px] leading-relaxed text-[#444]">
          AI analysis could not be generated. Check your connection or try again.
        </p>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className={`border px-5 py-2 font-mono text-[10px] font-bold tracking-wide ${retryButtonClass(pairColor)}`}
        >
          ↺ RETRY GENERATION
        </button>
      ) : null}
    </div>
  );
}
