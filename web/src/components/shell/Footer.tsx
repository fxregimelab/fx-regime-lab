"use client";

import Link from "next/link";
import React from "react";

export function Footer() {
  const [email, setEmail] = React.useState("");

  const handleSubscribe = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: wire to newsletter API
    setEmail("");
  };

  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-void)]">
      <div className="max-w-[1152px] mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
          {/* Navigation */}
          <div>
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
              Navigation
            </p>
            <div className="flex flex-col gap-2.5">
              {[
                ["/performance", "Performance"],
                ["/terminal", "Terminal"],
                ["/methodology", "Methodology"],
                ["/brief", "Brief"],
              ].map(([href, label]) => (
                <Link
                  key={href}
                  href={href}
                  className="font-sans text-[13px] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors duration-300"
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>

          {/* Transparency */}
          <div>
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
              Transparency
            </p>
            <div className="flex flex-col gap-2.5">
              {[
                ["/about", "About"],
                ["/performance", "Track Record"],
                ["/audit", "Audit"],
              ].map(([href, label]) => (
                <Link
                  key={href}
                  href={href}
                  className="font-sans text-[13px] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors duration-300"
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>

          {/* Distribution */}
          <div>
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
              Distribution
            </p>
            <div className="flex flex-col gap-2.5 mb-6">
              <a
                href="https://fxregimelab.substack.com"
                target="_blank"
                rel="noopener noreferrer"
                className="font-sans text-[13px] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors duration-300"
              >
                Substack
              </a>
            </div>

            <form onSubmit={handleSubscribe} className="flex flex-col gap-2">
              <label
                htmlFor="footer-email"
                className="font-mono text-[10px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase"
              >
                Subscribe to briefs
              </label>
              <div className="flex gap-2">
                <input
                  id="footer-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="flex-1 bg-[var(--color-surface)] border border-[var(--color-border)] px-3 py-2 font-sans text-[13px] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] outline-none focus:border-[var(--color-accent)] transition-colors duration-300"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-[var(--color-elevated)] border border-[var(--color-border)] font-sans text-[12px] text-[var(--color-text)] tracking-wide transition-all duration-300 hover:bg-[var(--color-text)] hover:text-[var(--color-void)] hover:border-[var(--color-text)]"
                >
                  Subscribe
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="mt-16 pt-6 border-t border-[var(--color-border)] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <p className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider">
            Research and learning only. Not investment advice.
          </p>
          <p className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider">
            Shreyash Sakhare — Discretionary Macro Research
          </p>
        </div>
      </div>
    </footer>
  );
}
