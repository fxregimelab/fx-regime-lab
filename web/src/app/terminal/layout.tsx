import type { ReactNode } from "react";
import { TerminalNav } from "@/components/terminal/TerminalNav";
import { GlobalMacroPulse } from "@/components/layout/global-macro-pulse";

export default function TerminalLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-terminal-bg text-terminal-text overflow-hidden">
      <GlobalMacroPulse />
      <TerminalNav />
      <main className="max-w-[1200px] mx-auto px-6 py-10 pt-[64px]">
        {children}
      </main>
    </div>
  );
}
