import { NoCalendarEventsState } from '@/components/states';
import { ErrorBoundaryCard } from '@/components/states';
import { mapMacroEventRow } from '@/lib/supabase/map-row';
import { getUpcomingMacroEvents } from '@/lib/supabase/queries';
import { CalendarClient } from './CalendarClient';

function utcToday(): string {
  return new Date().toISOString().slice(0, 10);
}

export default async function CalendarPage() {
  const ev = await getUpcomingMacroEvents();
  if (ev.error) {
    return (
      <div className="mx-auto max-w-[1280px] px-6 py-10">
        <ErrorBoundaryCard message={ev.error.message} tone="shell" />
      </div>
    );
  }

  const events = (ev.data ?? []).map(mapMacroEventRow);
  const anchorDate = utcToday();

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">MACRO CALENDAR</p>
      <h1 className="mt-2 font-sans text-[32px] font-extrabold tracking-tight text-[#0a0a0a]">
        Event calendar
      </h1>
      <p className="mt-2 max-w-2xl font-sans text-[14px] leading-relaxed text-[#737373]">
        High-impact releases that intersect with the three tracked pairs. Expand a row for stored AI
        context when available.
      </p>
      <div className="mt-10">
        {events.length === 0 ? (
          <NoCalendarEventsState />
        ) : (
          <CalendarClient events={events} anchorDate={anchorDate} />
        )}
      </div>
    </div>
  );
}
