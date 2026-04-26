export function NoCalendarEventsState({ pair = null }: { pair?: string | null }) {
  return (
    <div className="flex flex-col items-center gap-3 border border-[#e5e5e5] bg-[#fafafa] px-6 py-10">
      <svg width="36" height="36" viewBox="0 0 36 36" fill="none" aria-hidden>
        <title>No events</title>
        <rect x="4" y="8" width="28" height="24" stroke="#d0d0d0" strokeWidth="1.5" />
        <line x1="4" y1="14" x2="32" y2="14" stroke="#d0d0d0" strokeWidth="1.5" />
        <line x1="12" y1="4" x2="12" y2="10" stroke="#d0d0d0" strokeWidth="1.5" />
        <line x1="24" y1="4" x2="24" y2="10" stroke="#d0d0d0" strokeWidth="1.5" />
        <line x1="12" y1="22" x2="24" y2="22" stroke="#d0d0d0" strokeWidth="1.5" />
      </svg>
      <p className="m-0 font-sans text-[14px] font-semibold text-[#0a0a0a]">No events scheduled</p>
      <p className="m-0 max-w-[260px] text-center font-sans text-[13px] text-[#737373]">
        {pair
          ? `No upcoming macro events found for ${pair}.`
          : 'No macro events match the current filter.'}
      </p>
      <p className="mt-1 font-mono text-[10px] text-[#bbb]">
        Try selecting ALL pairs or check back later.
      </p>
    </div>
  );
}
