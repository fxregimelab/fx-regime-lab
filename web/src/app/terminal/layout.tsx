import { GlobalMacroPulse } from "@/components/layout/global-macro-pulse";
import { TerminalNav } from "@/components/terminal/TerminalNav";
import { TerminalSubNav } from "@/components/terminal/TerminalSubNav";
import type { ReactNode } from "react";

export default function TerminalLayout({ children }: { children: ReactNode }) {
  return (
    <div
      data-surface="terminal"
      className="min-h-screen bg-[var(--color-void)] text-[var(--color-text)] overflow-hidden"
    >
      <GlobalMacroPulse />
      <TerminalNav />
      <TerminalSubNav />
      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 py-10 pt-4"
      >
        {children}
      </main>
    </div>
  );
}
