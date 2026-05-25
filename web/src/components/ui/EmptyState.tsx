interface EmptyStateProps {
  title: string;
  explanation?: string;
  eta?: string;
}

export function EmptyState({ title, explanation, eta }: EmptyStateProps) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-10 text-center max-w-lg mx-auto">
      <p className="font-sans text-[12px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-3">
        {title}
      </p>
      {explanation && (
        <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-relaxed mb-3">
          {explanation}
        </p>
      )}
      {eta && (
        <p className="font-sans text-[11px] text-[var(--color-text-dim)]">
          {eta}
        </p>
      )}
    </div>
  );
}
