'use client';

import { PerformanceLedgerPageContent } from '@/components/pages/performance-ledger-page-content';

export default function TerminalPerformancePage() {
  return (
    <main
      className="min-h-screen bg-[#000000] text-white rounded-none"
      style={{ marginTop: 'var(--terminal-nav-h, 104px)' }}
    >
      <PerformanceLedgerPageContent />
    </main>
  );
}
