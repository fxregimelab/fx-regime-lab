"use client";

import { useState } from "react";

const TABS = [
  { id: "live", label: "Live" },
  { id: "backtested", label: "Backtested" },
  { id: "validation", label: "Regime Validation" },
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
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActive(tab.id)}
            className={`px-4 py-2.5 font-mono text-[11px] tracking-[0.1em] uppercase transition-colors ${
              active === tab.id
                ? "text-[var(--color-text)] border-b-2 border-[var(--color-text)]"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {active === "live" && liveContent}
      {active === "backtested" && backtestedContent}
      {active === "validation" && validationContent}
    </div>
  );
}
