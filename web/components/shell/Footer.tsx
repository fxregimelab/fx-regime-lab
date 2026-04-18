// Shell footer
import Link from 'next/link';
import { ROUTES } from '@/lib/constants/routes';

export function Footer() {
  return (
    <footer className="mt-auto border-t border-neutral-200 bg-shell-bg py-8 text-sm text-neutral-600">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 sm:flex-row sm:items-center sm:justify-between">
        <span>FX Regime Lab · fxregimelab.com</span>
        <Link href={ROUTES.about} className="hover:text-neutral-900">
          About
        </Link>
      </div>
    </footer>
  );
}
