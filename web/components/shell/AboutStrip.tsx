import Image from 'next/image';
import Link from 'next/link';
import { ROUTES } from '@/lib/constants/routes';

export function AboutStrip() {
  return (
    <section className="border-t border-neutral-200 bg-shell-bg py-16">
      <div className="mx-auto grid max-w-6xl grid-cols-1 items-start gap-12 px-4 md:grid-cols-2 md:gap-16">
        <div className="relative mx-auto w-full max-w-[280px] md:mx-0">
          <Image
            src="/images/shreyash_sakhare.png"
            alt="Shreyash Sakhare"
            width={280}
            height={320}
            className="h-auto w-full rounded-xl object-cover"
            priority
          />
        </div>
        <div>
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-neutral-500">
            THE RESEARCHER
          </p>
          <h2 className="mt-2 text-4xl font-semibold text-neutral-900">Shreyash Sakhare</h2>
          <p className="mt-5 max-w-[460px] text-base leading-[1.65] text-neutral-600">
            B.Tech Electrical Engineering, Pune. Building toward discretionary macro: understanding why
            positions form and break, not just where price is. This is
            where I practice. The pipeline runs daily. The calls are public. The methodology is
            documented. NTU MFE Singapore target, 2028.
          </p>
          <Link
            href={ROUTES.about}
            className="mt-6 inline-block text-sm font-medium text-accent underline decoration-accent underline-offset-4"
          >
            Full background →
          </Link>
        </div>
      </div>
    </section>
  );
}
