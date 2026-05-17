"use client";

import { LogoMark } from "@/components/ui/logo-mark";
import { fmtChg } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import type { LatestSignal } from "@/lib/supabase/queries";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface TerminalNavProps {
  signals?: Record<string, LatestSignal>;
}

export function TerminalNav({ signals }: TerminalNavProps) {
  const pathname = usePathname();
  const activeSlug = pathname.split("/").pop();
  const pair = PAIRS.find((p) => activeSlug === p.urlSlug);

  return (
    <header className="border-b border-[var(--color-border)] bg-[var(--color-void)] sticky top-0 z-50">
      {/* Brand bar */}
      <div className="border-b border-[var(--color-border-subtle)] px-6 h-[38px] flex items-center justify-between max-w-[1152px] mx-auto">
        <div className="flex items-center gap-2.5">
          <LogoMark size={16} />
          <span className="font-sans font-bold text-[13px] text-[var(--color-text)] tracking-tight">
            FX Regime Lab
          </span>
          <span className="font-mono text-[10px] text-[var(--color-text-dim)] ml-1">
            / Terminal
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-[5px] h-[5px] rounded-full bg-bullish" />
          <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
            LIVE
          </span>
        </div>
      </div>

      {/* Breadcrumb + pair tabs */}
      <div className="max-w-[1152px] mx-auto px-6 h-[38px] flex items-center justify-between">
        <div className="flex items-center gap-1.5 font-mono text-[10px]">
          <Link
            href="/"
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
          >
            shell
          </Link>
          <span className="text-[var(--color-text-dim)]">/</span>
          <Link
            href="/terminal"
            className={`transition-colors ${
              pathname === "/terminal"
                ? "text-[var(--color-text)]"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            }`}
          >
            terminal
          </Link>
          {pathname.includes("/fx-regime") && (
            <>
              <span className="text-[var(--color-text-dim)]">/</span>
              <Link
                href="/terminal"
                className="text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
              >
                fx-regime
              </Link>
            </>
          )}
          {pair && (
            <>
              <span className="text-[var(--color-text-dim)]">/</span>
              <span className="font-semibold" style={{ color: pair.pairColor }}>
                {pair.urlSlug}
              </span>
            </>
          )}
        </div>

        <div className="flex gap-0.5 overflow-x-auto">
          {PAIRS.map((p) => {
            const active = pathname.includes(p.urlSlug);
            const sig = signals?.[p.label];
            const chgPct = sig?.day_change_pct;
            const chg = chgPct != null ? fmtChg(chgPct) : null;
            return (
              <Link
                key={p.label}
                href={`/terminal/fx-regime/${p.urlSlug}`}
                className={`flex items-center gap-2 px-3 py-1 font-mono text-[10px] transition-all -mb-[1px] ${
                  active
                    ? "bg-[var(--color-elevated)]"
                    : "bg-transparent hover:bg-[var(--color-surface)]"
                }`}
                style={{
                  borderBottom: active
                    ? `2px solid ${p.pairColor}`
                    : "2px solid transparent",
                }}
              >
                <span className="font-bold" style={{ color: p.pairColor }}>
                  {p.display}
                </span>
                {sig && chgPct != null && (
                  <span style={{ color: chg?.color }}>{chg?.str}</span>
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </header>
  );
}
