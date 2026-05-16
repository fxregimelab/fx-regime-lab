"use client";

import { LogoMark } from "@/components/ui/logo-mark";
import { ChevronDown, Menu, X } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import React, { useEffect, useRef, useState, useCallback } from "react";

const NAV_LINKS = [
  { label: "Methodology", href: "/methodology" },
  { label: "Brief", href: "/brief" },
  { label: "Track Record", href: "/performance" },
  { label: "About", href: "/about" },
];

const TERMINAL_ITEMS = [
  { label: "Overview", href: "/terminal" },
  { label: "EUR / USD", href: "/terminal/fx-regime/eurusd" },
  { label: "USD / JPY", href: "/terminal/fx-regime/usdjpy" },
  { label: "USD / INR", href: "/terminal/fx-regime/usdinr" },
  { label: "Calendar", href: "/terminal/calendar" },
  { label: "Memos", href: "/terminal/memos" },
];

export function Nav() {
  const router = useRouter();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const mobileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!dropdownOpen) return;
    const onClick = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [dropdownOpen]);

  useEffect(() => {
    if (!mobileOpen) return;
    const onClick = (e: MouseEvent) => {
      if (
        mobileRef.current &&
        !mobileRef.current.contains(e.target as Node)
      ) {
        setMobileOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [mobileOpen]);

  const handleTerminalClick = useCallback(
    (href: string) => {
      setDropdownOpen(false);
      setMobileOpen(false);
      router.push(href);
    },
    [router],
  );

  return (
    <header
      className="sticky top-0 z-[var(--z-sticky)] border-b border-[var(--color-border)] bg-[var(--color-void)]"
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
        {/* Left: LogoMark + Brand */}
        <a
          href="/"
          className="flex items-center gap-2.5 outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
          style={{ borderRadius: 2 }}
        >
          <LogoMark size={28} />
          <Image
            src="/logos/wordmark-without-bg.png"
            alt="FX Regime Lab"
            width={140}
            height={28}
            className="object-contain h-[22px] w-auto"
            priority
          />
        </a>

        {/* Right: Desktop Nav links */}
        <div className="hidden md:flex items-center gap-1">
          {/* Terminal dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              ref={triggerRef}
              type="button"
              onClick={() => setDropdownOpen((p) => !p)}
              aria-expanded={dropdownOpen}
              aria-haspopup="menu"
              className="flex items-center gap-1 px-3 py-1.5 text-[0.8125rem] text-[var(--color-text)] outline-none transition-colors hover:bg-[var(--color-surface)] focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
              style={{ borderRadius: 2 }}
            >
              Terminal
              <ChevronDown
                size={14}
                className="transition-transform"
                style={{
                  transform: dropdownOpen ? "rotate(180deg)" : "rotate(0deg)",
                }}
              />
            </button>

            {dropdownOpen && (
              <ul
                role="menu"
                className="absolute right-0 top-full mt-1 w-52 border border-[var(--color-border)] bg-[var(--color-surface)] py-1 shadow-lg outline-none"
                style={{ borderRadius: 2, zIndex: "var(--z-dropdown)" }}
              >
                {TERMINAL_ITEMS.map((item) => (
                  <li key={item.href}>
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => handleTerminalClick(item.href)}
                      className="w-full px-3 py-1.5 text-left text-[0.8125rem] text-[var(--color-text)] outline-none transition-colors hover:bg-[var(--color-elevated)] focus-visible:bg-[var(--color-elevated)]"
                      style={{ borderRadius: 2 }}
                    >
                      {item.label}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Remaining links */}
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="px-3 py-1.5 text-[0.8125rem] text-[var(--color-text)] outline-none transition-colors hover:bg-[var(--color-surface)] focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
              style={{ borderRadius: 2 }}
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Mobile hamburger */}
        <button
          type="button"
          onClick={() => setMobileOpen((p) => !p)}
          aria-expanded={mobileOpen}
          aria-label="Toggle navigation menu"
          className="md:hidden flex items-center justify-center w-10 h-10 text-[var(--color-text)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
          style={{ borderRadius: 2 }}
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
          <div className="px-4 py-3 space-y-1">
            <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase px-3 py-1.5">
              Terminal
            </p>
            {TERMINAL_ITEMS.map((item) => (
              <button
                key={item.href}
                type="button"
                onClick={() => handleTerminalClick(item.href)}
                className="w-full text-left px-3 py-2 text-[0.8125rem] text-[var(--color-text)] outline-none transition-colors hover:bg-[var(--color-elevated)] focus-visible:bg-[var(--color-elevated)]"
                style={{ borderRadius: 2 }}
              >
                {item.label}
              </button>
            ))}
            <div className="border-t border-[var(--color-border)] my-2" />
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2 text-[0.8125rem] text-[var(--color-text)] outline-none transition-colors hover:bg-[var(--color-elevated)] focus-visible:ring-2 focus-visible:ring-[var(--color-text)]"
                style={{ borderRadius: 2 }}
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}

export default Nav;
