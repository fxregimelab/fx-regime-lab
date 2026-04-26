const TRACK: Record<'light' | 'dark', string> = {
  light: '#e5e5e5',
  dark: '#1e1e1e',
};

type BarHeightPx = 3 | 4 | 6;

const barClass: Record<BarHeightPx, string> = {
  3: 'h-[3px]',
  4: 'h-1',
  6: 'h-[6px]',
};

export function ConfidenceBar({
  value,
  pairColor,
  variant = 'light',
  className,
  barHeightPx = 6,
}: {
  value: number;
  pairColor: string;
  variant?: 'light' | 'dark';
  className?: string;
  barHeightPx?: BarHeightPx;
}) {
  const w = Math.max(0, Math.min(1, value)) * 100;
  const h = barHeightPx;
  return (
    <svg
      className={`block w-full ${barClass[h]} ${className ?? ''}`}
      viewBox={`0 0 100 ${h}`}
      preserveAspectRatio="none"
      role="img"
    >
      <title>Confidence bar</title>
      <rect width="100" height={h} fill={TRACK[variant]} />
      <rect width={w} height={h} fill={pairColor} />
    </svg>
  );
}
