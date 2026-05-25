import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import type { Metadata } from "next";
import MethodologyContent from "./MethodologyContent";

export const metadata: Metadata = {
  title: "Methodology | FX Regime Lab",
  description:
    "Transparent regime detection framework: signal inputs, composite scoring, and honest performance measurement with published limitations.",
};

export default function MethodologyPage() {
  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <AuditTrailBannerServer variant="shell" />
      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full"
      >
        <MethodologyContent />
      </main>
      <Footer />
    </div>
  );
}
