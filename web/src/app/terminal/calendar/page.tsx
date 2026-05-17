"use client";

import { ConvexityRadarPageContent } from "@/components/pages/convexity-radar-page-content";

export default function TerminalCalendarPage() {
  return (
    <main
      id="main-content"
      className="min-h-screen bg-[var(--color-void)] text-[var(--color-text)]"
      style={{ marginTop: "var(--terminal-nav-h, 76px)" }}
    >
      <ConvexityRadarPageContent />
    </main>
  );
}
