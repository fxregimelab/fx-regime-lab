import type { Metadata } from "next";
import { Cormorant, Inter, JetBrains_Mono } from "next/font/google";
import dynamic from "next/dynamic";
import "./globals.css";
import { ToastProvider } from "@/components/ui/toast-context";
import { Toaster } from "@/components/ui/toaster";
import { Providers } from "./providers";

const CommandPalette = dynamic(
  () => import("@/components/layout/command-palette").then((m) => m.CommandPalette),
  { ssr: false },
);

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

const manifestoSerif = Cormorant({
  variable: "--font-playfair",
  subsets: ["latin"],
  weight: ["300"],
});

export const metadata: Metadata = {
  title: "FX Regime Lab",
  description: "Daily regime calls. On the record.",
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
      <body
        className="relative min-h-screen w-full bg-[var(--color-void)] text-[var(--color-text)] font-sans"
        data-density="standard"
      >
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-[var(--color-surface)] focus:border focus:border-[var(--color-border)] focus:text-[var(--color-text)] focus:font-sans focus:text-[13px]"
        >
          Skip to content
        </a>
        <Providers>
          <ToastProvider>
            {children}
            <CommandPalette />
            <Toaster />
          </ToastProvider>
        </Providers>
      </body>
    </html>
  );
}
