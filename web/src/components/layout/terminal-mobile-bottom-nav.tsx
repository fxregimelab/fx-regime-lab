'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart2, LayoutGrid, Radar } from 'lucide-react';

const items = [
  { href: '/', label: 'APEX', Icon: LayoutGrid },
  { href: '/calendar', label: 'RADAR', Icon: Radar },
  { href: '/performance', label: 'TRUTH', Icon: BarChart2 },
] as const;

export function TerminalMobileBottomNav() {
  const pathname = usePathname() || '';

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-50 h-16 w-full border-t border-[#111] bg-[#000000]"
      aria-label="Terminal mobile navigation"
    >
      <div className="flex h-full w-full items-stretch justify-around px-6 md:px-8">
        {items.map(({ href, label, Icon }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 font-mono text-[9px] tracking-widest no-underline transition-colors ${
                active ? 'text-[#d4d4d4]' : 'text-[#666] hover:text-[#999]'
              }`}
            >
              <Icon className="h-6 w-6" strokeWidth={1.5} aria-hidden />
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
