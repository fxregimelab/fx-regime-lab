'use client';

type GlobalErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#000000] text-[#e8e8e8] flex items-center justify-center px-6">
        <div className="w-full max-w-2xl border border-[#222] bg-[#000000] p-6">
          <p className="font-mono text-[12px] tracking-widest text-[#f59e0b]">[ DATA OFFLINE ]</p>
          <p className="font-mono text-[11px] text-[#888] mt-2 break-all">
            {error.message || 'Global terminal failure'}
          </p>
          <button
            type="button"
            onClick={() => reset()}
            className="mt-4 border border-[#333] bg-[#000000] px-3 py-2 font-mono text-[10px] text-[#d4d4d4] tracking-widest hover:text-[#ffffff]"
          >
            [ RETRY SYSTEM ]
          </button>
        </div>
      </body>
    </html>
  );
}
