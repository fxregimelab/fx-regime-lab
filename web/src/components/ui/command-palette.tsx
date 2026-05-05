'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BinaryResolve } from '@/components/ui/BinaryResolve';
import { PAIRS } from '@/lib/mockData';

type CmdItem = {
  id: string;
  label: string;
  path: string;
  keywords: string[];
};

function buildItems(): CmdItem[] {
  const pages: CmdItem[] = [
    {
      id: 'shell',
      label: 'Shell · Gateway',
      path: '/',
      keywords: ['home', 'shell', 'gateway', 'landing'],
    },
    {
      id: 'apex',
      label: 'Terminal · Apex',
      path: '/terminal',
      keywords: ['apex', 'terminal', 'desk', 'g10'],
    },
    {
      id: 'ledger',
      label: 'Alpha Ledger · Performance',
      path: '/terminal/performance',
      keywords: ['ledger', 'performance', 'truth', 'alpha', 'oos', 'stats'],
    },
    {
      id: 'radar',
      label: 'Event Radar · Calendar',
      path: '/terminal/calendar',
      keywords: ['radar', 'calendar', 'events', 'macro'],
    },
    {
      id: 'memos',
      label: 'Macro Memos',
      path: '/terminal/memos',
      keywords: ['memos', 'memo', 'substack', 'research'],
    },
    {
      id: 'brief',
      label: 'Morning Brief',
      path: '/brief',
      keywords: ['brief', 'morning'],
    },
    {
      id: 'about',
      label: 'About',
      path: '/about',
      keywords: ['about', 'pipeline'],
    },
  ];

  const pairs: CmdItem[] = PAIRS.map((p) => ({
    id: `pair-${p.label}`,
    label: `Pair · ${p.display}`,
    path: `/terminal/fx-regime/${p.urlSlug}`,
    keywords: [
      p.label,
      p.display,
      p.urlSlug,
      p.label.replace('/', ''),
      ...p.display.split('/').map((s) => s.trim().toLowerCase()),
    ],
  }));

  return [...pages, ...pairs];
}

function matchesQuery(item: CmdItem, q: string): boolean {
  if (!q.trim()) return true;
  const n = q.toLowerCase().trim();
  if (item.label.toLowerCase().includes(n)) return true;
  return item.keywords.some((k) => k.toLowerCase().includes(n));
}

const TELEPORT_MS = 150;

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isTeleporting, setIsTeleporting] = useState(false);
  const [teleportPath, setTeleportPath] = useState<string | null>(null);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const teleportTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const items = useMemo(() => buildItems(), []);

  const filtered = useMemo(
    () => items.filter((item) => matchesQuery(item, query)),
    [items, query],
  );

  const initiateTeleport = useCallback((item: CmdItem) => {
    if (teleportTimerRef.current) {
      clearTimeout(teleportTimerRef.current);
      teleportTimerRef.current = null;
    }
    setIsTeleporting(true);
    setTeleportPath(item.path);
    teleportTimerRef.current = setTimeout(() => {
      router.push(item.path);
      setOpen(false);
      setQuery('');
      setSelectedIndex(0);
      setIsTeleporting(false);
      setTeleportPath(null);
      teleportTimerRef.current = null;
    }, TELEPORT_MS);
  }, [router]);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
        return;
      }
      if (!open) return;
      if (e.key === 'Escape') {
        e.preventDefault();
        if (teleportTimerRef.current) {
          clearTimeout(teleportTimerRef.current);
          teleportTimerRef.current = null;
        }
        setIsTeleporting(false);
        setTeleportPath(null);
        setOpen(false);
        setQuery('');
        setSelectedIndex(0);
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (!filtered.length) return;
        setSelectedIndex((prev) => (prev + 1) % filtered.length);
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (!filtered.length) return;
        setSelectedIndex((prev) => (prev - 1 + filtered.length) % filtered.length);
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        if (!filtered.length || isTeleporting) return;
        const idx = Math.min(selectedIndex, filtered.length - 1);
        const it = filtered[idx];
        if (it) initiateTeleport(it);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [open, filtered, selectedIndex, initiateTeleport, isTeleporting]);

  useEffect(() => {
    if (open) {
      setSelectedIndex(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    return () => {
      if (teleportTimerRef.current) clearTimeout(teleportTimerRef.current);
    };
  }, []);

  if (!open) return null;

  const clampedIndex = filtered.length ? Math.min(selectedIndex, filtered.length - 1) : 0;

  const closePalette = () => {
    if (teleportTimerRef.current) {
      clearTimeout(teleportTimerRef.current);
      teleportTimerRef.current = null;
    }
    setIsTeleporting(false);
    setTeleportPath(null);
    setOpen(false);
    setQuery('');
    setSelectedIndex(0);
  };

  return (
    <div
      className="fixed inset-0 z-[300] flex items-start justify-center bg-black/80 pt-[12vh] shadow-none"
      role="presentation"
      onMouseDown={closePalette}
    >
      <div
        className="relative w-full max-w-[520px] border border-[var(--bg-hover)] bg-[#000000] shadow-none"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {isTeleporting ? (
          <div className="pointer-events-none absolute left-4 right-4 top-3 z-[1] font-mono text-[10px] tracking-widest text-[#888] omega-heartbeat">
            [ CALCULATING_INGRESS_VECTOR... ]
          </div>
        ) : null}
        <input
          ref={inputRef}
          autoFocus
          value={isTeleporting ? '' : query}
          readOnly={isTeleporting}
          onChange={(e) => {
            if (!isTeleporting) setQuery(e.target.value);
          }}
          placeholder="Teleport — pairs, ledger, radar, memos…"
          className="w-full border-0 border-b border-[var(--bg-hover)] bg-[#000000] px-4 py-3.5 font-mono text-[13px] text-[#ffffff] placeholder-[var(--text-muted)] outline-none shadow-none"
        />
        <div className="max-h-[min(360px,50vh)] overflow-y-auto shadow-none">
          {filtered.length === 0 ? (
            <p className="px-4 py-8 text-center font-mono text-[11px] text-[var(--text-muted)] shadow-none">
              No results.
            </p>
          ) : (
            <div className="py-1 shadow-none">
              {filtered.map((item, i) => (
                <button
                  key={item.id}
                  type="button"
                  onMouseEnter={() => setSelectedIndex(i)}
                  className={`w-full border-0 px-4 py-2.5 text-left font-mono text-[11px] tracking-wide outline-none shadow-none transition-none ${
                    i === clampedIndex
                      ? 'bg-[#ffffff] text-[#000000]'
                      : 'bg-transparent text-[#ffffff] hover:bg-[var(--bg-surface)]'
                  }`}
                  onClick={() => {
                    if (!isTeleporting) initiateTeleport(item);
                  }}
                >
                  <span className="block">{item.label}</span>
                  {isTeleporting && teleportPath === item.path ? (
                    <span className={`mt-1 block font-mono text-[9px] tabular-nums ${i === clampedIndex ? 'text-[#333]' : 'text-[#555]'}`}>
                      <BinaryResolve
                        value={item.path}
                        resolveKey={item.path}
                        flickerMs={100}
                        tickMs={20}
                        resolveFlash={false}
                        className="opacity-80"
                      />
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center justify-between border-t border-[var(--bg-hover)] bg-[var(--bg-void)] px-4 py-2 shadow-none">
          <span className="font-mono text-[9px] text-[var(--text-muted)]">↑↓ navigate · ↵ open · esc</span>
          <span className="font-mono text-[9px] text-[var(--text-muted)]">⌘K</span>
        </div>
      </div>
    </div>
  );
}
