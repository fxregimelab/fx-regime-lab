"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useScrollReveal } from "@/hooks/useScrollReveal";

export function Nav() {
  const currentRoute = usePathname();
  const [scrolled, setScrolled] = React.useState(false);
  const [terminalOpen, setTerminalOpen] = React.useState(false);

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useScrollReveal();

  const isActive = (href: string) =>
    href === "/" ? currentRoute === "/" : currentRoute.startsWith(href);

  const links = [
    { href: "/performance", label: "Performance" },
    { href: "/methodology", label: "Methodology" },
    { href: "/brief", label: "Brief" },
    { href: "/about", label: "About" },
  ];

  const terminalDropdown = [
    { href: "/terminal", label: "Overview" },
    { href: "/terminal/fx-regime/eurusd", label: "EUR/USD" },
    { href: "/terminal/fx-regime/usdjpy", label: "USD/JPY" },
    { href: "/terminal/fx-regime/usdinr", label: "USD/INR" },
    { href: "/terminal/calendar", label: "Calendar" },
    { href: "/terminal/memos", label: "Memos" },
    { href: "/terminal/performance", label: "Alpha Ledger" },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-[90] transition-all duration-500 ${
        scrolled
          ? "bg-[var(--color-surface)]/80 backdrop-blur-md border-b border-[var(--color-border)]"
          : "bg-transparent"
      }`}
    >
      <nav className="max-w-[1152px] mx-auto px-6 h-[56px] flex items-center justify-between">
        <Link
          href="/"
          className="font-mono text-[11px] tracking-[0.2em] text-[var(--color-text)] uppercase font-medium"
        >
          FX Regime Lab
        </Link>

        <div className="flex items-center gap-1">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`relative px-3 py-1.5 font-sans text-[13px] transition-colors duration-300 ${
                isActive(link.href)
                  ? "text-[var(--color-text)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
              }`}
            >
              {link.label}
              {isActive(link.href) && (
                <span className="absolute bottom-0 left-3 right-3 h-px bg-[var(--color-accent)] animate-line-grow" />
              )}
            </Link>
          ))}

          {/* Terminal dropdown */}
          <div
            className="relative"
            onMouseEnter={() => setTerminalOpen(true)}
            onMouseLeave={() => setTerminalOpen(false)}
          >
            <Link
              href="/terminal"
              className={`relative px-3 py-1.5 font-sans text-[13px] transition-colors duration-300 ${
                isActive("/terminal")
                  ? "text-[var(--color-text)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
              }`}
            >
              Terminal
              {isActive("/terminal") && (
                <span className="absolute bottom-0 left-3 right-3 h-px bg-[var(--color-accent)] animate-line-grow" />
              )}
            </Link>

            {terminalOpen && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 pt-2">
                <div className="border border-[var(--color-border)] bg-[var(--color-surface)]/95 backdrop-blur-md min-w-[180px] py-2 shadow-lg">
                  {terminalDropdown.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`block px-4 py-2 font-sans text-[13px] transition-colors duration-200 ${
                        currentRoute === item.href
                          ? "text-[var(--color-text)]"
                          : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-elevated)]"
                      }`}
                    >
                      {item.label}
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
}
