interface SectionHeaderProps {
  label?: string;
  title: string;
  description?: string;
  align?: "left" | "center";
}

export function SectionHeader({
  label,
  title,
  description,
  align = "left",
}: SectionHeaderProps) {
  const alignClass = align === "center" ? "text-center mx-auto" : "";

  return (
    <div className={`mb-14 ${alignClass}`}>
      {label && (
        <span className="block font-sans text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">
          {label}
        </span>
      )}
      <h2 className="font-sans font-semibold text-[28px] text-[var(--color-text)] tracking-tight leading-snug">
        {title}
      </h2>
      {description && (
        <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[480px] mt-4">
          {description}
        </p>
      )}
    </div>
  );
}
