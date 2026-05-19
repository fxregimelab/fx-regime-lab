"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const SECTIONS = [
  { label: "Overview", href: "/terminal" },
  { label: "Calendar", href: "/terminal/calendar" },
  { label: "Track Record", href: "/terminal/performance" },
  { label: "Memos", href: "/terminal/memos" },
];

export function TerminalSubNav() {
  const pathname = usePathname();

  return (
    <nav
      className="border-b border-[var(--color-border)] bg-[var(--color-void)]"
      aria-label="Terminal sections"
    >
      <div className="mx-auto flex h-[36px] max-w-[1152px] items-center gap-0.5 overflow-x-auto px-6">
        {SECTIONS.map((section) => {
          const active =
            pathname === section.href ||
            (section.href !== "/terminal" &&
              pathname?.startsWith(section.href));
          return (
            <Link
              key={section.href}
              href={section.href}
              className={`px-3 py-1 font-mono text-[10px] tracking-widest uppercase transition-colors ${
                active
                  ? "text-[var(--color-text)] border-b border-[var(--color-text)]"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
              style={{ marginBottom: "-1px" }}
            >
              {section.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
