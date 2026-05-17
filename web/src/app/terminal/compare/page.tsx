"use client";

import { CompareView } from "@/components/ui/compare-view";
import { useSearchParams } from "next/navigation";

/**
 * Compare mode — side-by-side pair desks.
 * URL: /terminal/compare?pairs=eurusd,usdjpy
 */
export default function ComparePage() {
  const searchParams = useSearchParams();
  const pairsParam = searchParams.get("pairs") ?? "";

  return (
    <div className="pt-4">
      <CompareView pairsParam={pairsParam} />
    </div>
  );
}
