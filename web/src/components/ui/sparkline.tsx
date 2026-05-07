"use client";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fillOpacity?: number;
}

export function Sparkline({
  data,
  width = 120,
  height = 40,
  color = "var(--color-stone-500)",
  fillOpacity = 0.1,
}: SparklineProps) {
  if (data.length < 2) return <div style={{ width, height }} />;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const padding = 2;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - padding - ((v - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const areaPath =
    points.length > 0
      ? `M${points[0]} L${points.join(" L")} L${width - padding},${height - padding} L${padding},${height - padding} Z`
      : "";

  const linePath =
    points.length > 0 ? `M${points[0]} L${points.join(" L")}` : "";

  const isUp = data[data.length - 1] >= data[0];
  const strokeColor =
    color === "var(--color-stone-500)" ? (isUp ? "#7a9e7a" : "#b87a7a") : color;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
    >
      <title>Sparkline</title>
      <path d={areaPath} fill={strokeColor} opacity={fillOpacity} />
      <path
        d={linePath}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
