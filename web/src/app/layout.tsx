import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { CommandPalette } from '@/components/ui/command-palette';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
});

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-jetbrains-mono',
  subsets: ['latin'],
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
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="relative z-[1] min-h-[100dvh] flex flex-col font-sans bg-[#000000] text-[#e8e8e8] antialiased">
        <Providers>
          {/* Pair-desk systemic banner + dollar/Polymarket strip: `app/terminal/layout.tsx` + TerminalNav */}
          {children}
          <CommandPalette />
        </Providers>
      </body>
    </html>
  );
}
