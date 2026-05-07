"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global Error caught:", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="bg-[#000000] text-white min-h-screen flex items-center justify-center font-mono">
        <div className="border border-[#333] bg-[#050505] p-8 max-w-2xl text-center">
          <p className="text-[10px] tracking-widest text-[#f59e0b] mb-4">
            [ FATAL SYSTEM EXCEPTION ]
          </p>
          <h1 className="text-2xl font-light mb-4">
            The Omega Terminal Encountered an Error
          </h1>
          <p className="text-[12px] text-[#888] mb-6">
            {error.message || "An unexpected runtime exception occurred."}
          </p>
          <button
            type="button"
            onClick={() => reset()}
            className="border border-[#333] hover:bg-[#111] px-6 py-2 text-[11px] tracking-widest transition-colors"
          >
            [ REBOOT SEQUENCE ]
          </button>
        </div>
      </body>
    </html>
  );
}
