import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import MethodologyContent from "./MethodologyContent";

export const metadata = {
  title: "Methodology | FX Regime Lab",
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
