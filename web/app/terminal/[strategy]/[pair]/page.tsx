// Pair desk — full signal depth
import { PairDesk } from '@/components/terminal/PairDesk';

type Props = { params: Promise<{ strategy: string; pair: string }> };

export default async function TerminalPairPage({ params }: Props) {
  const { strategy, pair } = await params;
  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <PairDesk strategy={strategy} pairSlug={pair} />
    </main>
  );
}
