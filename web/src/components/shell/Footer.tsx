import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-[var(--color-stone-200)] bg-[var(--color-cream)]">
      <div className="max-w-[1152px] mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr] gap-12">
          <div>
            <p className="font-mono text-[11px] tracking-[0.2em] text-[var(--color-stone-700)] uppercase font-medium mb-3">
              FX Regime Lab
            </p>
            <p className="font-sans text-[13px] text-[var(--color-stone-500)] leading-relaxed max-w-[320px]">
              Daily G10 FX regime research. Every call logged. Every outcome
              public. No narrative added after the fact.
            </p>
          </div>

          <div>
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-stone-400)] uppercase mb-4">
              Research
            </p>
            <div className="flex flex-col gap-2.5">
              {[
                ["/brief", "Daily Brief"],
                ["/methodology", "Methodology"],
                ["/terminal", "Terminal"],
              ].map(([href, label]) => (
                <Link
                  key={href}
                  href={href}
                  className="font-sans text-[13px] text-[var(--color-stone-500)] hover:text-[var(--color-stone-800)] transition-colors duration-300"
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>

          <div>
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-stone-400)] uppercase mb-4">
              Info
            </p>
            <div className="flex flex-col gap-2.5">
              {[
                ["/about", "About"],
                ["/performance", "Performance"],
              ].map(([href, label]) => (
                <Link
                  key={href}
                  href={href}
                  className="font-sans text-[13px] text-[var(--color-stone-500)] hover:text-[var(--color-stone-800)] transition-colors duration-300"
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-16 pt-6 border-t border-[var(--color-stone-200)] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <p className="font-mono text-[10px] text-[var(--color-stone-400)] tracking-wider">
            Research and learning only. Not investment advice.
          </p>
          <p className="font-mono text-[10px] text-[var(--color-stone-400)] tracking-wider">
            Shreyash Sakhare — Discretionary Macro Research
          </p>
        </div>
      </div>
    </footer>
  );
}
