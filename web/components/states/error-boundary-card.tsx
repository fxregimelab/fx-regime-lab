export function ErrorBoundaryCard({
  message = 'Failed to load data.',
  onRetry,
  tone = 'shell',
}: {
  message?: string;
  onRetry?: () => void;
  tone?: 'shell' | 'terminal';
}) {
  const isT = tone === 'terminal';
  return (
    <div
      className={`flex items-start justify-between gap-4 p-4 pl-5 ${
        isT
          ? 'border border-[#1e1e1e] bg-[#0c0c0c] border-l-[3px] border-l-[#ef4444]'
          : 'border border-[#e5e5e5] bg-white border-l-[3px] border-l-[#dc2626]'
      }`}
    >
      <div>
        <p
          className={`mb-1.5 font-mono text-[9px] tracking-widest ${isT ? 'text-[#ef4444]' : 'text-[#dc2626]'}`}
        >
          ERROR
        </p>
        <p
          className={`font-sans text-[13px] leading-relaxed ${isT ? 'text-[#888]' : 'text-[#525252]'}`}
        >
          {message}
        </p>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className={`shrink-0 whitespace-nowrap border px-3.5 py-1.5 font-mono text-[10px] tracking-wide ${
            isT
              ? 'border-[#ef4444]/40 bg-[#ef4444]/10 text-[#ef4444]'
              : 'border-[#dc2626]/40 bg-[#fff5f5] text-[#dc2626]'
          }`}
        >
          ↺ Retry
        </button>
      ) : null}
    </div>
  );
}
