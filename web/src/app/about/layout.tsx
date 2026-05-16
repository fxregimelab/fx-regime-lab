import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About | FX Regime Lab",
  description:
    "Meet the team behind FX Regime Lab. Systematic FX macro research, published daily. Built by Shreyash Sakhare.",
};

export default function AboutLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}
