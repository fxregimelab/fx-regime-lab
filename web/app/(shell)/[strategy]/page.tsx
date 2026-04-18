// Strategy overview (fx-regime etc)
export const runtime = 'edge';

type Props = { params: Promise<{ strategy: string }> };

export default async function StrategyPage({ params }: Props) {
  const { strategy } = await params;
  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="font-display text-3xl font-semibold text-neutral-900">Strategy: {strategy}</h1>
      <p className="mt-4 text-neutral-600">Overview and links to terminal desks.</p>
    </main>
  );
}
