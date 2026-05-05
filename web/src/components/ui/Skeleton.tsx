"use client";

import { useReducedMotion } from "@/hooks/useReducedMotion";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
}

export function Skeleton({ width, height, className = "" }: SkeletonProps) {
  const reducedMotion = useReducedMotion();

  const style: React.CSSProperties = {
    width: typeof width === "number" ? `${width}px` : width,
    height: typeof height === "number" ? `${height}px` : height,
  };

  return (
    <div
      style={style}
      className={[
        "rounded-md bg-[var(--color-surface)]",
        reducedMotion ? "" : "animate-pulse",
        className,
      ].join(" ")}
    />
  );
}
