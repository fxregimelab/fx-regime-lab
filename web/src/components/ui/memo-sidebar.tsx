"use client";

import { useResearchMemoReader, useResearchMemosList } from "@/lib/queries";
import { useState } from "react";

const SUBSTACK_EMBED = "https://fxregimelab.substack.com/embed";

/** Vertical memo feed + reader overlay + Substack subscribe embed (terminal [M] rail). */
export function MemoSidebar() {
  const listQ = useResearchMemosList();
  const [readerId, setReaderId] = useState<string | null>(null);
  const readerQ = useResearchMemoReader(readerId);

  return (
    <>
      <div className="flex h-full min-h-[60vh] w-full max-w-xl border-[var(--color-border)] bg-[var(--color-void)] text-[var(--color-text)]">
        <header className="border-b border-[var(--color-border)] px-4 py-3 font-mono text-[10px] tracking-widest text-[var(--color-text-muted)]">
          WEEKLY MACRO MEMO
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-3 py-2">
          {listQ.isLoading && (
            <p className="font-mono text-[10px] text-[var(--color-text-muted)]">Loading…</p>
          )}
          {listQ.isError && (
            <p className="font-mono text-[10px] text-[var(--color-down)]">
              Could not load memos.
            </p>
          )}
          <ul className="list-none space-y-2 p-0">
            {(listQ.data ?? []).map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  onClick={() => setReaderId(String(m.id))}
                  className="w-full border border-transparent bg-transparent text-left font-mono text-[11px] text-[var(--color-text)] transition-colors hover:border-[var(--color-border)] hover:bg-[var(--color-surface)]"
                >
                  <span className="block truncate">{m.title}</span>
                  <span className="block text-[9px] tracking-wider text-[var(--color-text-muted)]">
                    {m.date}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
        <footer className="shrink-0 border-t border-[var(--color-border)] p-3">
          <p className="mb-2 font-mono text-[9px] tracking-widest text-[var(--color-text-muted)]">
            SUBSCRIBE
          </p>
          <iframe
            src={SUBSTACK_EMBED}
            title="Substack subscription"
            className="h-[140px] w-full border border-[var(--color-border)] bg-[var(--color-surface)]"
            style={{ filter: "grayscale(1)" }}
          />
        </footer>
      </div>

      {readerId ? (
        <dialog
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/85 p-4"
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
            className="relative z-[1] max-h-[90vh] w-full max-w-2xl overflow-y-auto border border-[var(--color-border)] bg-[var(--color-void)] px-6 py-8 text-[var(--color-text)] shadow-2xl"
            style={{ fontFamily: 'Georgia, "Times New Roman", Times, serif' }}
          >
            <button
              type="button"
              onClick={() => setReaderId(null)}
              className="absolute right-3 top-3 border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 font-mono text-[10px] text-[var(--color-text-muted)]"
            >
              CLOSE
            </button>
            {readerQ.isLoading ? (
              <p className="text-sm opacity-60">Loading…</p>
            ) : null}
            {readerQ.data ? (
              <>
                <p className="mb-4 font-mono text-[10px] tracking-widest text-[var(--color-text-muted)]">
                  {readerQ.data.date}
                </p>
                <h1 className="mb-6 text-xl font-normal leading-snug">
                  {readerQ.data.title}
                </h1>
                <div className="whitespace-pre-wrap text-[15px] leading-relaxed">
                  {readerQ.data.raw_content}
                </div>
              </>
            ) : null}
            {!readerQ.isLoading && readerId && !readerQ.data ? (
              <p className="font-mono text-[11px] text-[var(--color-text-muted)]">
                Memo not found.
              </p>
            ) : null}
          </div>
        </dialog>
      ) : null}
    </>
  );
}
