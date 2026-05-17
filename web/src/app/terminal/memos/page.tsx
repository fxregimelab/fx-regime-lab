"use client";

import { MemoSidebar } from "@/components/ui/memo-sidebar";

export default function TerminalMemosPage() {
  return (
    <main
      id="main-content"
      className="min-h-screen bg-[var(--terminal-bg)] text-[var(--terminal-fg)]"
      style={{ marginTop: "var(--terminal-nav-h, 76px)" }}
    >
      <div className="px-4 pb-8 pt-2">
        <MemoSidebar />
      </div>
    </main>
  );
}
