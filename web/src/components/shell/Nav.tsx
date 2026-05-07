"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown } from "lucide-react";
import { LogoMark } from "@/components/ui/logo-mark";

const NAV_LINKS = [
  { label: "Performance", href: "/performance" },
  { label: "Methodology", href: "/methodology" },
  { label: "Brief", href: "/brief" },
  { label: "About", href: "/about" },
];

const TERMINAL_ITEMS = [
  { label: "Overview", href: "/terminal" },
  { label: "Mosaic", href: "/terminal/mosaic" },
  { label: "EUR / USD", href: "/terminal/eur-usd" },
  { label: "USD / JPY", href: "/terminal/usd-jpy" },
  { label: "USD / INR", href: "/terminal/usd-inr" },
  { label: "Calendar", href: "/terminal/calendar" },
  { label: "Memos", href: "/terminal/memos" },
  { label: "Alpha Ledger", href: "/terminal/alpha-ledger" },
];

export function Nav() {
  const router = useRouter();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && dropdownOpen) {
        e.preventDefault();
        setDropdownOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [dropdownOpen]);

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

  const handleTerminalClick = useCallback(
    (href: string) => {
      setDropdownOpen(false);
      router.push(href);
    },
    [router]
  );

  return (
    <header
      className="sticky top-0 z-[var(--z-sticky)] border-b border-[#e5e5e5] bg-[#ffffff]"
      style={{
        height: 64,
        transition: "box-shadow 150ms ease-out",
        boxShadow: scrolled ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
      }}
    >
      <nav
        className="mx-auto flex h-full max-w-[1440px] items-center justify-between px-4"
        aria-label="Main"
      >
        {/* Left: LogoMark + Brand */}
        <a
          href="/"
          className="flex items-center gap-2.5 outline-none focus-visible:ring-2 focus-visible:ring-[#0a0a0a]"
          style={{ borderRadius: 2 }}
        >
          <LogoMark size={28} color="#0a0a0a" />
          <span className="text-[0.875rem] font-medium tracking-tight text-[#0a0a0a]">
            FX Regime Lab
          </span>
        </a>

        {/* Right: Nav links */}
        <div className="flex items-center gap-1">
          {/* Performance */}
          <a
            href="/performance"
            className="px-3 py-1.5 text-[0.8125rem] text-[#0a0a0a] outline-none transition-colors hover:bg-[rgba(28,25,23,0.04)] focus-visible:ring-2 focus-visible:ring-[#0a0a0a]"
            style={{ borderRadius: 2 }}
          >
            Performance
          </a>

          {/* Terminal dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              ref={triggerRef}
              type="button"
              onClick={() => setDropdownOpen((p) => !p)}
              aria-expanded={dropdownOpen}
              aria-haspopup="menu"
              className="flex items-center gap-1 px-3 py-1.5 text-[0.8125rem] text-[#0a0a0a] outline-none transition-colors hover:bg-[rgba(28,25,23,0.04)] focus-visible:ring-2 focus-visible:ring-[#0a0a0a]"
              style={{ borderRadius: 2 }}
            >
              Terminal
              <ChevronDown
                size={14}
                className="transition-transform"
                style={{ transform: dropdownOpen ? "rotate(180deg)" : "rotate(0deg)" }}
              />
            </button>

            {dropdownOpen && (
              <ul
                role="menu"
                className="absolute right-0 top-full mt-1 w-52 border border-[#d6d3d1] bg-[#ffffff] py-1 shadow-lg outline-none"
                style={{ borderRadius: 2, zIndex: "var(--z-dropdown)" }}
              >
                {TERMINAL_ITEMS.map((item) => (
                  <li key={item.href} role="none">
                    <button
                      role="menuitem"
                      onClick={() => handleTerminalClick(item.href)}
                      className="w-full px-3 py-1.5 text-left text-[0.8125rem] text-[#1c1917] outline-none transition-colors hover:bg-[rgba(28,25,23,0.04)] focus-visible:bg-[rgba(28,25,23,0.08)]"
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
          {NAV_LINKS.slice(1).map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="px-3 py-1.5 text-[0.8125rem] text-[#0a0a0a] outline-none transition-colors hover:bg-[rgba(28,25,23,0.04)] focus-visible:ring-2 focus-visible:ring-[#0a0a0a]"
              style={{ borderRadius: 2 }}
            >
              {link.label}
            </a>
          ))}
        </div>
      </nav>
    </header>
  );
}

export default Nav;
