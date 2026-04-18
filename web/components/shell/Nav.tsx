// Shell navigation: Home, Brief, Research dropdown, About
'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ROUTES } from '@/lib/constants/routes';

export function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b border-neutral-200 bg-shell-bg/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-4 py-3">
        <Link
          href={ROUTES.home}
          className="inline-flex min-h-[44px] min-w-[44px] items-center font-display text-lg font-semibold text-neutral-900"
        >
          FX Regime Lab
        </Link>
        <div className="flex items-center gap-2 text-sm font-medium text-neutral-700 sm:gap-4">
          <Link
            href={ROUTES.home}
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center px-2 py-3 hover:text-neutral-900"
          >
            Home
          </Link>
          <Link
            href={ROUTES.brief}
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center px-2 py-3 hover:text-neutral-900"
          >
            Brief
          </Link>
          <div className="relative">
            <button
              type="button"
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1 px-2 py-3 hover:text-neutral-900"
              aria-expanded={open}
              aria-haspopup="menu"
              onClick={() => setOpen((v) => !v)}
            >
              Research
              <span className="text-xs" aria-hidden>
                ▾
              </span>
            </button>
            {open ? (
              <div className="absolute right-0 z-20 mt-2 min-w-[10rem] rounded-shell border border-neutral-200 bg-white py-1 shadow-md">
                <Link
                  href={ROUTES.performance}
                  className="flex min-h-[44px] items-center px-3 py-3 hover:bg-neutral-50"
                  onClick={() => setOpen(false)}
                >
                  Performance
                </Link>
                <Link
                  href={ROUTES.fxRegime}
                  className="flex min-h-[44px] items-center px-3 py-3 hover:bg-neutral-50"
                  onClick={() => setOpen(false)}
                >
                  FX regime
                </Link>
              </div>
            ) : null}
          </div>
          <Link
            href={ROUTES.about}
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center px-2 py-3 hover:text-neutral-900"
          >
            About
          </Link>
        </div>
      </nav>
    </header>
  );
}
