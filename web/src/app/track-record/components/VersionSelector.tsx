"use client";

export function VersionSelector({
  versions,
  selectedVersion,
}: {
  versions: string[];
  selectedVersion: string;
}) {
  return (
    <select
      className="bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] text-[12px] px-3 py-1.5 rounded-md cursor-pointer"
      value={selectedVersion}
      onChange={(e) => {
        const url = new URL(window.location.href);
        url.searchParams.set("version", e.target.value);
        window.location.href = url.toString();
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
