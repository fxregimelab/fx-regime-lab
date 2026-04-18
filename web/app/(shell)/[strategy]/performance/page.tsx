// Strategy-specific performance
type Props = { params: Promise<{ strategy: string }> };

export default async function StrategyPerformancePage({ params }: Props) {
  const { strategy } = await params;
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="font-display text-3xl font-semibold text-neutral-900">
        Performance — {strategy}
      </h1>
      <p className="mt-4 text-neutral-600">Pair- and strategy-specific validation views.</p>
    </main>
  );
}
