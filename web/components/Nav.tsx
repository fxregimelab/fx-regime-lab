'use client';

import { LogoMark } from '@/components/LogoMark';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

const RESEARCH_LINKS: { href: string; label: string }[] = [
  { href: '/signals', label: 'Signals' },
  { href: '/performance', label: 'Performance' },
  { href: '/calendar', label: 'Calendar' },
  { href: '/fx-regime', label: 'FX Regime' },
];

function researchActive(pathname: string): boolean {
  return RESEARCH_LINKS.some(
    ({ href }) => pathname === href || (href !== '/' && pathname.startsWith(`${href}/`))
  );
}

function linkActive(pathname: string, href: string): boolean {
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}

function navLinkClass(active: boolean): string {
  return `border-b-2 px-3.5 py-2 font-sans text-[13px] ${
    active
      ? 'border-[#F5923A] font-semibold text-[#0a0a0a]'
      : 'border-transparent font-medium text-[#a0a0a0] hover:text-[#737373]'
  }`;
}

export function Nav() {
  const pathname = usePathname() ?? '/';
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [researchOpen, setResearchOpen] = useState(false);
  const researchRef = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setDrawerOpen(false), []);

  useEffect(() => {
    if (!researchOpen) return;
    const onDoc = (e: MouseEvent) => {
      if (researchRef.current && !researchRef.current.contains(e.target as Node)) {
        setResearchOpen(false);
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [researchOpen]);

  const resActive = researchActive(pathname);

  return (
    <header className="sticky top-0 z-50 border-b border-[#e5e5e5] bg-white">
      <nav className="mx-auto flex h-[54px] max-w-[1280px] items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5" onClick={close}>
          <LogoMark className="h-[22px] w-[22px] shrink-0 text-[#0a0a0a]" />
          <span className="font-mono text-[10px] font-normal tracking-widest text-[#0a0a0a]">
            FX REGIME LAB
          </span>
        </Link>

        <div className="flex max-md:hidden items-end gap-0">
          <Link href="/" className={navLinkClass(linkActive(pathname, '/'))}>
            Home
          </Link>
          <Link href="/brief" className={navLinkClass(linkActive(pathname, '/brief'))}>
            Brief
          </Link>
          <div className="relative" ref={researchRef}>
            <button
              type="button"
              aria-expanded={researchOpen}
              aria-haspopup="true"
              onClick={() => setResearchOpen((o) => !o)}
              className={`flex items-center gap-1 border-b-2 px-3.5 py-2 font-sans text-[13px] ${
                resActive || researchOpen
                  ? 'border-[#F5923A] font-semibold text-[#0a0a0a]'
                  : 'border-transparent font-medium text-[#a0a0a0] hover:text-[#737373]'
              }`}
            >
              Research
              <span className="text-[10px]" aria-hidden>
                {researchOpen ? '▾' : '▸'}
              </span>
            </button>
            {researchOpen ? (
              <div
                className="absolute left-0 top-full z-50 min-w-[180px] border border-[#e5e5e5] bg-white py-1 shadow-md"
                role="menu"
              >
                {RESEARCH_LINKS.map(({ href, label }) => (
                  <Link
                    key={href}
                    href={href}
                    role="menuitem"
                    className={`block px-4 py-2.5 font-sans text-[13px] ${
                      linkActive(pathname, href) ? 'bg-[#fafafa] font-semibold text-[#0a0a0a]' : 'text-[#525252]'
                    }`}
                    onClick={() => setResearchOpen(false)}
                  >
                    {label}
                  </Link>
                ))}
              </div>
            ) : null}
          </div>
          <Link href="/about" className={navLinkClass(linkActive(pathname, '/about'))}>
            About
          </Link>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/terminal"
            className="hidden items-center gap-2 rounded-none bg-[#0a0a0a] px-3 py-1.5 font-mono text-[10px] text-white md:inline-flex"
          >
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#22c55e]" aria-hidden />
            Terminal
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
            <div className="flex flex-1 flex-col gap-1 overflow-y-auto">
              <Link
                href="/"
                className={`border-b border-[#f0f0f0] py-3 font-sans text-[14px] ${
                  linkActive(pathname, '/') ? 'font-semibold text-[#0a0a0a]' : 'text-[#a0a0a0]'
                }`}
                onClick={close}
              >
                Home
              </Link>
              <Link
                href="/brief"
                className={`border-b border-[#f0f0f0] py-3 font-sans text-[14px] ${
                  linkActive(pathname, '/brief') ? 'font-semibold text-[#0a0a0a]' : 'text-[#a0a0a0]'
                }`}
                onClick={close}
              >
                Brief
              </Link>
              <p className="pt-2 font-mono text-[9px] tracking-widest text-[#a0a0a0]">RESEARCH</p>
              {RESEARCH_LINKS.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`border-b border-[#f0f0f0] py-2.5 pl-2 font-sans text-[14px] ${
                    linkActive(pathname, href) ? 'font-semibold text-[#0a0a0a]' : 'text-[#a0a0a0]'
                  }`}
                  onClick={close}
                >
                  {label}
                </Link>
              ))}
              <Link
                href="/about"
                className={`border-b border-[#f0f0f0] py-3 font-sans text-[14px] ${
                  linkActive(pathname, '/about') ? 'font-semibold text-[#0a0a0a]' : 'text-[#a0a0a0]'
                }`}
                onClick={close}
              >
                About
              </Link>
            </div>
            <Link
              href="/terminal"
              className="mt-auto flex items-center justify-center gap-2 bg-[#0a0a0a] py-2.5 font-mono text-[10px] text-white"
              onClick={close}
            >
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#22c55e]" aria-hidden />
              Terminal
            </Link>
          </div>
        </>
      ) : null}
    </header>
  );
}
