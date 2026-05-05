import Link from "next/link";
import { LogoMark } from "@/components/ui/logo-mark";
import { PAIRS } from "@/lib/constants";

export function Footer() {
  return (
    <footer className="border-t border-shell-border bg-white mt-20">
      <div className="max-w-[1152px] mx-auto px-6 py-12 flex flex-wrap justify-between gap-10">
        <div>
          <div className="flex items-center gap-2.5 mb-2.5">
            <LogoMark size={20} />
            <span className="font-sans font-bold text-sm text-shell-text">
              FX Regime Lab
            </span>
          </div>
          <p className="font-mono text-[11px] text-shell-muted max-w-[260px] leading-relaxed">
            Daily G10 FX regime research.
            <br />
            Every call logged. Every outcome public.
          </p>
          <div className="flex gap-2 mt-3.5">
            {PAIRS.map((p) => (
              <span
                key={p.label}
                className="inline-block w-[18px] h-1"
                style={{ background: p.pairColor }}
              />
            ))}
          </div>
        </div>
        <div className="flex gap-12">
          <div className="flex flex-col gap-2.5">
            {[
              ["/", "Home"],
              ["/brief", "Brief"],
              ["/performance", "Performance"],
            ].map(([href, label]) => (
              <Link
                key={href}
                href={href}
                className="font-sans text-[13px] text-shell-secondary text-left hover:text-shell-text transition-colors"
              >
                {label}
              </Link>
            ))}
          </div>
          <div className="flex flex-col gap-2.5">
            {[
              ["/methodology", "Methodology"],
              ["/about", "About"],
              ["/terminal", "Terminal"],
            ].map(([href, label]) => (
              <Link
                key={href}
                href={href}
                className="font-sans text-[13px] text-shell-secondary text-left hover:text-shell-text transition-colors"
              >
                {label}
              </Link>
            ))}
          </div>
        </div>
      </div>
      <div className="border-t border-[#f0f0f0] py-3.5 px-6">
        <p className="max-w-[1152px] mx-auto font-mono text-[11px] text-shell-muted">
          Research and learning only. Not investment advice. Shreyash Sakhare —
          Discretionary Macro Research.
        </p>
      </div>
    </footer>
  );
}
