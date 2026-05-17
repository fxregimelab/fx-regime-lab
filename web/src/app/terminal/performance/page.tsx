"use client";

import { PerformanceLedgerPageContent } from "@/components/pages/performance-ledger-page-content";

export default function TerminalPerformancePage() {
  return (
    <main
      id="main-content"
      className="min-h-screen bg-[var(--terminal-bg)] text-[var(--terminal-fg)] rounded-none"
      style={{ marginTop: "var(--terminal-nav-h, 76px)" }}
    >
      <PerformanceLedgerPageContent />
    </main>
  );
}
