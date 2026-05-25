"use client";

import { useRouter, useSearchParams } from "next/navigation";

export function VersionSelector({
  versions,
  selectedVersion,
}: {
  versions: string[];
  selectedVersion: string;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  return (
    <select
      className="bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] text-[12px] px-3 py-1.5 rounded-md cursor-pointer"
      value={selectedVersion}
      onChange={(e) => {
        const params = new URLSearchParams(searchParams.toString());
        params.set("version", e.target.value);
        router.push(`/track-record?${params.toString()}`);
      }}
    >
      {versions.map((v) => (
        <option key={v} value={v}>
          {v}
        </option>
      ))}
    </select>
  );
}
