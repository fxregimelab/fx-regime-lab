import type { ReactNode } from "react";
import { TerminalNav } from "@/components/terminal/TerminalNav";

export default function TerminalLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-terminal-bg text-terminal-text">
      <TerminalNav />
      <main className="max-w-[1200px] mx-auto px-6 py-10">{children}</main>
    </div>
  );
}
