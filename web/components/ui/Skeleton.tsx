// Loading skeleton
type Props = { className?: string };

export function Skeleton({ className }: Props) {
  return <div className={`animate-pulse rounded-md bg-neutral-200 ${className ?? 'h-4 w-full'}`} />;
}
