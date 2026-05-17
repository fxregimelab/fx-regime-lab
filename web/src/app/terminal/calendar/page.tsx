"use client";

import { ConvexityRadarPageContent } from "@/components/pages/convexity-radar-page-content";

export default function TerminalCalendarPage() {
  return (
    <main
      id="main-content"
      className="min-h-screen bg-[var(--terminal-bg)] text-[var(--terminal-fg)]"
      style={{ marginTop: "var(--terminal-nav-h, 76px)" }}
    >
      <ConvexityRadarPageContent />
    </main>
  );
}
