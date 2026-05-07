"use client";

import React from "react";

export function GlobalMacroPulse() {
  return (
    <div
      className="fixed left-0 right-0 top-0 z-[calc(var(--z-sticky)+1)] flex items-center justify-center overflow-hidden bg-[#000000]"
      style={{ height: 28 }}
    >
      <span
        className="text-[0.6875rem] font-medium tracking-wider text-[#e7e5e4]"
        style={{ fontVariantNumeric: "tabular-nums", fontFeatureSettings: '"tnum"' }}
      >
        DXY · US10Y · VIX · WTI
      </span>
    </div>
  );
}

export default GlobalMacroPulse;
