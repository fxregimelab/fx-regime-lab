export function ChartLoadErrorState({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3.5 border border-[#1a1a1a] border-t-0 bg-[#0a0a0a] px-5 py-10">
      <div className="mb-2 flex h-20 w-full items-center justify-center border border-dashed border-[#1e1e1e]">
        <svg width="200" height="60" viewBox="0 0 200 60" preserveAspectRatio="none" aria-hidden>
          <title>Chart error</title>
          {[0, 1, 2, 3].map((i) => (
            <line
              key={i}
              x1={i * 50 + 10}
              y1="10"
              x2={i * 50 + 40}
              y2="50"
              stroke="#1e1e1e"
              strokeWidth="1"
              strokeDasharray="4,3"
            />
          ))}
        </svg>
      </div>
      <div className="text-center">
        <p className="mb-1.5 font-mono text-[9px] tracking-widest text-[#ef4444]">
          CHART LOAD ERROR
        </p>
        <p className="font-sans text-[12px] leading-relaxed text-[#444]">
          Could not load chart data. TradingView integration pending.
        </p>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="border border-[#1e1e1e] bg-transparent px-4 py-1.5 font-mono text-[10px] tracking-wide text-[#888]"
        >
          ↺ Retry
        </button>
      ) : null}
    </div>
  );
}
