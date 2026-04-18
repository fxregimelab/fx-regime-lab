// Strategy terminal overview
import Link from 'next/link';
import { PAIRS } from '@/lib/constants/pairs';

type Props = { params: Promise<{ strategy: string }> };

export default async function TerminalStrategyPage({ params }: Props) {
  const { strategy } = await params;
  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="font-mono text-lg font-semibold text-neutral-100">{strategy}</h1>
      <p className="mt-2 text-sm text-neutral-500">Pair desks</p>
      <ul className="mt-6 grid gap-2 sm:grid-cols-3">
        {PAIRS.map((p) => (
          <li key={p.label}>
            <Link
              href={`/terminal/${strategy}/${p.urlSlug}`}
              className="block rounded-md border border-neutral-800 bg-terminal-surface px-3 py-2 font-mono text-sm text-neutral-100 hover:border-accent"
            >
              {p.display}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
