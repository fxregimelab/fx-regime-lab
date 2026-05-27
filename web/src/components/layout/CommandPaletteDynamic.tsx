"use client";

import dynamic from "next/dynamic";

const CommandPalette = dynamic(
  () => import("./command-palette").then((m) => m.CommandPalette),
  { ssr: false },
);

export function CommandPaletteDynamic() {
  return <CommandPalette />;
}
