export function NoValidationDataState() {
  return (
    <div className="flex flex-col items-center gap-2.5 border border-[#e5e5e5] px-6 py-8">
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
        <title>No validation</title>
        <rect x="4" y="4" width="24" height="24" stroke="#d0d0d0" strokeWidth="1.5" />
        {[8, 14, 20].map((y) => (
          <line key={y} x1="8" y1={y} x2="24" y2={y} stroke="#ebebeb" strokeWidth="1" />
        ))}
      </svg>
      <p className="m-0 font-sans text-[14px] font-semibold text-[#0a0a0a]">
        No validation history yet
      </p>
      <p className="m-0 max-w-[280px] text-center font-sans text-[13px] text-[#737373]">
        Regime calls are validated the following trading day. Check back after market close.
      </p>
      <p className="mt-1 font-mono text-[10px] text-[#bbb]">Pipeline runs daily at 07:00 UTC</p>
    </div>
  );
}
