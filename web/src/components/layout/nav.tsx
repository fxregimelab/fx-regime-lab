'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LogoMark } from '../ui/logo-mark';
import { BRAND } from '@/lib/mockData';

export function Nav() {
  const currentRoute = usePathname();
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    const h = () => setOpen(false);
    document.addEventListener('click', h);
    return () => document.removeEventListener('click', h);
  }, []);

  const isActive = (href: string) => href === '/' ? currentRoute === '/' : currentRoute.startsWith(href);

  return (
    <header className="border-b border-[#e5e5e5] bg-white sticky top-0 z-50">
      <nav className="max-w-[1152px] mx-auto px-6 h-[54px] flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <LogoMark size={22} />
          <span className="font-sans font-bold text-[15px] text-[#0a0a0a] tracking-tight">FX Regime Lab</span>
        </Link>

        <div className="flex items-center gap-0">
          {[
            ['/', 'Home'],
            ['/brief', 'Brief']
          ].map(([href, label]) => (
            <Link key={href} href={href}
              className={`font-sans text-[13px] font-medium px-[14px] h-[54px] flex items-center border-b-2 transition-colors ${
                isActive(href) ? 'text-[#0a0a0a] border-accent' : 'text-[#555] border-transparent'
              }`}
              style={{ borderBottomColor: isActive(href) ? BRAND.accent : 'transparent' }}
            >
              {label}
            </Link>
          ))}

          <div className="relative" onClick={e => e.stopPropagation()}>
            <button onClick={() => setOpen(v => !v)}
              className="font-sans text-[13px] font-medium text-[#555] px-[14px] h-[54px] flex items-center gap-1.5 border-b-2 border-transparent">
              Research
              <svg width="10" height="6" viewBox="0 0 10 6" fill="none" className={`opacity-50 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}>
                <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            {open && (
              <div className="absolute right-0 top-[54px] bg-white border border-[#e5e5e5] min-w-[180px] shadow-[0_8px_24px_rgba(0,0,0,0.08)] z-[100]">
                {[
                  ['/performance', 'Performance'],
                  ['/fx-regime', 'FX Regime'],
                  ['/calendar', 'Calendar']
                ].map(([href, label]) => (
                  <Link key={href} href={href} onClick={() => setOpen(false)}
                    className="flex items-center w-full px-4 py-[11px] font-sans text-[13px] text-[#0a0a0a] border-b border-[#f5f5f5] transition-colors hover:bg-[#fafafa]">
                    {label}
                  </Link>
                ))}
              </div>
            )}
          </div>

          <Link href="/about"
            className={`font-sans text-[13px] font-medium px-[14px] h-[54px] flex items-center border-b-2 transition-colors ${
              isActive('/about') ? 'text-[#0a0a0a] border-accent' : 'text-[#555] border-transparent'
            }`}
            style={{ borderBottomColor: isActive('/about') ? BRAND.accent : 'transparent' }}
          >
            About
          </Link>

          <Link href="/terminal"
            className="ml-[14px] bg-[#0a0a0a] text-white font-sans font-semibold text-xs px-4 py-2 tracking-wide flex items-center gap-1.5 transition-opacity hover:opacity-90">
            <span className="w-1.5 h-1.5 rounded-full live-indicator animate-pulse shrink-0" />
            Terminal
          </Link>
        </div>
      </nav>
    </header>
  );
}
