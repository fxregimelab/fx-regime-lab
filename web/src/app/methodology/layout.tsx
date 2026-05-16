import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Methodology | FX Regime Lab",
  description:
    "Three-layer regime classification engine: macro gate, directional signal, and execution timing. Documented weights, thresholds, and validation framework.",
};

export default function MethodologyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
