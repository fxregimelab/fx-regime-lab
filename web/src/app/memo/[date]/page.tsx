import { ComingSoon } from "@/components/ui/coming-soon";
import type { Metadata } from "next";

interface MemoArchivePageProps {
  params: Promise<{ date: string }>;
}

export async function generateMetadata({
  params,
}: MemoArchivePageProps): Promise<Metadata> {
  const { date } = await params;
  return {
    title: `Memo Archive — ${date} | FX Regime Lab`,
    description:
      "Daily regime memo archive. T+24h SEO-optimized summaries of systemic state.",
    robots: { index: true, follow: true },
  };
}

export default async function MemoArchivePage({
  params,
}: MemoArchivePageProps) {
  const { date } = await params;

  return (
    <ComingSoon
      phase="PHASE 3"
      title="Memo Archive"
      description={`The T+24h memo archive for ${date} is being prepared. This section will contain SEO-optimized regime summaries with structured data for each trading day.`}
    />
  );
}
