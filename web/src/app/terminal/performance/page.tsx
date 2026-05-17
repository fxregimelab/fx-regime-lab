"use client";

import { PerformanceLedgerPageContent } from "@/components/pages/performance-ledger-page-content";

export default function TerminalPerformancePage() {
  return (
    <main
      id="main-content"
      className="min-h-screen bg-[var(--color-void)] text-[var(--color-text)] rounded-none"
      style={{ marginTop: "var(--terminal-nav-h, 76px)" }}
    >
      <PerformanceLedgerPageContent />
    </main>
  );
}
