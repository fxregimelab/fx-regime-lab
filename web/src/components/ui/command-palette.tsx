'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { PAIRS } from '@/lib/mockData';

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const items = [
    { label: 'Home', path: '/' },
    { label: 'Brief', path: '/brief' },
    { label: 'Performance', path: '/performance' },
    { label: 'Terminal Index', path: '/terminal' },
    ...PAIRS.map(p => ({ label: `Desk: ${p.display}`, path: `/terminal/fx-regime/${p.urlSlug}` }))
  ];

  const filtered = items.filter(item => item.label.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => {
          if (!prev) setSelectedIndex(0);
          return !prev;
        });
      }
      
      if (!open) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        setOpen(false);
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
        if (!filtered.length) return;
        const idx = Math.min(selectedIndex, filtered.length - 1);
        if (filtered[idx]) {
          router.push(filtered[idx].path);
          setOpen(false);
          setQuery('');
          setSelectedIndex(0);
        }
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [open, filtered, selectedIndex, router]);

  if (!open) return null;

  const clampedIndex = filtered.length ? Math.min(selectedIndex, filtered.length - 1) : 0;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm"
      onClick={() => {
        setOpen(false);
        setSelectedIndex(0);
      }}
    >
      <div className="bg-[#050505] border border-[#1a1a1a] shadow-none w-full max-w-[500px] overflow-hidden rounded-none" onClick={e => e.stopPropagation()}>
        <input 
          ref={inputRef}
          autoFocus
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelectedIndex(0);
          }}
          placeholder="Type a command or search..."
          className="w-full bg-transparent text-[#e5e5e5] placeholder-[#666] font-sans text-sm px-4 py-4 border-b border-[#1a1a1a] outline-none"
        />
        <div className="max-h-[300px] overflow-y-auto">
          {filtered.length === 0 ? (
            <p className="px-4 py-8 text-center text-[#666] font-mono text-xs">No results found.</p>
          ) : (
            <div className="py-2">
              {filtered.map((item, i) => (
                <button 
                  key={item.path}
                  onMouseEnter={() => setSelectedIndex(i)}
                  className={`w-full text-left px-4 py-2 outline-none font-mono text-xs transition-none ${
                    i === clampedIndex 
                      ? 'bg-[#e5e5e5] text-[#0a0a0a]' 
                      : 'text-[#e5e5e5] hover:bg-transparent'
                  }`}
                  onClick={() => {
                    router.push(item.path);
                    setOpen(false);
                    setQuery('');
                    setSelectedIndex(0);
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="px-4 py-2 border-t border-[#1a1a1a] bg-[#080808] flex justify-between items-center">
          <span className="font-mono text-[9px] text-[#666]">Use ↑↓ to navigate, ↵ to select</span>
          <span className="font-mono text-[9px] text-[#666]">esc to close</span>
        </div>
      </div>
    </div>
  );
}
