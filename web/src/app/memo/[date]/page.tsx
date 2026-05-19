import { getResearchMemoByDate } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

interface MemoDatePageProps {
  params: Promise<{ date: string }>;
}

export async function generateMetadata({
  params,
}: MemoDatePageProps): Promise<Metadata> {
  const { date } = await params;
  return {
    title: `Memo — ${date} | FX Regime Lab`,
    description: `Weekly macro memo archive entry for ${date}.`,
    robots: { index: true, follow: true },
  };
}

export default async function MemoDatePage({ params }: MemoDatePageProps) {
  const { date } = await params;
  const supabase = await createClient();
  const memo = await getResearchMemoByDate(supabase, date);

  if (!memo) {
    notFound();
  }

  return (
    <main className="mx-auto max-w-2xl px-4 py-8 text-[var(--color-text)]">
      <Link
        href="/memo"
        className="mb-6 inline-block font-mono text-[10px] tracking-widest text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text)]"
      >
        ← BACK TO ARCHIVE
      </Link>

      <article className="border border-[var(--color-border)] bg-[var(--color-void)] px-6 py-8">
        <header className="mb-6 border-b border-[var(--color-border)] pb-4">
          <p className="mb-2 font-mono text-[10px] tracking-widest text-[var(--color-text-muted)]">
            {memo.date}
          </p>
          <h1
            className="text-xl font-normal leading-snug"
            style={{
              fontFamily: 'Georgia, "Times New Roman", Times, serif',
            }}
          >
            {memo.title}
          </h1>
        </header>

        <div
          className="whitespace-pre-wrap text-[15px] leading-relaxed"
          style={{
            fontFamily: 'Georgia, "Times New Roman", Times, serif',
          }}
        >
          {memo.raw_content}
        </div>

        {memo.ai_thesis_summary && (
          <details className="mt-6 border border-[var(--color-border)] bg-[var(--color-void)]">
            <summary className="cursor-pointer px-4 py-3 font-mono text-[10px] tracking-widest text-[var(--color-text-muted)] uppercase">
              AI Thesis Summary
            </summary>
            <div className="px-4 py-4 font-sans text-[14px] leading-relaxed text-[var(--color-text-secondary)] whitespace-pre-wrap">
              {typeof memo.ai_thesis_summary === "string"
                ? memo.ai_thesis_summary
                : JSON.stringify(memo.ai_thesis_summary, null, 2)}
            </div>
          </details>
        )}

        {memo.link_url ? (
          <footer className="mt-8 border-t border-[var(--color-border)] pt-4">
            <a
              href={memo.link_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[10px] tracking-widest text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text)]"
            >
              VIEW ON SUBSTACK ↗
            </a>
          </footer>
        ) : null}
      </article>
    </main>
  );
}
