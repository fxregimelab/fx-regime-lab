import { TerminalNav } from '@/components/TerminalNav';

export const revalidate = 300;

export default function TerminalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-1 flex-col bg-[#080808] text-[#e8e8e8]">
      <TerminalNav />
      {children}
    </div>
  );
}
