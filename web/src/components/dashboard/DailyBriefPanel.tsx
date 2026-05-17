import { normalizeProp } from "@/components/ui/utils";
import type { BriefLogRow } from "@/lib/supabase/queries";
import Link from "next/link";

interface DailyBriefPanelProps {
  brief: BriefLogRow | null;
}

export function DailyBriefPanel({ brief }: DailyBriefPanelProps) {
  const dd = normalizeProp(brief?.dollar_dominance);
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
      <div className="px-5 py-3 border-b border-[var(--color-border)] flex items-center justify-between">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Macro Regime Dispatch
        </p>
        {brief?.date && (
          <span className="font-mono text-[9px] text-[var(--color-text-muted)] tabular-nums">
            {brief.date}
          </span>
        )}
      </div>
      <div className="px-5 py-4">
        {brief?.brief_text ? (
          <>
            <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-relaxed">
              {brief.brief_text.length > 300
                ? `${brief.brief_text.slice(0, 300)}...`
                : brief.brief_text}
            </p>
            {dd != null && (
              <div className="mt-3 flex items-center gap-2">
                <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider">
                  DOLLAR DOMINANCE
                </span>
                <span className="font-mono text-[11px] text-[var(--color-text)] tabular-nums">
                  {(dd * 100).toFixed(0)}%
                </span>
              </div>
            )}
            <Link
              href="/brief"
              className="inline-block mt-3 font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider hover:text-[var(--color-text)] transition-colors"
            >
              Read full brief →
            </Link>
          </>
        ) : (
          <p className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider">
            Today&apos;s brief is being generated...
          </p>
        )}
      </div>
    </div>
  );
}
