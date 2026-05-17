import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "FX Regime Mosaic | FX Regime Lab",
  description:
    "Multi-pair regime mosaic. At-a-glance directional bias, confidence, and volatility regime for G10 and EM FX.",
};

export default function FxRegimeLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
