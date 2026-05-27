"use client";

import { LogoMark } from "@/components/ui/logo-mark";
import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useEffect, useRef, useState } from "react";

/* ─── Nav structure ─────────────────────────────────────────────────── */

interface NavItem {
  label: string;
  href: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Framework",
    items: [
      { label: "Methodology", href: "/methodology" },
      { label: "How It Works", href: "/methodology#overview" },
      { label: "Data Sources", href: "/methodology#data-sources" },
    ],
  },
  {
    label: "Terminal",
    items: [
      { label: "Overview", href: "/desk" },
      { label: "EUR / USD", href: "/desk/fx-regime/eurusd" },
      { label: "USD / JPY", href: "/desk/fx-regime/usdjpy" },
      { label: "USD / INR", href: "/desk/fx-regime/usdinr" },
    ],
  },
  {
    label: "Validation",
    items: [
      { label: "Track Record", href: "/track-record" },
      { label: "Limitations", href: "/limitations" },
    ],
  },
  {
    label: "About",
    items: [
      { label: "Team", href: "/about" },
      { label: "Our Journey", href: "/journey" },
      { label: "Principles", href: "/about#principles" },
      { label: "Contact", href: "/about#contact" },
    ],
  },
];

const FLAT_LINKS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

/* ─── Component ─────────────────────────────────────────────────────── */

export function Nav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const mobileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!mobileOpen) return;
    const onClick = (e: MouseEvent) => {
      if (mobileRef.current && !mobileRef.current.contains(e.target as Node)) {
        setMobileOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [mobileOpen]);

  // Close mobile menu on route change
  // biome-ignore lint/correctness/useExhaustiveDependencies: pathname triggers on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const isActive = (href: string) => {
    if (!pathname) return false;
    if (href === "/") return pathname === "/";
    // Strip hash for comparison
    const hrefPath = href.split("#")[0];
    return pathname === hrefPath || pathname.startsWith(`${hrefPath}/`);
  };

  return (
    <header
      className="sticky top-0 z-[var(--z-sticky)] border-b border-[var(--color-border)] bg-[var(--color-void)]/95 backdrop-blur-sm"
      style={{
        height: 64,
        transition: "box-shadow 150ms ease-out",
        boxShadow: scrolled ? "0 1px 3px rgba(0,0,0,0.4)" : "none",
      }}
    >
      <nav
        className="mx-auto flex h-full max-w-[1440px] items-center justify-between px-4"
        aria-label="Main"
      >
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
          style={{ borderRadius: 2 }}
        >
          <LogoMark size={28} />
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-0.5">
          {NAV_GROUPS.map((group) => (
            <div key={group.label} className="relative group">
              <button
                type="button"
                className="px-3 py-1.5 text-[0.8125rem] text-[var(--color-text)] outline-none transition-colors hover:bg-[var(--color-surface)] focus-visible:ring-2 focus-visible:ring-[var(--color-text)] rounded-sm"
                onClick={() =>
                  setOpenDropdown(
                    openDropdown === group.label ? null : group.label,
                  )
                }
                onMouseEnter={() => setOpenDropdown(group.label)}
                aria-expanded={openDropdown === group.label}
              >
                {group.label}
              </button>
              {/* Dropdown */}
              <ul
                className={`absolute right-0 top-full mt-1 w-48 border border-[var(--color-border)] bg-[var(--color-surface)] py-1 shadow-lg outline-none transition-all duration-150 ${openDropdown === group.label ? "opacity-100 visible" : "opacity-0 invisible"}`}
                style={{ borderRadius: 2, zIndex: "var(--z-dropdown)" }}
                onMouseLeave={() => setOpenDropdown(null)}
              >
                {group.items.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      aria-current={isActive(item.href) ? "page" : undefined}
                      className={`block w-full px-3 py-1.5 text-left text-[0.8125rem] outline-none transition-colors duration-150 hover:bg-[var(--color-elevated)] focus-visible:bg-[var(--color-elevated)] hover:text-[var(--color-brand-amber)] ${
                        isActive(item.href)
                          ? "text-[var(--color-brand-amber)]"
                          : "text-[var(--color-text)]"
                      }`}
                      style={{ borderRadius: 2 }}
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Mobile hamburger */}
        <button
          type="button"
          onClick={() => setMobileOpen((p) => !p)}
          aria-expanded={mobileOpen}
          aria-label="Toggle navigation menu"
          className="md:hidden flex items-center justify-center w-10 h-10 text-[var(--color-text)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-text)] rounded-sm"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </nav>

      {/* Mobile menu */}
      {mobileOpen && (
        <div
          ref={mobileRef}
          className="md:hidden absolute top-full left-0 right-0 border-b border-[var(--color-border)] bg-[var(--color-surface)] shadow-lg"
          style={{ zIndex: "var(--z-dropdown)" }}
        >
          <div className="px-4 py-3 space-y-3">
            {NAV_GROUPS.map((group) => (
              <div key={group.label}>
                <p className="font-sans text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase px-3 py-1.5">
                  {group.label}
                </p>
                <div className="space-y-0.5">
                  {group.items.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`block px-3 py-2 text-[0.8125rem] outline-none transition-colors hover:bg-[var(--color-elevated)] focus-visible:bg-[var(--color-elevated)] rounded-sm ${
                        isActive(item.href)
                          ? "text-[var(--color-brand-amber)]"
                          : "text-[var(--color-text)]"
                      }`}
                    >
                      {item.label}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}

export default Nav;
