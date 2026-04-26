'use client';

export function AiRateLimitState() {
  const now = new Date();
  const midnight = new Date(now);
  midnight.setUTCHours(24, 0, 0, 0);
  const hoursLeft = Math.ceil((midnight.getTime() - now.getTime()) / 3600000);

  return (
    <div className="flex flex-col items-center gap-3.5 border border-[#1e1e1e] border-t-2 border-t-amber-400 bg-[#0c0c0c] px-4 py-5 text-center">
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden>
        <title>Rate limit</title>
        <circle cx="14" cy="14" r="10" stroke="#fbbf24" strokeWidth="1.5" />
        <line x1="14" y1="8" x2="14" y2="14" stroke="#fbbf24" strokeWidth="1.5" />
        <line x1="14" y1="14" x2="18" y2="17" stroke="#fbbf24" strokeWidth="1.5" />
      </svg>
      <div>
        <p className="mb-1.5 font-mono text-[10px] font-bold tracking-wide text-amber-400">
          DAILY AI BUDGET REACHED
        </p>
        <p className="font-sans text-[12px] leading-relaxed text-[#444]">
          AI generation resets at midnight UTC. Cached briefs remain available.
        </p>
      </div>
      <div className="flex items-center gap-2 border border-[#1a1a1a] bg-[#0a0a0a] px-4 py-2">
        <span className="font-mono text-[9px] tracking-wide text-[#555]">RESETS IN</span>
        <span className="font-mono text-[14px] font-bold text-amber-400">{hoursLeft}h</span>
        <span className="font-mono text-[9px] text-[#333]">at 00:00 UTC</span>
      </div>
    </div>
  );
}
