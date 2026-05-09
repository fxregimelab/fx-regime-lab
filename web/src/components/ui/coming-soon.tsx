interface ComingSoonProps {
  phase?: string;
  title: string;
  description: string;
}

export function ComingSoon({
  phase = "PHASE 2",
  title,
  description,
}: ComingSoonProps) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-6">
      <div className="w-full max-w-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
        <p className="font-mono text-[9px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">
          [{phase}]
        </p>
        <h1 className="font-sans font-semibold text-[clamp(24px,3vw,32px)] text-[var(--color-text)] tracking-tight leading-snug mb-4">
          {title}
        </h1>
        <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-relaxed mb-6">
          {description}
        </p>
        <div className="border-t border-[var(--color-border)] pt-4">
          <p className="font-mono text-[9px] tracking-wider text-[var(--color-text-muted)]">
            Expected in a future phase of the research program.
          </p>
        </div>
      </div>
    </div>
  );
}
