"use client";

import {
  BookOpen,
  Calendar,
  FileText,
  Info,
  Mail,
  Newspaper,
  Search,
  Sparkles,
  Terminal,
  TrendingUp,
} from "lucide-react";
import { useRouter } from "next/navigation";
import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

interface CommandItem {
  id: string;
  label: string;
  path: string;
  icon: React.ReactNode;
  section: string;
}

const ALL_ITEMS: CommandItem[] = [
  // Pages
  {
    id: "home",
    label: "Home",
    path: "/",
    icon: <FileText size={14} />,
    section: "Pages",
  },
  {
    id: "methodology",
    label: "Methodology",
    path: "/methodology",
    icon: <BookOpen size={14} />,
    section: "Pages",
  },
  {
    id: "brief",
    label: "Brief",
    path: "/brief",
    icon: <Newspaper size={14} />,
    section: "Pages",
  },
  {
    id: "track-record",
    label: "Track Record",
    path: "/performance",
    icon: <TrendingUp size={14} />,
    section: "Pages",
  },
  {
    id: "about",
    label: "About",
    path: "/about",
    icon: <Info size={14} />,
    section: "Pages",
  },
  // Terminal
  {
    id: "terminal-overview",
    label: "Terminal Overview",
    path: "/terminal",
    icon: <Terminal size={14} />,
    section: "Terminal",
  },
  // {
  //   id: "terminal-fx-regime",
  //   label: "FX Regime Mosaic",
  //   path: "/terminal/fx-regime",
  //   icon: <Sparkles size={14} />,
  //   section: "Terminal",
  // }, // HIDDEN: desk_open_cards pipeline not ready
  {
    id: "terminal-calendar",
    label: "Calendar",
    path: "/terminal/calendar",
    icon: <Calendar size={14} />,
    section: "Terminal",
  },
  {
    id: "terminal-track-record",
    label: "Track Record",
    path: "/terminal/performance",
    icon: <TrendingUp size={14} />,
    section: "Terminal",
  },
  {
    id: "terminal-memos",
    label: "Memos",
    path: "/terminal/memos",
    icon: <Mail size={14} />,
    section: "Terminal",
  },
  // Pair desks
  {
    id: "desk-eurusd",
    label: "EUR / USD Desk",
    path: "/terminal/fx-regime/eurusd",
    icon: <Terminal size={14} />,
    section: "Pair Desks",
  },
  {
    id: "desk-usdjpy",
    label: "USD / JPY Desk",
    path: "/terminal/fx-regime/usdjpy",
    icon: <Terminal size={14} />,
    section: "Pair Desks",
  },
  {
    id: "desk-usdinr",
    label: "USD / INR Desk",
    path: "/terminal/fx-regime/usdinr",
    icon: <Terminal size={14} />,
    section: "Pair Desks",
  },
];

/* ── Natural language routing ─────────────────────────────────────────── */

function parseNaturalLanguage(
  q: string,
): { path: string; label: string } | null {
  const lower = q.toLowerCase();

  // Pair detection
  let pair: string | null = null;
  if (/eur\s*\/usd|eurusd/.test(lower)) pair = "eurusd";
  else if (/usd\s*\/jpy|usdjpy/.test(lower)) pair = "usdjpy";
  else if (/usd\s*\/inr|usdinr/.test(lower)) pair = "usdinr";

  // Performance / accuracy queries
  if (/accuracy|performance|track record|win rate|brier/.test(lower)) {
    const params = new URLSearchParams();
    if (pair) params.set("pair", pair);
    const windowMatch = lower.match(/(?:last\s+)?(\d+)\s*(?:day|d)/);
    if (windowMatch) params.set("window", `${windowMatch[1]}d`);
    const query = params.toString();
    return {
      path: `/performance${query ? `?${query}` : ""}`,
      label: pair
        ? `${pair.toUpperCase()} Performance${windowMatch ? ` (${windowMatch[1]}d)` : ""}`
        : "Performance",
    };
  }

  // Regime queries → route directly to pair desk (Mosaic grid hidden)
  if (/regime|regimes/.test(lower)) {
    if (pair) {
      return {
        path: `/terminal/fx-regime/${pair}`,
        label: `${pair.toUpperCase()} Desk`,
      };
    }
    return {
      path: "/terminal",
      label: "Terminal Overview",
    };
  }

  // Direct pair desk
  if (pair && !/accuracy|performance|regime/.test(lower)) {
    return {
      path: `/terminal/fx-regime/${pair}`,
      label: `${pair.toUpperCase()} Desk`,
    };
  }

  return null;
}

/* ── Fuzzy match score ────────────────────────────────────────────────── */

