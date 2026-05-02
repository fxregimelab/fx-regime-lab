'use client';

import { ConvexityRadarPageContent } from '@/components/pages/convexity-radar-page-content';

export default function TerminalCalendarPage() {
  return (
    <main
      className="min-h-screen bg-[#000000] text-white"
      style={{ marginTop: 'var(--terminal-nav-h, 104px)' }}
    >
      <ConvexityRadarPageContent />
    </main>
  );
}
