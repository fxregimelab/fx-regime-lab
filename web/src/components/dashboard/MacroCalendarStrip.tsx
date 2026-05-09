import type { MacroEventRow } from "@/lib/supabase/queries";

interface MacroCalendarStripProps {
  events: MacroEventRow[];
}

export function MacroCalendarStrip({ events }: MacroCalendarStripProps) {
  if (events.length === 0) {
    return (
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-3 mb-10">
        <span className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider">
          NO HIGH-IMPACT EVENTS TODAY
        </span>
      </div>
    );
  }

  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
      <div className="px-5 py-3 border-b border-[var(--color-border)]">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Macro Calendar — High Impact
        </p>
      </div>
      <div className="px-5 py-3 flex flex-wrap gap-3">
        {events.map((e) => (
          <div
            key={e.id}
            className="border border-[var(--color-border-subtle)] px-3 py-2"
          >
            <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider">
              {e.category ?? "GLOBAL"}
            </span>
            <p className="font-mono text-[11px] text-[var(--color-text)] font-medium mt-0.5">
              {e.event}
            </p>
            <p className="font-mono text-[9px] text-[var(--color-text-secondary)] mt-0.5">
              {e.pairs.join(", ")}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
