// Light theme shell layout — nav, footer, canvas bg
import '@/styles/shell.css';
import { CanvasBg } from '@/components/shell/CanvasBg';
import { Footer } from '@/components/shell/Footer';
import { Nav } from '@/components/shell/Nav';

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell-root relative flex min-h-full flex-col">
      <CanvasBg />
      <Nav />
      <div className="relative z-10 flex-1">{children}</div>
      <Footer />
    </div>
  );
}
