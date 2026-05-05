"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function Nav() {
  const currentRoute = usePathname();
  const [scrolled, setScrolled] = React.useState(false);

  React.useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const isActive = (href: string) =>
    href === "/" ? currentRoute === "/" : currentRoute.startsWith(href);

  const links = [
    { href: "/", label: "Home" },
    { href: "/brief", label: "Brief" },
    { href: "/methodology", label: "Methodology" },
    { href: "/about", label: "About" },
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

          <Link
            href="/terminal"
            className="ml-4 px-4 py-1.5 bg-[var(--color-elevated)] text-[var(--color-text)] font-sans text-[12px] tracking-wide border border-[var(--color-border)] transition-all duration-300 hover:bg-[var(--color-surface)] hover:border-[var(--color-border)]"
          >
            Terminal
          </Link>
        </div>
      </nav>
    </header>
  );
}
