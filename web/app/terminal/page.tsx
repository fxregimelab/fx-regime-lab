// Terminal home — strategy selector
import Link from 'next/link';
import { STRATEGIES } from '@/lib/constants/strategies';

export default function TerminalHomePage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="font-mono text-xl font-semibold text-neutral-100">Terminal</h1>
      <p className="mt-2 text-sm text-neutral-400">Choose a strategy desk.</p>
      <ul className="mt-6 space-y-2">
        {STRATEGIES.map((s) => (
          <li key={s.id}>
            <Link
              href={`/terminal/${s.id}`}
              className="block rounded-md border border-neutral-800 bg-terminal-surface px-4 py-3 text-neutral-100 hover:border-accent"
            >
              <span className="font-mono text-sm font-medium">{s.name}</span>
              <span className="ml-2 text-xs text-neutral-500">{s.asset_class}</span>
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
