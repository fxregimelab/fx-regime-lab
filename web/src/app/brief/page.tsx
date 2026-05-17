import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import { normalizeProp } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import { getDriverTag } from "@/lib/pairProfiles";
import { getLatestBrief } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Daily Brief | FX Regime Lab",
  description:
    "Institutional morning desk brief. Macro summary, pair regime calls, and tactical execution notes.",
};

function DollarDominanceIndex({
  brief,
}: { brief: { pair_regimes?: unknown; dollar_dominance?: number | null } }) {
  const pairRegimes = brief.pair_regimes as Record<string, string> | null;

  let usdStrength = 0;
  let usdWeakness = 0;
  let neutral = 0;

  for (const p of PAIRS) {
    const regime = pairRegimes?.[p.label] ?? pairRegimes?.[p.urlSlug] ?? "";
    const u = regime.toUpperCase();
    if (
      u.includes("STRENGTH") ||
      u.includes("APPRECIATION") ||
      u.includes("DOLLAR_ON") ||
      u.includes("RISK_OFF")
    ) {
      usdStrength++;
    } else if (
      u.includes("WEAKNESS") ||
      u.includes("DEPRECIATION") ||
      u.includes("DOLLAR_OFF") ||
      u.includes("RISK_ON")
    ) {
      usdWeakness++;
    } else {
      neutral++;
    }
  }

  const total = usdStrength + usdWeakness + neutral;
  if (total === 0) return null;

  const strengthPct = (usdStrength / total) * 100;
  const weaknessPct = (usdWeakness / total) * 100;
  const neutralPct = (neutral / total) * 100;

  const dd = normalizeProp(brief.dollar_dominance);
  const dominanceLabel =
    dd != null ? `${(dd * 100).toFixed(0)}%` : `${Math.round(strengthPct)}%`;

  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
      <div className="flex items-center justify-between mb-4">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Dollar Dominance
        </p>
        <span className="font-mono text-[11px] text-[var(--color-text)] font-medium">
          {dominanceLabel}
        </span>
      </div>
      <div className="flex h-2 bg-[var(--color-elevated)] overflow-hidden">
        {usdStrength > 0 && (
          <div
            className="h-full bg-[var(--color-up)]"
            style={{ width: `${strengthPct}%` }}
          />
        )}
        {neutral > 0 && (
          <div
            className="h-full bg-[var(--color-text-muted)]"
            style={{ width: `${neutralPct}%` }}
          />
        )}
        {usdWeakness > 0 && (
          <div
            className="h-full bg-[var(--color-down)]"
            style={{ width: `${weaknessPct}%` }}
          />
        )}
      </div>
      <div className="flex gap-6 mt-3">
        <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
          <span className="inline-block w-1.5 h-1.5 bg-[var(--color-up)] mr-1.5" />
          USD STRONG: {usdStrength}
        </span>
        <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
          <span className="inline-block w-1.5 h-1.5 bg-[var(--color-text-muted)] mr-1.5" />
          NEUTRAL: {neutral}
        </span>
        <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
          <span className="inline-block w-1.5 h-1.5 bg-[var(--color-down)] mr-1.5" />
          USD WEAK: {usdWeakness}
        </span>
      </div>
    </div>
  );
}

