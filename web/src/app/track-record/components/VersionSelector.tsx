"use client";

interface VersionSelectorProps {
  versions: string[];
  selectedVersion: string;
  onChange?: (version: string) => void;
}

export function VersionSelector({
  versions,
  selectedVersion,
  onChange,
}: VersionSelectorProps) {
  return (
    <select
      className="bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] text-[12px] px-3 py-1.5 rounded-md cursor-pointer"
      value={selectedVersion}
      onChange={(e) => {
        onChange?.(e.target.value);
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
