'use client';

import React, { useState } from 'react';

export function ClickToCopy({ value, children }: { value: string | undefined, children: React.ReactNode }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!value) return;
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1000);
  };

  return (
    <div 
      className="relative cursor-pointer group flex flex-col items-end"
      onClick={handleCopy}
    >
      <div className={`transition-opacity duration-200 ${copied ? 'opacity-0' : 'opacity-100 group-hover:opacity-80'}`}>
        {children}
      </div>
      {copied && (
        <div className="absolute inset-0 flex flex-col items-end justify-center bg-[#080808]">
          <span className="font-mono text-[10px] font-bold text-[#4ade80] tracking-widest px-2 py-1 border border-[#4ade80]">COPIED</span>
        </div>
      )}
    </div>
  );
}
