"use client";

import { useState } from "react";

const TABS = [
  { id: "live", label: "Live Production" },
  { id: "backtested", label: "Historical Backfill" },
  { id: "validation", label: "Regime Validation Research" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function TrackRecordTabs({
  liveContent,
  backtestedContent,
  validationContent,
}: {
  liveContent: React.ReactNode;
  backtestedContent: React.ReactNode;
  validationContent: React.ReactNode;
}) {
  const [active, setActive] = useState<TabId>("live");

  return (
    <div>
      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-[var(--color-border)] mb-8">
        {TABS.map((tab) => {
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActive(tab.id)}
              className={`relative px-4 py-2.5 font-mono text-[11px] tracking-[0.1em] uppercase cursor-pointer transition-all duration-200 ${
                isActive
                  ? "text-[var(--color-text)]"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
              style={
                isActive
                  ? {
                      boxShadow:
                        "0 2px 0 0 var(--color-text), 0 4px 12px rgba(231,229,228,0.12)",
                    }
                  : undefined
              }
            >
              <span
                className={`absolute bottom-0 left-0 right-0 h-[2px] transition-all duration-200 ${
                  isActive
                    ? "bg-[var(--color-text)] opacity-100"
                    : "bg-[var(--color-text)] opacity-0 hover:opacity-30"
                }`}
                style={
                  isActive
                    ? {
                        boxShadow:
                          "0 0 8px rgba(231,229,228,0.35), 0 0 16px rgba(231,229,228,0.15)",
                      }
                    : undefined
                }
              />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {active === "live" && liveContent}
      {active === "backtested" && backtestedContent}
      {active === "validation" && validationContent}
    </div>
  );
}
