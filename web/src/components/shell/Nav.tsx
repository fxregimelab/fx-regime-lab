"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";

export function Nav() {
  const currentRoute = usePathname();
  const [scrolled, setScrolled] = React.useState(false);
  const [terminalOpen, setTerminalOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Close dropdown on Escape
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTerminalOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const isActive = (href: string) =>
    href === "/" ? currentRoute === "/" : currentRoute.startsWith(href);

  const links = [
    { href: "/performance", label: "Performance" },
    { href: "/terminal", label: "Terminal", dropdown: true },
    { href: "/methodology", label: "Methodology" },
    { href: "/brief", label: "Brief" },
    { href: "/about", label: "About" },
  ];

  const terminalDropdown = [
    { href: "/terminal", label: "Overview" },
    { href: "/terminal/fx-regime", label: "FX-Regime Mosaic" },
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
          ? "bg-[var(--color-surface)] border-b border-[var(--color-border)]"
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
          {links.map((link) =>
            link.dropdown ? (
              <div
                key={link.href}
                ref={dropdownRef}
                className="relative"
                onMouseEnter={() => setTerminalOpen(true)}
                onMouseLeave={() => setTerminalOpen(false)}
              >
                <button
                  type="button"
                  onClick={() => setTerminalOpen((o) => !o)}
                  onFocus={() => setTerminalOpen(true)}
                  className={`relative px-3 py-1.5 font-sans text-[13px] transition-colors duration-300 bg-transparent border-0 cursor-pointer ${
                    isActive(link.href)
                      ? "text-[var(--color-text)]"
                      : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
                  }`}
                  aria-expanded={terminalOpen}
                  aria-haspopup="menu"
                  aria-controls="terminal-dropdown"
                >
                  {link.label}
                  {isActive(link.href) && (
                    <span className="absolute bottom-0 left-3 right-3 h-px bg-[var(--color-accent)] animate-line-grow" />
                  )}
                </button>

                {terminalOpen && (
                  <div className="absolute top-full left-1/2 -translate-x-1/2 pt-2">
                    <div
                      id="terminal-dropdown"
                      role="menu"
                      className="border border-[var(--color-border)] bg-[var(--color-surface)] min-w-[180px] py-2"
                    >
                      {terminalDropdown.map((item) => (
                        <Link
                          key={item.href}
                          href={item.href}
                          role="menuitem"
                          className={`block px-4 py-2 font-sans text-[13px] transition-colors duration-200 ${
                            currentRoute === item.href
                              ? "text-[var(--color-text)]"
                              : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-elevated)]"
                          }`}
                          onClick={() => setTerminalOpen(false)}
                        >
                          {item.label}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Link
                key={link.href}
                href={link.href}
                aria-current={isActive(link.href) ? "page" : undefined}
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
            ),
          )}
        </div>
      </nav>
    </header>
  );
}
