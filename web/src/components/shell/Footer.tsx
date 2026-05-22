"use client";

import Link from "next/link";
import type React from "react";
import { type FormEvent, useState } from "react";

const NAV_LINKS = [
  { label: "Terminal", href: "/terminal" },
  { label: "Methodology", href: "/methodology" },
  { label: "Brief", href: "/brief" },
  { label: "Track Record", href: "/track-record" },
  { label: "About", href: "/about" },
];

const TRANSPARENCY_LINKS = [{ label: "Methodology", href: "/methodology" }];

export function Footer() {
  const [email, setEmail] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const url = new URL("https://fxregimelab.substack.com/");
    url.searchParams.set("utm_source", "website");
    url.searchParams.set("utm_campaign", "footer");
    if (email.trim()) {
      url.searchParams.set("email", email.trim());
    }
    window.open(url.toString(), "_blank", "noopener,noreferrer");
  };

  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-void)]">
      <div className="mx-auto max-w-[1440px] px-4 py-10">
        {/* 3-column grid */}
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {/* Column 1: Navigation */}
          <div>
            <h3 className="mb-3 text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Navigation
            </h3>
            <ul className="space-y-1.5">
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-[0.8125rem] text-[var(--color-text-secondary)] outline-none transition-all duration-200 hover:text-[var(--color-text)] glow-text focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
                    style={{ borderRadius: 2 }}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 2: Transparency */}
          <div>
            <h3 className="mb-3 text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Transparency
            </h3>
            <ul className="space-y-1.5">
              {TRANSPARENCY_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-[0.8125rem] text-[var(--color-text-secondary)] outline-none transition-all duration-200 hover:text-[var(--color-text)] glow-text focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
                    style={{ borderRadius: 2 }}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 3: Subscribe */}
          <div>
            <h3 className="mb-3 text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
              Subscribe
            </h3>
            <p className="mb-3 text-[0.8125rem] text-[var(--color-text-secondary)]">
              Weekly regime briefs delivered to your inbox.
            </p>
            <form
              onSubmit={handleSubmit}
              className="flex flex-col sm:flex-row gap-2"
            >
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@domain.com"
                className="flex-1 border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[0.8125rem] text-[var(--color-text)] placeholder:text-[var(--color-text-dim)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
                style={{ borderRadius: 2 }}
              />
              <button
                type="submit"
                className="border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 text-[0.8125rem] font-medium text-[var(--color-text)] outline-none transition-all duration-200 hover:bg-[var(--color-elevated)] glow-hover focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
                style={
                  {
                    "--glow-color": "rgba(231, 229, 228, 0.12)",
                    borderRadius: 2,
                  } as React.CSSProperties
                }
              >
                Join
              </button>
            </form>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-[var(--color-border)] pt-6 md:flex-row">
          <p className="text-[0.6875rem] text-[var(--color-text-dim)]">
            © {new Date().getFullYear()} FX Regime Lab. Research and learning
            only. Not investment advice.
          </p>
          <p className="text-[0.6875rem] text-[var(--color-text-dim)]">
            Built with institutional discipline. Validated out-of-sample.
          </p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
