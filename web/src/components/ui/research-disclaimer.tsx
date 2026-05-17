export function ResearchDisclaimer() {
  return (
    <div className="border border-[var(--color-border-subtle)] bg-[var(--color-void)] px-4 py-3 mb-6">
      <p className="font-mono text-[9px] tracking-[0.1em] text-[var(--color-text-muted)] leading-relaxed">
        <span className="text-[var(--color-warn)]">[RESEARCH ONLY]</span> For
        research purposes only. These regime classifications are derived from a
        deterministic 3-layer signal framework and validated out-of-sample. Not
        investment advice. Past calibration metrics do not guarantee future
        performance.
      </p>
    </div>
  );
}
