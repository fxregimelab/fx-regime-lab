'use client';

import { MemoSidebar } from '@/components/ui/memo-sidebar';

export default function TerminalMemosPage() {
  return (
    <main
      className="min-h-screen bg-[#000000] text-white"
      style={{ marginTop: 'var(--terminal-nav-h, 104px)' }}
    >
      <div className="px-4 pb-8 pt-2">
        <MemoSidebar />
      </div>
    </main>
  );
}
