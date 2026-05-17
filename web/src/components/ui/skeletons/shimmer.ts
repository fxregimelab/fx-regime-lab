/** Skeleton shimmer styles — uses CSS custom properties for theming.
 *  `--skeleton-base`: muted background (surface)
 *  `--skeleton-highlight`: slightly lighter for shimmer effect
 */
export const SHIMMER =
  "animate-pulse bg-[var(--skeleton-base,_rgba(128,128,128,0.12))]" as const;

/** Terminal-themed skeleton (dark surface) */
export const SHIMMER_DARK =
  "animate-pulse bg-[var(--terminal-border-subtle)]" as const;

/** Shell-themed skeleton (light surface) */
export const SHIMMER_LIGHT =
  "animate-pulse bg-[var(--shell-border-subtle)]" as const;

/** Block skeleton with rounded corners (max 2px per design system) */
export function shimmerBlock(
  width: string,
  height: string,
  theme: "dark" | "light" = "dark",
) {
  const base = theme === "dark" ? SHIMMER_DARK : SHIMMER_LIGHT;
  return `${base} ${width} ${height}`;
}
