import { LogoMark } from '@/components/LogoMark';
import Link from 'next/link';

const link = 'font-mono text-[11px] text-[#525252] hover:text-[#0a0a0a]';
const colTitle = 'mb-3 font-mono text-[9px] tracking-[0.12em] text-[#a0a0a0]';

export function Footer() {
  return (
    <footer className="border-t border-[#e5e5e5] bg-white">
      <div className="px-6 py-10">
        <div className="mx-auto max-w-[1280px]">
          <div className="mb-8 flex flex-wrap items-center gap-2.5">
            <LogoMark className="h-5 w-5 shrink-0 text-[#0a0a0a]" />
            <span className="font-mono text-[10px] tracking-widest text-[#0a0a0a]">FX REGIME LAB</span>
          </div>
          <div className="grid grid-cols-2 gap-8 border-t border-[#f0f0f0] pt-8 md:grid-cols-4">
            <div>
              <p className={colTitle}>SITE</p>
              <ul className="flex flex-col gap-2">
                <Link className={link} href="/">
                  Home
                </Link>
                <Link className={link} href="/brief">
                  Brief
                </Link>
                <Link className={link} href="/about">
                  About
                </Link>
              </ul>
            </div>
            <div>
              <p className={colTitle}>RESEARCH</p>
              <ul className="flex flex-col gap-2">
                <Link className={link} href="/signals">
                  Signals
                </Link>
                <Link className={link} href="/performance">
                  Performance
                </Link>
                <Link className={link} href="/calendar">
                  Calendar
                </Link>
                <Link className={link} href="/fx-regime">
                  FX Regime
                </Link>
              </ul>
            </div>
            <div>
              <p className={colTitle}>TOOLS</p>
              <Link className={link} href="/terminal">
                Terminal
              </Link>
            </div>
            <div>
              <p className={colTitle}>TAGLINE</p>
              <p className="font-sans text-[12px] leading-relaxed text-[#737373]">
                Dated regime calls, validated next day. Research only.
              </p>
            </div>
          </div>
          <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-[#f0f0f0] pt-6">
            <p className="font-mono text-[10px] text-[#bbb]">© {new Date().getFullYear()} FX Regime Lab</p>
            <p className="font-mono text-[10px] text-[#bbb]">Research only. Not investment advice.</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
