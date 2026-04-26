import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-[1280px] flex-col justify-center px-6 py-20">
      <p className="font-mono text-[72px] font-bold leading-none tracking-tighter text-[#0a0a0a]">
        404
      </p>
      <p className="mt-4 font-mono text-[10px] tracking-[0.2em] text-[#a0a0a0]">PAGE NOT FOUND</p>
      <p className="mt-4 max-w-md font-sans text-[15px] text-[#525252]">
        The page you requested is not in this deployment.
      </p>
      <div className="mt-8 flex flex-wrap gap-4">
        <Link
          href="/"
          className="font-mono text-[11px] text-[#0a0a0a] underline decoration-[#e5e5e5]"
        >
          Home
        </Link>
        <Link
          href="/brief"
          className="font-mono text-[11px] text-[#0a0a0a] underline decoration-[#e5e5e5]"
        >
          Today&apos;s brief
        </Link>
      </div>
    </div>
  );
}
