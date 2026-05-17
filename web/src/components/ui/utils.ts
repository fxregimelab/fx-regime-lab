import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt2(v: number | null | undefined) {
  return v == null || Number.isNaN(v) ? "—" : v.toFixed(2);
}

export function fmt4(v: number | null | undefined) {
  return v == null || Number.isNaN(v) ? "—" : v.toFixed(4);
}

/** Normalize a value that may be stored as proportion (0–1) or percentage (0–100). */
export function normalizeProp(v: number | null | undefined): number | null {
  if (v == null || Number.isNaN(v)) return null;
  // If > 1, treat as already-multiplied percentage and divide back
  if (v > 1) return v / 100;
  return v;
}

export function fmtConfidence(v: number | null | undefined) {
  if (v == null || Number.isNaN(v)) return "—";
  const prop = normalizeProp(v) ?? 0;
  const clamped = Math.min(1, Math.max(0, prop));
  return `${Math.round(clamped * 100)}%`;
}

export function fmtInt(v: number | null | undefined) {
  return v == null || Number.isNaN(v) ? "—" : v.toFixed(0);
}

/** Format large numbers as K/M (e.g. 1_234_567 → "1.23M", -45_000 → "-45.0K") */
export function fmtKM(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(1)}K`;
  return `${sign}${abs.toFixed(0)}`;
}

export function fmtChg(v: number | null | undefined) {
  if (v == null || Number.isNaN(v))
    return { str: "—", color: "var(--color-text-dim)" };
  const sign = v >= 0 ? "+" : "";
  const color = v >= 0 ? "var(--color-up)" : "var(--color-down)";
  return { str: `${sign}${v.toFixed(2)}%`, color };
}

export function timeAgo(dateString: string | undefined): string {
  if (!dateString) return "Updated just now";
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return `Updated ${diffInSeconds}s ago`;

  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) return `Updated ${diffInMinutes}m ago`;

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) return `Updated ${diffInHours}h ago`;

  const diffInDays = Math.floor(diffInHours / 24);
  return `Updated ${diffInDays}d ago`;
}
