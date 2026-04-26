import { LogoMark } from '@/components/LogoMark';
import Link from 'next/link';

export function Footer() {
  return (
    <footer className="border-t border-[#e5e5e5] bg-white">
      <div className="px-6 py-6">
        <div className="mx-auto max-w-[1280px]">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <LogoMark className="h-5 w-5 shrink-0 text-[#0a0a0a]" />
              <span className="font-mono text-[10px] tracking-widest text-[#0a0a0a]">
                FX REGIME LAB
              </span>
            </div>
            <Link
              href="/terminal"
              className="font-mono text-[10px] text-[#0a0a0a] underline decoration-[#d0d0d0] underline-offset-4"
            >
              Terminal →
            </Link>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-4 border-t border-[#f0f0f0] pt-4">
            <p className="font-mono text-[10px] text-[#bbb]">
              © {new Date().getFullYear()} FX Regime Lab
            </p>
            <p className="font-mono text-[10px] text-[#bbb]">
              Research only. Not investment advice.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
