"use client";

import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, FileText, BarChart3, Terminal, BookOpen, Mail, Info, Calendar, Sparkles, Newspaper } from "lucide-react";
import { BinaryResolve } from "@/components/ui/BinaryResolve";

interface CommandItem {
  id: string;
  label: string;
  path: string;
  icon: React.ReactNode;
  section: string;
}

const ALL_ITEMS: CommandItem[] = [
  // Pages
  { id: "home", label: "Home", path: "/", icon: <FileText size={14} />, section: "Pages" },
  { id: "performance", label: "Performance", path: "/performance", icon: <BarChart3 size={14} />, section: "Pages" },
  { id: "methodology", label: "Methodology", path: "/methodology", icon: <BookOpen size={14} />, section: "Pages" },
  { id: "brief", label: "Brief", path: "/brief", icon: <Newspaper size={14} />, section: "Pages" },
  { id: "about", label: "About", path: "/about", icon: <Info size={14} />, section: "Pages" },
  // Terminal
  { id: "terminal-overview", label: "Terminal Overview", path: "/terminal", icon: <Terminal size={14} />, section: "Terminal" },
  { id: "terminal-fx-regime", label: "FX Regime Mosaic", path: "/terminal/fx-regime", icon: <Sparkles size={14} />, section: "Terminal" },
  { id: "terminal-calendar", label: "Calendar", path: "/terminal/calendar", icon: <Calendar size={14} />, section: "Terminal" },
  { id: "terminal-memos", label: "Memos", path: "/terminal/memos", icon: <Mail size={14} />, section: "Terminal" },
  // Pair desks
  { id: "desk-eurusd", label: "EUR / USD Desk", path: "/terminal/fx-regime/eur-usd", icon: <Terminal size={14} />, section: "Pair Desks" },
  { id: "desk-usdjpy", label: "USD / JPY Desk", path: "/terminal/fx-regime/usd-jpy", icon: <Terminal size={14} />, section: "Pair Desks" },
  { id: "desk-usdinr", label: "USD / INR Desk", path: "/terminal/fx-regime/usd-inr", icon: <Terminal size={14} />, section: "Pair Desks" },
];

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [teleportTarget, setTeleportTarget] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return ALL_ITEMS;
    return ALL_ITEMS.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.path.toLowerCase().includes(q) ||
        item.section.toLowerCase().includes(q)
    );
  }, [query]);

  // Reset selection when filter changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Global ⌘K / Ctrl+K toggle
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Escape to close
  useEffect(() => {
    if (!open) return;
    const down = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setOpen(false);
        setQuery("");
        setTeleportTarget(null);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open]);

  // Keyboard navigation (↑↓↵)
  useEffect(() => {
    if (!open) return;
    const down = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % filtered.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filtered.length) % filtered.length);
      } else if (e.key === "Enter") {
        e.preventDefault();
        const item = filtered[selectedIndex];
        if (item) {
          handleSelect(item);
        }
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, filtered, selectedIndex]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      const id = requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
      return () => cancelAnimationFrame(id);
    }
  }, [open]);

  // Scroll selected item into view
  useEffect(() => {
    const el = itemRefs.current[selectedIndex];
    if (el) {
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [selectedIndex]);

  const handleSelect = useCallback(
    (item: CommandItem) => {
      setTeleportTarget(item.path);
      setTimeout(() => {
        setOpen(false);
        setQuery("");
        setSelectedIndex(0);
        setTeleportTarget(null);
        router.push(item.path);
      }, 150);
    },
    [router]
  );

  if (!open) return null;

  // Group by section
  const grouped: Record<string, CommandItem[]> = {};
  for (const item of filtered) {
    if (!grouped[item.section]) grouped[item.section] = [];
    grouped[item.section].push(item);
  }
  const sections = Object.keys(grouped);

  return (
    <div
      className="fixed inset-0 z-[var(--z-command-palette)] flex items-start justify-center pt-[20vh]"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={() => {
          setOpen(false);
          setQuery("");
          setTeleportTarget(null);
        }}
      />

      {/* Modal */}
      <div
        className="relative w-full max-w-lg overflow-hidden border border-[var(--shell-border)] bg-[var(--shell-bg-elevated)] shadow-lg"
        style={{ borderRadius: 2 }}
      >
        {/* Search input */}
        <div className="flex items-center gap-2 border-b border-[var(--shell-border-subtle)] px-3">
          <Search size={14} className="text-[var(--shell-fg-dim)]" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search pages and desks…"
            className="w-full bg-transparent py-3 text-[0.8125rem] text-[var(--shell-fg)] outline-none placeholder:text-[var(--shell-fg-dim)]"
            aria-label="Command palette search"
          />
          {/* ⌘K hint */}
          <kbd className="hidden items-center gap-0.5 border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1.5 py-0.5 text-[0.6875rem] text-[var(--shell-fg-dim)] sm:flex" style={{ borderRadius: 2 }}>
            <span>{typeof navigator !== "undefined" && navigator.platform.includes("Mac") ? "⌘" : "Ctrl"}</span>
            <span>K</span>
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-[50vh] overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <div className="px-4 py-6 text-center text-[0.8125rem] text-[var(--shell-fg-dim)]">
              No results found.
            </div>
          ) : (
            sections.map((section) => {
              const items = grouped[section];
              return (
                <div key={section}>
                  <div className="px-3 py-1 text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--shell-fg-dim)]">
                    {section}
                  </div>
                  {items.map((item) => {
                    const idx = filtered.indexOf(item);
                    const isSelected = idx === selectedIndex;
                    return (
                      <button
                        key={item.id}
                        ref={(el) => { itemRefs.current[idx] = el; }}
                        onClick={() => handleSelect(item)}
                        onMouseEnter={() => setSelectedIndex(idx)}
                        className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-[0.8125rem] outline-none transition-colors"
                        style={{
                          borderRadius: 2,
                          backgroundColor: isSelected ? "#0a0a0a" : "transparent",
                          color: isSelected ? "#f5f5f0" : "var(--shell-fg)",
                        }}
                      >
                        <span
                          className="flex items-center justify-center"
                          style={{ color: isSelected ? "#f5f5f0" : "var(--shell-fg-dim)" }}
                        >
                          {item.icon}
                        </span>
                        <span className="flex-1">{item.label}</span>
                        {teleportTarget === item.path && (
                          <span className="font-mono text-[0.6875rem]" style={{ color: isSelected ? "#a8a29e" : "var(--shell-fg-dim)" }}>
                            <BinaryResolve
                              value={item.path}
                              resolveKey={`teleport-${item.id}`}
                              flickerMs={150}
                              tickMs={40}
                              paused={false}
                            />
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>

        {/* Footer hints */}
        <div className="flex items-center justify-between border-t border-[var(--shell-border-subtle)] px-3 py-2 text-[0.6875rem] text-[var(--shell-fg-dim)]">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1" style={{ borderRadius: 2 }}>↑</kbd>
              <kbd className="border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1" style={{ borderRadius: 2 }}>↓</kbd>
              <span>navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1" style={{ borderRadius: 2 }}>↵</kbd>
              <span>teleport</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1" style={{ borderRadius: 2 }}>Esc</kbd>
              <span>close</span>
            </span>
          </div>
          <span>{filtered.length} result{filtered.length !== 1 ? "s" : ""}</span>
        </div>
      </div>
    </div>
  );
}

export default CommandPalette;
