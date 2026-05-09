import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { ComingSoon } from "@/components/ui/coming-soon";

export const metadata = {
  title: "Track Record & Calibration | FX Regime Lab",
};

export default function PerformancePage() {
  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 pt-28 pb-20"
      >
        <ComingSoon
          phase="PHASE 2"
          title="Track Record & Calibration"
          description="Out-of-sample validation metrics are being compiled. This section will present Brier scores, directional calibration, and regime-conditioned accuracy statistics derived from the immutable ledger."
        />
      </main>
      <Footer />
    </div>
  );
}
