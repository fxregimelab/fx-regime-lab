// 404 — shell placeholder
import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[50vh] max-w-lg flex-col justify-center gap-4 px-6 py-16">
      <h1 className="font-display text-3xl text-neutral-900">Page not found</h1>
      <p className="text-neutral-600">The page you requested does not exist.</p>
      <Link href="/" className="text-accent underline-offset-4 hover:underline">
        Back to home
      </Link>
    </main>
  );
}
