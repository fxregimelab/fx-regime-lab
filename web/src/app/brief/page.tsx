import Link from "next/link";
import { Nav } from "@/components/shell/Nav";
import { Footer } from "@/components/shell/Footer";
import { createClient } from "@/lib/supabase/server";
import { getLatestBrief } from "@/lib/supabase/queries";
import { PAIRS } from "@/lib/constants";

export default async function BriefPage() {
  const supabase = await createClient();
  const brief = await getLatestBrief(supabase);

  const date = brief?.date ?? new Date().toISOString().slice(0, 10);

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Nav />
      <main className="flex-1 max-w-[1152px] mx-auto px-6 py-12 w-full">
        {/* Header */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] items-start gap-8 mb-10 pb-6 border-b border-shell-border">
          <div>
            <div className="flex items-center gap-2.5 mb-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-up" />
              <span className="font-mono text-[11px] text-[#888] tracking-[0.1em]">
                MORNING BRIEF
              </span>
              <span className="font-mono text-[11px] text-[#ccc]">{date}</span>
            </div>
            <h1 className="font-sans font-extrabold text-[32px] text-shell-text tracking-tight">
              Daily Brief — {date}
            </h1>
          </div>
          <Link
            href="/terminal"
            className="font-mono text-[11px] text-[#555] border border-shell-border px-4 py-2 whitespace-nowrap"
          >
            Open terminal →
          </Link>
        </div>

        {/* Brief text */}
        {brief?.brief_text ? (
          <div className="max-w-[720px]">
            <article className="prose prose-sm max-w-none">
              {brief.brief_text.split("\n").map((para, i) => {
                if (para.startsWith("## ")) {
                  return (
                    <h2
                      key={i}
                      className="font-sans font-bold text-lg text-shell-text tracking-tight mt-8 mb-3"
                    >
                      {para.replace("## ", "")}
                    </h2>
                  );
                }
                if (para.startsWith("# ")) {
                  return (
                    <h1
                      key={i}
                      className="font-sans font-extrabold text-2xl text-shell-text tracking-tight mt-8 mb-3"
                    >
                      {para.replace("# ", "")}
                    </h1>
                  );
                }
                if (para.startsWith("---")) {
                  return <hr key={i} className="border-shell-border my-6" />;
                }
                if (para.trim() === "") {
                  return <div key={i} className="h-2" />;
                }
                const parts = para.split(/(\*\*.*?\*\*)/g);
                return (
                  <p
                    key={i}
                    className="font-sans text-[15px] text-[#444] leading-relaxed mb-4"
                  >
                    {parts.map((part, j) => {
                      if (part.startsWith("**") && part.endsWith("**")) {
                        return (
                          <strong key={j} className="text-shell-text">
                            {part.slice(2, -2)}
                          </strong>
                        );
                      }
                      return <span key={j}>{part}</span>;
                    })}
                  </p>
                );
              })}
            </article>
          </div>
        ) : (
          <div className="py-20 text-center">
            <p className="font-mono text-sm text-shell-muted">
              No brief available for today.
            </p>
          </div>
        )}

        {/* Pair regimes */}
        {brief && (
          <div className="mt-12 pt-8 border-t border-shell-border">
            <p className="font-mono text-[10px] text-shell-muted tracking-[0.12em] mb-4">
              REGIME SNAPSHOT
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {PAIRS.map((p) => {
                const regimeKey = `${p.urlSlug}_regime` as const;
                const regime = (brief as unknown as Record<string, string>)[regimeKey];
                return (
                  <div
                    key={p.label}
                    className="border border-shell-border p-4"
                    style={{ borderTop: `3px solid ${p.pairColor}` }}
                  >
                    <p
                      className="font-mono text-xs font-bold mb-1"
                      style={{ color: p.pairColor }}
                    >
                      {p.display}
                    </p>
                    <p className="font-mono text-sm font-bold text-shell-text">
                      {regime ?? "—"}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="mt-10 pt-6 border-t border-shell-border">
          <p className="font-mono text-[10px] text-[#c0c0c0] tracking-wider leading-relaxed">
            RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE. ALL CALLS LOGGED
            PRIOR TO MARKET OPEN. OUTCOMES VALIDATED NEXT TRADING DAY.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
