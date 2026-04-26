'use client';

import { LogoMark } from '@/components/LogoMark';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useCallback, useState } from 'react';

const links: { href: string; label: string }[] = [
  { href: '/', label: 'Home' },
  { href: '/brief', label: 'Brief' },
  { href: '/signals', label: 'Signals' },
  { href: '/performance', label: 'Performance' },
  { href: '/calendar', label: 'Calendar' },
  { href: '/about', label: 'About' },
];

function linkActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Nav() {
  const pathname = usePathname() ?? '/';
  const [drawerOpen, setDrawerOpen] = useState(false);
  const close = useCallback(() => setDrawerOpen(false), []);

  return (
    <header className="sticky top-0 z-50 border-b border-[#e5e5e5] bg-white">
      <nav className="mx-auto flex h-[54px] max-w-[1280px] items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5" onClick={close}>
          <LogoMark className="h-[22px] w-[22px] shrink-0 text-[#0a0a0a]" />
          <span className="font-mono text-[10px] font-normal tracking-widest text-[#0a0a0a]">
            FX REGIME LAB
          </span>
        </Link>

        <div className="hidden items-center gap-0 md:flex">
          {links.map(({ href, label }) => {
            const active = linkActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                className={`px-3.5 py-0 font-sans text-[13px] ${
                  active ? 'font-semibold text-[#0a0a0a]' : 'font-medium text-[#a0a0a0]'
                }`}
              >
                {label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/terminal"
            className="hidden rounded-none bg-[#0a0a0a] px-3 py-1.5 font-mono text-[10px] text-white md:inline-block"
          >
            Terminal →
          </Link>

          <button
            type="button"
            className="flex h-10 w-10 flex-col items-center justify-center gap-1 md:hidden"
            aria-expanded={drawerOpen}
            aria-label="Open menu"
            onClick={() => setDrawerOpen((o) => !o)}
          >
            <span className="block h-px w-5 bg-[#0a0a0a]" />
            <span className="block h-px w-5 bg-[#0a0a0a]" />
            <span className="block h-px w-5 bg-[#0a0a0a]" />
          </button>
        </div>
      </nav>

      {drawerOpen ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/20 md:hidden"
            aria-label="Close menu"
            onClick={close}
          />
          <div className="fixed right-0 top-0 z-50 flex h-full w-64 flex-col bg-white py-6 pl-6 pr-4 shadow-xl md:hidden">
            <div className="mb-8 flex justify-end">
              <button
                type="button"
                className="font-mono text-[10px] text-[#a0a0a0]"
                onClick={close}
              >
                Close
              </button>
            </div>
            <div className="flex flex-1 flex-col gap-1">
              {links.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`border-b border-[#f0f0f0] py-3 font-sans text-[14px] ${
                    linkActive(pathname, href) ? 'font-semibold text-[#0a0a0a]' : 'text-[#a0a0a0]'
                  }`}
                  onClick={close}
                >
                  {label}
                </Link>
              ))}
            </div>
            <Link
              href="/terminal"
              className="mt-auto bg-[#0a0a0a] py-2.5 text-center font-mono text-[10px] text-white"
              onClick={close}
            >
              Terminal →
            </Link>
          </div>
        </>
      ) : null}
    </header>
  );
}
