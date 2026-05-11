import { getResearchMemosList } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Memo Archive | FX Regime Lab",
  description:
    "Archive of weekly macro memos and regime research notes from FX Regime Lab.",
  robots: { index: true, follow: true },
};

export default async function MemoArchivePage() {
  const supabase = await createClient();
  const memos = await getResearchMemosList(supabase);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 text-[var(--color-text)]">
      <header className="mb-8 border-b border-[var(--color-border)] pb-4">
        <h1 className="font-mono text-xs tracking-widest text-[var(--color-text-muted)]">
          WEEKLY MACRO MEMO ARCHIVE
        </h1>
        <p className="mt-2 font-serif text-2xl font-normal">
          Regime Research Notes
        </p>
      </header>

      {memos.length === 0 ? (
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-12 text-center">
          <p className="font-mono text-[11px] tracking-widest text-[var(--color-text-muted)]">
            NO MEMOS PUBLISHED YET
          </p>
        </div>
      ) : (
        <ul className="list-none space-y-0 p-0">
          {memos.map((memo) => (
            <li
              key={memo.id}
              className="border-b border-[var(--color-border)] transition-colors hover:bg-[var(--color-surface)]"
            >
              <Link
                href={`/memo/${memo.date}`}
                className="flex items-baseline justify-between gap-4 px-2 py-4 no-underline"
              >
                <span className="font-serif text-base leading-snug">
                  {memo.title}
                </span>
                <span className="shrink-0 font-mono text-[10px] tracking-wider text-[var(--color-text-muted)]">
                  {memo.date}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