function fuzzyScore(query: string, text: string): number {
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  if (t.includes(q)) return 100; // substring match

  // Character-by-character fuzzy match
  let qi = 0;
  let ti = 0;
  let score = 0;
  while (qi < q.length && ti < t.length) {
    if (q[qi] === t[ti]) {
      score++;
      qi++;
    }
    ti++;
  }
  if (qi < q.length) return 0; // not all chars matched
  return score;
}

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [teleportTarget, setTeleportTarget] = useState<string | null>(null);
  const [nlResult, setNlResult] = useState<{
    path: string;
    label: string;
  } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Listen for custom open event from VimNav
  useEffect(() => {
    const handler = (e: CustomEvent<{ filter?: string }>) => {
      setOpen(true);
      if (e.detail?.filter === "pair") {
        setQuery("desk ");
      } else {
        setQuery("");
      }
      setSelectedIndex(0);
    };
    document.addEventListener(
      "fxrl:open-command-palette",
      handler as EventListener,
    );
    return () =>
      document.removeEventListener(
        "fxrl:open-command-palette",
        handler as EventListener,
      );
  }, []);

  // Natural language parsing
  useEffect(() => {
    const q = query.trim();
    if (q.length > 2) {
      const parsed = parseNaturalLanguage(q);
      setNlResult(parsed);
    } else {
      setNlResult(null);
    }
  }, [query]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return ALL_ITEMS;
    const scored = ALL_ITEMS.map((item) => ({
      item,
      score: Math.max(
        fuzzyScore(q, item.label),
        fuzzyScore(q, item.path),
        fuzzyScore(q, item.section),
      ),
    }));
    const filtered = scored.filter((s) => s.score > 0);
    filtered.sort((a, b) => b.score - a.score);
    return filtered.map((s) => s.item);
  }, [query]);

  // Combine NL result with filtered items
  const displayItems = useMemo(() => {
    if (nlResult && query.trim().length > 2) {
      const nlItem: CommandItem = {
        id: "nl-result",
        label: nlResult.label,
        path: nlResult.path,
        icon: <Search size={14} />,
        section: "Search",
      };
      return [nlItem, ...filtered];
    }
    return filtered;
  }, [nlResult, filtered, query]);

  // Reset selection when filter changes
  // biome-ignore lint/correctness/useExhaustiveDependencies: query is the correct dependency
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Global ⌘K / Ctrl+K toggle
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
        setQuery("");
        setNlResult(null);
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
        setNlResult(null);
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
        setSelectedIndex((prev) => (prev + 1) % displayItems.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex(
          (prev) => (prev - 1 + displayItems.length) % displayItems.length,
        );
      } else if (e.key === "Enter") {
        e.preventDefault();
        const item = displayItems[selectedIndex];
        if (item) {
          handleSelect(item);
        }
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, displayItems, selectedIndex]);

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
        setNlResult(null);
        router.push(item.path);
      }, 150);
    },
    [router],
  );

  if (!open) return null;

  // Group by section
  const grouped: Record<string, CommandItem[]> = {};
  for (const item of displayItems) {
    if (!grouped[item.section]) grouped[item.section] = [];
    grouped[item.section].push(item);
  }
  const sections = Object.keys(grouped);

  return (
    <dialog
      className="fixed inset-0 z-[var(--z-command-palette)] flex items-start justify-center bg-transparent p-0 pt-[20vh] open:flex"
      aria-label="Command palette"
      open
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={() => {
          setOpen(false);
          setQuery("");
          setTeleportTarget(null);
          setNlResult(null);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            setOpen(false);
            setQuery("");
            setTeleportTarget(null);
            setNlResult(null);
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Close command palette"
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
          <kbd
            className="hidden items-center gap-0.5 border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1.5 py-0.5 text-[0.6875rem] text-[var(--shell-fg-dim)] sm:flex"
            style={{ borderRadius: 2 }}
          >
            <span>
              {typeof navigator !== "undefined" &&
              navigator.platform.includes("Mac")
                ? "⌘"
                : "Ctrl"}
            </span>
            <span>K</span>
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-[50vh] overflow-y-auto py-2">
          {displayItems.length === 0 ? (
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
                    const idx = displayItems.indexOf(item);
                    const isSelected = idx === selectedIndex;
                    const isNl = item.id === "nl-result";
                    return (
                      <button
                        type="button"
                        key={item.id}
                        ref={(el) => {
                          itemRefs.current[idx] = el;
                        }}
                        onClick={() => handleSelect(item)}
                        onMouseEnter={() => setSelectedIndex(idx)}
                        className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-[0.8125rem] outline-none transition-colors"
                        style={{
                          borderRadius: 2,
                          backgroundColor: isSelected
                            ? "var(--terminal-bg-sunken)"
                            : "transparent",
                          color: isSelected
                            ? "var(--terminal-fg)"
                            : "var(--shell-fg)",
                        }}
                      >
                        <span
                          className="flex items-center justify-center"
                          style={{
                            color: isSelected
                              ? "var(--terminal-fg)"
                              : "var(--shell-fg-dim)",
                          }}
                        >
                          {item.icon}
                        </span>
                        <span className="flex-1">
                          {item.label}
                          {isNl && (
                            <span className="ml-2 font-mono text-[9px] text-[var(--shell-fg-dim)]">
                              → {item.path}
                            </span>
                          )}
                        </span>
                        {teleportTarget === item.path && (
                          <span
                            className="font-mono text-[0.6875rem]"
                            style={{
                              color: isSelected
                                ? "var(--terminal-fg-muted)"
                                : "var(--shell-fg-dim)",
                            }}
                          >
                            {item.path}
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
              <kbd
                className="border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1"
                style={{ borderRadius: 2 }}
              >
                ↑
              </kbd>
              <kbd
                className="border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1"
                style={{ borderRadius: 2 }}
              >
                ↓
              </kbd>
              <span>navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd
                className="border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1"
                style={{ borderRadius: 2 }}
              >
                ↵
              </kbd>
              <span>teleport</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd
                className="border border-[var(--shell-border-subtle)] bg-[var(--shell-bg-sunken)] px-1"
                style={{ borderRadius: 2 }}
              >
                Esc
              </kbd>
              <span>close</span>
            </span>
          </div>
          <span>
            {displayItems.length} result{displayItems.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>
    </dialog>
  );
}

export default CommandPalette;
