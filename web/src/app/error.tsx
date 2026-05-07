"use client";

import { useEffect } from "react";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App-level Error caught:", error);
  }, [error]);

  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-[#000000] p-6 font-mono shadow-none">
      <div className="border border-[#222] bg-[#030303] p-8 text-center shadow-none">
        <p className="mb-4 text-[10px] tracking-widest text-[#f59e0b] shadow-none">
          [ RENDER EXCEPTION ]
        </p>
        <h2 className="mb-4 text-xl font-light text-white shadow-none">
          Component Failure Detected
        </h2>
        <p className="mb-8 text-[11px] text-[#666] shadow-none">
          {error.message || "The terminal module failed to render correctly."}
        </p>
        <button
          type="button"
          onClick={() => reset()}
          className="border border-[#333] bg-transparent px-4 py-2 text-[10px] tracking-widest text-[#d4d4d4] transition-colors hover:bg-[#111] shadow-none"
        >
          [ RETRY MODULE ]
        </button>
      </div>
    </div>
  );
}
