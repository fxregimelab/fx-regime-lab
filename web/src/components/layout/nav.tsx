'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LogoMark } from '../ui/logo-mark';
import { BRAND } from '@/lib/mockData';
import { PULSE_BAR_H } from '../ui/macro-pulse-bar';

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
    <header className="border-b border-[#e5e5e5] bg-white sticky z-[90]" style={{ top: `${PULSE_BAR_H}px` }}>
      <nav className="max-w-[1152px] mx-auto px-6 h-[54px] flex items-center justify-between">
        <Link href="/" className="flex items-center">
          <LogoMark size={24} />
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

          <div className="relative group" onClick={e => e.stopPropagation()}>
            <button onClick={() => setOpen(v => !v)}
              className="font-sans text-[13px] font-medium text-[#555] px-[14px] h-[54px] flex items-center gap-1.5 border-b-2 border-transparent group-hover:text-[#0a0a0a]">
              Research
              <svg width="10" height="6" viewBox="0 0 10 6" fill="none" className={`opacity-50 transition-transform duration-150 ${open ? 'rotate-180' : ''} group-hover:rotate-180`}>
                <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            <div className={`absolute right-0 top-[54px] bg-[#050505] border border-[#1a1a1a] min-w-[180px] shadow-none z-[1000] transition-all duration-150 ${open ? 'opacity-100 visible' : 'opacity-0 invisible group-hover:opacity-100 group-hover:visible'}`}>
              {[
                ['/performance', 'Performance'],
                ['/strategy', 'Strategy'],
                ['/terminal/fx-regime/eurusd', 'Terminal'],
                ['/calendar', 'Calendar']
              ].map(([href, label]) => {
                const isLocked = href === '/performance' || href === '/strategy';
                if (isLocked) {
                  return (
                    <div key={href}
                      className="flex justify-between items-center w-full px-4 py-[11px] font-sans text-[13px] text-[#555] border-b border-[#1a1a1a] last:border-b-0 cursor-not-allowed">
                      <span>{label}</span>
                      <span className="text-[9px] font-mono tracking-widest text-[#444]">[ LOCKED ]</span>
                    </div>
                  );
                }
                return (
                  <Link key={href} href={href} onClick={() => setOpen(false)}
                    className="flex items-center w-full px-4 py-[11px] font-sans text-[13px] text-[#e8e8e8] border-b border-[#1a1a1a] last:border-b-0 transition-colors hover:bg-[#111]">
                    {label}
                  </Link>
                );
              })}
            </div>
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
            <span className="w-1.5 h-1.5 shrink-0 hidden" />
            Terminal
          </Link>
        </div>
      </nav>
    </header>
  );
}
