import type { Metadata } from 'next';
import { PAIRS } from '@/lib/mockData';

export async function generateMetadata({ params }: { params: Promise<{ pair: string }> }): Promise<Metadata> {
  const resolvedParams = await params;
  const pairSlug = resolvedParams.pair;
  const pair = PAIRS.find((p) => p.urlSlug === pairSlug) ?? PAIRS[0];

  return {
    title: `${pair.display} desk | FX Regime Lab`,
  };
}

export default function PairDeskLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
