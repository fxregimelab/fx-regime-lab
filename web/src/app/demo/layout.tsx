import Link from "next/link";
import type React from "react";

export default function DemoLayout({
  children,
}: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans overflow-x-hidden selection:bg-white/20 selection:text-white">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b border-white/10 bg-[#050505]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/demo" className="flex items-center gap-3 group">
            <div className="w-6 h-6 rounded bg-white group-hover:scale-105 transition-transform" />
            <span className="font-mono font-medium tracking-tight text-sm">
              FX REGIME LAB
            </span>
          </Link>
          <div className="flex gap-6 text-xs font-mono tracking-widest text-white/50 uppercase">
            <Link
              href="/demo/terminal"
              className="hover:text-white transition-colors"
            >
              Terminal
            </Link>
            <Link
              href="/demo/performance"
              className="hover:text-white transition-colors"
            >
              Performance
            </Link>
          </div>
        </div>
      </nav>
      {/* Content */}
      <main className="max-w-7xl mx-auto p-6 min-h-[calc(100vh-64px)]">
        {children}
      </main>
    </div>
  );
}
