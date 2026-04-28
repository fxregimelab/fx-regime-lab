'use client';

import { Nav } from '@/components/layout/nav';
import { Footer } from '@/components/layout/footer';
import { useUpcomingMacroEvents } from '@/lib/queries';
import { CalendarTab } from '@/app/terminal/calendar-tab';
import type { Database } from '@/lib/supabase/database.types';

type MacroEventRow = Database['public']['Tables']['macro_events']['Row'];

export default function CalendarPage() {
  const eventsQ = useUpcomingMacroEvents();
  const today = new Date().toISOString().slice(0, 10);
  const events = (eventsQ.data ?? []) as MacroEventRow[];

  return (
    <>
      <Nav />
      <main className="min-h-screen bg-[#090909] text-[#ececec]">
        <section className="max-w-[980px] mx-auto px-6 py-10">
          <h1 className="font-sans text-3xl font-bold mb-2">Macro Calendar</h1>
          <p className="font-mono text-[11px] text-[#8a8a8a] tracking-widest mb-6">
            HIGH/MEDIUM impact events with AI context
          </p>
          <div className="border border-[#1e1e1e] bg-[#0d0d0d] p-4">
            {eventsQ.isPending ? (
              <div className="h-32 animate-pulse bg-[#121212]" />
            ) : (
              <CalendarTab events={events} todayIso={today} compact />
            )}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
