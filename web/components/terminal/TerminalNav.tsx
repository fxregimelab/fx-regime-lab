// Terminal navigation strip
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { PAIRS } from '@/lib/constants/pairs';

const ACCENT = '#e8a045';

const links = [
  { href: '/terminal', label: 'Home', kind: 'hub' as const },
  { label: 'FX regime', kind: 'strategy' as const },
];

export function TerminalNav() {
  const pathname = usePathname() ?? '';
  const parts = pathname.split('/').filter(Boolean);
  const strategySeg =
    parts[0] === 'terminal' && parts.length >= 2 && parts[1] !== '' ? parts[1]! : 'fx-regime';
  const pairSlugActive = parts.length >= 3 ? parts[2] : undefined;

  const strategyHref = `/terminal/${strategySeg}`;

  return (
    <header className="border-b border-neutral-800 bg-terminal-surface">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 font-mono text-xs">
        {links.map((l) => {
          if (l.kind === 'hub') {
            const active = pathname === l.href || pathname === `${l.href}/`;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={
                  active
                    ? 'opacity-100'
                    : 'text-neutral-400 opacity-90 hover:text-neutral-100 hover:opacity-100'
                }
                style={active ? { color: ACCENT } : undefined}
              >
                {l.label}
              </Link>
            );
          }
          const hubActive = pathname === strategyHref || pathname === `${strategyHref}/`;
          return (
            <Link
              key={strategyHref}
              href={strategyHref}
              className={
                hubActive
                  ? 'opacity-100'
                  : 'text-neutral-400 opacity-90 hover:text-neutral-100 hover:opacity-100'
              }
              style={hubActive ? { color: ACCENT } : undefined}
            >
              {l.label}
            </Link>
          );
        })}
        <span className="text-neutral-600" aria-hidden>
          |
        </span>
        {PAIRS.map((p) => {
          const href = `/terminal/${strategySeg}/${p.urlSlug}`;
          const active = pairSlugActive === p.urlSlug;
          return (
            <Link
              key={p.urlSlug}
              href={href}
              className={
                active
                  ? 'opacity-100'
                  : 'text-neutral-400 opacity-90 hover:text-neutral-100 hover:opacity-100'
              }
              style={active ? { color: ACCENT } : undefined}
            >
              {p.display}
            </Link>
          );
        })}
      </div>
    </header>
  );
}
