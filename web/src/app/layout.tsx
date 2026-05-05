import type { Metadata } from 'next';
import { Cormorant, Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { CommandPalette } from '@/components/layout/command-palette';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
});

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-jetbrains-mono',
  subsets: ['latin'],
});

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
      className={`${inter.variable} ${jetbrainsMono.variable} ${manifestoSerif.variable} antialiased`}
    >
      <body className="relative min-h-screen w-full bg-[var(--color-cream)] text-[var(--color-stone-900)] font-sans">
        <Providers>
          {children}
          <CommandPalette />
        </Providers>
      </body>
    </html>
  );
}
