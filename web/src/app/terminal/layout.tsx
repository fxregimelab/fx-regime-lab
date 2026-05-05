import type { ReactNode } from "react";
import { TerminalNav } from "@/components/terminal/TerminalNav";
import { GlobalMacroPulse } from "@/components/layout/global-macro-pulse";

export default function TerminalLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--color-void)] text-[var(--color-text)] overflow-hidden">
      <GlobalMacroPulse />
      <TerminalNav />
      <main id="main-content" className="max-w-[1152px] mx-auto px-6 py-10 pt-[64px]">
        {children}
      </main>
    </div>
  );
}
