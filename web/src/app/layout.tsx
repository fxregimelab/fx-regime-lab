import type { Metadata } from 'next';
import { Cormorant, Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { GlobalMacroPulse } from '@/components/layout/global-macro-pulse';
import { CommandPalette } from '@/components/layout/command-palette';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
});

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-jetbrains-mono',
  subsets: ['latin'],
});

/** Light (300) serif for manifesto — Playfair static weights omit 300 in `next/font`. */
const manifestoSerif = Cormorant({
  variable: '--font-playfair',
  subsets: ['latin'],
  weight: ['300'],
});

export const metadata: Metadata = {
  title: 'FX Regime Lab',
  description: 'Daily regime calls. On the record.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-fxrl-app="omega"
      className={`${inter.variable} ${jetbrainsMono.variable} ${manifestoSerif.variable} h-full max-h-[100dvh] overflow-hidden antialiased`}
    >
      <body className="relative z-[1] h-[100dvh] w-screen max-w-[100vw] overflow-hidden flex flex-col font-sans bg-[var(--bg-void)] text-[#e8e8e8] antialiased">
        <Providers>
          <GlobalMacroPulse />
          <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden pt-[28px] shadow-none">
            {children}
          </div>
          <CommandPalette />
        </Providers>
      </body>
    </html>
  );
}