export default async function BriefPage() {
  const supabase = await createClient();
  const brief = await getLatestBrief(supabase);

  const date = brief?.date ?? new Date().toISOString().slice(0, 10);

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <AuditTrailBannerServer variant="shell" />
      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full"
      >
        {/* Header */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] items-start gap-8 mb-10 pb-6 border-b border-[var(--color-border)]">
          <div>
            <div className="flex items-center gap-2.5 mb-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)] animate-gentle-pulse" />
              <span className="font-mono text-[11px] text-[var(--color-text-muted)] tracking-[0.1em]">
                MORNING BRIEF
              </span>
              <span className="font-mono text-[11px] text-[var(--color-text-dim)]">
                {date}
              </span>
            </div>
            <h1 className="font-sans font-semibold text-[32px] text-[var(--color-text)] tracking-tight">
              Daily Brief — {date}
            </h1>
          </div>
          <Link
            href="/terminal"
            className="font-mono text-[11px] text-[var(--color-text-secondary)] border border-[var(--color-border)] px-4 py-2 whitespace-nowrap transition-all duration-300 hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)] hover:border-[var(--color-border)]"
          >
            Open terminal →
          </Link>
        </div>

        {/* Brief text */}
        {brief?.brief_text ? (
          <div className="max-w-[720px]">
            <article className="prose prose-sm max-w-none">
              {brief.brief_text.split("\n").map((para) => {
                const paraKey = para.slice(0, 20) || "empty";
                if (para.startsWith("## ")) {
                  return (
                    <h2
                      key={`h2-${paraKey}`}
                      className="font-sans font-semibold text-lg text-[var(--color-text)] tracking-tight mt-8 mb-3"
                    >
                      {para.replace("## ", "")}
                    </h2>
                  );
                }
                if (para.startsWith("# ")) {
                  return (
                    <h1
                      key={`h1-${paraKey}`}
                      className="font-sans font-semibold text-2xl text-[var(--color-text)] tracking-tight mt-8 mb-3"
                    >
                      {para.replace("# ", "")}
                    </h1>
                  );
                }
                if (para.startsWith("---")) {
                  return (
                    <hr
                      key={`hr-${paraKey}`}
                      className="border-[var(--color-border)] my-6"
                    />
                  );
                }
                if (para.trim() === "") {
                  return <div key={`sp-${paraKey}`} className="h-2" />;
                }
                // Bullet list
                if (para.trim().startsWith("- ")) {
                  return (
                    <ul
                      key={`ul-${paraKey}`}
                      className="list-disc list-inside mb-4"
                    >
                      {para.split("\n").map((line) => {
                        const trimmed = line.trim();
                        if (!trimmed.startsWith("- ")) return null;
                        const itemKey = trimmed.slice(0, 20);
                        const itemText = trimmed.slice(2);
                        const itemParts = itemText.split(/(\*\*.*?\*\*)/g);
                        return (
                          <li
                            key={`li-${itemKey}`}
                            className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-1"
                          >
                            {itemParts.map((part) => {
                              const pk = part.slice(0, 10) || "empty";
                              if (
                                part.startsWith("**") &&
                                part.endsWith("**")
                              ) {
                                return (
                                  <strong
                                    key={`sb-${pk}`}
                                    className="text-[var(--color-text)]"
                                  >
                                    {part.slice(2, -2)}
                                  </strong>
                                );
                              }
                              return <span key={`ssp-${pk}`}>{part}</span>;
                            })}
                          </li>
                        );
                      })}
                    </ul>
                  );
                }
                const parts = para.split(/(\*\*.*?\*\*)/g);
                return (
                  <p
                    key={`p-${paraKey}`}
                    className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-4"
                  >
                    {parts.map((part) => {
                      const partKey = part.slice(0, 10) || "empty";
                      if (part.startsWith("**") && part.endsWith("**")) {
                        return (
                          <strong
                            key={`s-${partKey}`}
                            className="text-[var(--color-text)]"
                          >
                            {part.slice(2, -2)}
                          </strong>
                        );
                      }
                      return <span key={`sp-${partKey}`}>{part}</span>;
                    })}
                  </p>
                );
              })}
            </article>
          </div>
        ) : (
          <div className="py-20 text-center">
            <p className="font-mono text-sm text-[var(--color-text-muted)]">
              No brief available for today.
            </p>
          </div>
        )}

        {/* Dollar Dominance Index */}
        {brief && (
          <div className="mt-10">
            <DollarDominanceIndex brief={brief} />
          </div>
        )}

        {/* Pair regimes */}
        {brief && (
          <div className="mt-10 pt-8 border-t border-[var(--color-border)]">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
              Regime Snapshot
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {PAIRS.map((p) => {
                // Read from JSON first, fallback to hardcoded column
                const pairRegimes = brief.pair_regimes as Record<
                  string,
                  string
                > | null;
                const regime =
                  pairRegimes?.[p.label] ??
                  pairRegimes?.[p.urlSlug] ??
                  (brief as unknown as Record<string, string>)[
                    `${p.urlSlug}_regime`
                  ] ??
                  "—";
                const driverTag = getDriverTag(p.label);
                return (
                  <div
                    key={p.label}
                    className="border border-[var(--color-border)] bg-[var(--color-surface)] p-5 hover-lift relative"
                  >
                    {/* Pair-colored top accent */}
                    <div
                      className="absolute top-0 left-0 right-0 h-[2px]"
                      style={{ backgroundColor: p.pairColor }}
                    />
                    <div className="flex items-center justify-between mb-2">
                      <p
                        className="font-mono text-[10px] tracking-[0.15em] uppercase font-bold"
                        style={{ color: p.pairColor }}
                      >
                        {p.display}
                      </p>
                      <span className="font-mono text-[9px] px-2 py-0.5 bg-[var(--color-elevated)] text-[var(--color-text-muted)] tracking-wider">
                        {driverTag}
                      </span>
                    </div>
                    <p className="font-mono text-[13px] font-medium text-[var(--color-text)]">
                      {regime.replace(/_/g, " ")}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="mt-10 pt-6 border-t border-[var(--color-border)]">
          <p className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider leading-relaxed">
            RESEARCH ONLY. NOT INVESTMENT ADVICE. ALL CALLS LOGGED PRIOR TO
            MARKET OPEN. OUTCOMES VALIDATED AT T+5 AND T+20.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
