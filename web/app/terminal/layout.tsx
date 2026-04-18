// Dark theme terminal layout
import '@/styles/terminal.css';
import { TerminalNav } from '@/components/terminal/TerminalNav';

export default function TerminalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="terminal-root flex min-h-full flex-col">
      <TerminalNav />
      <div className="flex-1">{children}</div>
    </div>
  );
}
