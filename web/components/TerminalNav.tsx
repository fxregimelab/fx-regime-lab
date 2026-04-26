'use client';

import { LogoMark } from '@/components/LogoMark';
import { PAIRS } from '@/lib/mock/data';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const CENTER_LINKS: { href: string; label: string }[] = [
  { href: '/terminal', label: 'INDEX' },
  { href: '/terminal/fx-regime', label: 'FX REGIME' },
];

const chipActive: Record<string, string> = {
  EURUSD: 'border border-[#4BA3E3] text-[#4BA3E3]',
  USDJPY: 'border border-[#F5923A] text-[#F5923A]',
  USDINR: 'border border-[#D94030] text-[#D94030]',
};

function navTextClass(href: string, pathname: string) {
  const isActive = href === '/terminal' ? pathname === '/terminal' : pathname === href;
  if (isActive) return 'text-[#e8e8e8]';
  return 'text-[#555] hover:text-[#999]';
}

export function TerminalNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 h-[48px] border-b border-[#1e1e1e] bg-[#080808]">
      <div className="mx-auto flex h-full max-w-[1600px] items-center gap-2 px-4 sm:px-5">
        <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
          <Link href="/" className="flex shrink-0 items-center gap-2">
            <LogoMark className="h-[22px] w-[22px] shrink-0 text-[#e8e8e8]" />
            <span className="hidden font-mono text-[10px] font-normal tracking-widest text-[#e8e8e8] sm:inline">
              FX REGIME LAB
            </span>
            <span className="hidden h-4 w-px bg-[#1e1e1e] sm:block" />
            <span className="hidden font-mono text-[8px] text-[#555] sm:inline-flex sm:items-center sm:rounded sm:border sm:border-[#1e1e1e] sm:px-1.5 sm:py-0.5">
              TERMINAL
            </span>
          </Link>
        </div>

        <nav
          className="hidden min-w-0 items-center justify-center gap-6 md:flex"
          aria-label="Terminal"
        >
          {CENTER_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`font-mono text-[10px] font-normal tracking-[0.08em] ${navTextClass(href, pathname)}`}
            >
              {label}
            </Link>
          ))}
        </nav>

        <div className="flex flex-1 items-center justify-end gap-2 sm:gap-3">
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            {PAIRS.map((p) => {
              const chipHref = `/terminal/fx-regime/${p.urlSlug}`;
              const active = pathname?.includes(p.urlSlug) === true;
              return (
                <Link
                  key={p.label}
                  href={chipHref}
                  className={`shrink-0 px-1.5 py-0.5 font-mono text-[8px] tracking-tight ${
                    active
                      ? chipActive[p.label]
                      : 'border border-transparent text-[#555] hover:text-[#999]'
                  }`}
                >
                  [{p.display}]
                </Link>
              );
            })}
          </div>
          <Link
            href="/"
            className="shrink-0 pl-0.5 font-mono text-[9px] text-[#555] hover:text-[#999] sm:pl-1"
          >
            ← Shell
          </Link>
        </div>
      </div>
    </header>
  );
}
