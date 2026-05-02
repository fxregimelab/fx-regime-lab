'use client';

import { useState } from 'react';
import { useResearchMemoReader, useResearchMemosList } from '@/lib/queries';

const SUBSTACK_EMBED = 'https://fxregimelab.substack.com/embed';

/** Vertical memo feed + reader overlay + Substack subscribe embed (terminal [M] rail). */
export function MemoSidebar() {
  const listQ = useResearchMemosList();
  const [readerId, setReaderId] = useState<string | null>(null);
  const readerQ = useResearchMemoReader(readerId);

  return (
    <>
      <div className="flex h-full min-h-[60vh] w-full max-w-xl flex-col border-[#1a1a1a] bg-[#000000] text-[#ccc]">
        <header className="border-b border-[#1a1a1a] px-4 py-3 font-mono text-[10px] tracking-widest text-[#888]">
          WEEKLY MACRO MEMO
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-3 py-2">
          {listQ.isLoading && (
            <p className="font-mono text-[10px] text-[#666]">Loading…</p>
          )}
          {listQ.isError && (
            <p className="font-mono text-[10px] text-[#c45]">Could not load memos.</p>
          )}
          <ul className="list-none space-y-2 p-0">
            {(listQ.data ?? []).map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  onClick={() => setReaderId(m.id)}
                  className="w-full border border-transparent bg-transparent text-left font-mono text-[11px] text-[#e0e0e0] transition-colors hover:border-[#333] hover:bg-[#0a0a0a]"
                >
                  <span className="block truncate">{m.title}</span>
                  <span className="block text-[9px] tracking-wider text-[#666]">{m.date}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
        <footer className="shrink-0 border-t border-[#1a1a1a] p-3">
          <p className="mb-2 font-mono text-[9px] tracking-widest text-[#555]">SUBSCRIBE</p>
          <iframe
            src={SUBSTACK_EMBED}
            title="Substack subscription"
            className="h-[140px] w-full border border-[#222] bg-[#0a0a0a]"
            style={{ filter: 'grayscale(1)' }}
          />
        </footer>
      </div>

      {readerId ? (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/85 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Memo reader"
        >
          <button
            type="button"
            className="absolute inset-0 cursor-default border-0 bg-transparent"
            aria-label="Close reader"
            onClick={() => setReaderId(null)}
          />
          <div
            className="relative z-[1] max-h-[90vh] w-full max-w-2xl overflow-y-auto border border-[#333] bg-[#000000] px-6 py-8 text-[#e8e8e8] shadow-2xl"
            style={{ fontFamily: 'Georgia, "Times New Roman", Times, serif' }}
          >
            <button
              type="button"
              onClick={() => setReaderId(null)}
              className="absolute right-3 top-3 border border-[#444] bg-black px-2 py-1 font-mono text-[10px] text-[#aaa]"
            >
              CLOSE
            </button>
            {readerQ.isLoading ? (
              <p className="text-sm opacity-60">Loading…</p>
            ) : null}
            {readerQ.data ? (
              <>
                <p className="mb-4 font-mono text-[10px] tracking-widest text-[#666]">
                  {readerQ.data.date}
                </p>
                <h1 className="mb-6 text-xl font-normal leading-snug">{readerQ.data.title}</h1>
                <div className="whitespace-pre-wrap text-[15px] leading-relaxed">
                  {readerQ.data.raw_content}
                </div>
              </>
            ) : null}
            {!readerQ.isLoading && readerId && !readerQ.data ? (
              <p className="font-mono text-[11px] text-[#888]">Memo not found.</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
