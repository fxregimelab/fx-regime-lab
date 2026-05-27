"use client";

import { useEffect, useState } from "react";

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "architecture", label: "Three-Layer Architecture" },
  { id: "layer1", label: "Layer 1 — Regime Gate" },
  { id: "layer2", label: "Layer 2 — Directional Bias" },
  { id: "layer3", label: "Layer 3 — Execution & Timing" },
  { id: "per-pair", label: "Per-Pair Methodology" },
  { id: "confidence", label: "Confidence Derivation" },
  { id: "validation", label: "Validation Methodology" },
  { id: "simulation", label: "Sizing Simulation" },
  { id: "data-sources", label: "Data Sources" },
];

export function MethodologyTOC() {
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        // biome-ignore lint/complexity/noForEach: small array, readable
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        });
      },
      { rootMargin: "-20% 0px -60% 0px" },
    );

    // biome-ignore lint/complexity/noForEach: small constant array
    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <nav className="hidden lg:block sticky top-28 w-64 shrink-0 self-start">
      <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
        Contents
      </p>
      <ul className="space-y-1">
        {SECTIONS.map(({ id, label }) => (
          <li key={id}>
            <a
              href={`#${id}`}
              className={`block px-3 py-1.5 text-[13px] transition-colors rounded ${
                activeId === id
                  ? "text-[var(--color-brand-amber)] bg-[var(--color-surface)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
              }`}
            >
              {label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
