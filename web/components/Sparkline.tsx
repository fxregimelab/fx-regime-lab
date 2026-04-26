export function Sparkline({
  values,
  color,
  width = 120,
  height = 48,
}: {
  values: number[];
  color: string;
  width?: number;
  height?: number;
}) {
  if (!values || values.length < 2) {
    return (
      <svg className="block" width={width} height={height} role="img">
        <title>Sparkline</title>
      </svg>
    );
  }
  const mn = Math.min(...values);
  const mx = Math.max(...values);
  const range = mx - mn || 0.01;
  const n = values.length;
  const pts = values.map((v, i) => {
    const x = (i / (n - 1)) * width;
    const y = height - 2 - ((v - mn) / range) * (height - 4);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`).join(' ');
  return (
    <svg
      className="block max-w-full"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
    >
      <title>Sparkline</title>
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
