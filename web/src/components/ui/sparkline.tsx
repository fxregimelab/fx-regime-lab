import React from 'react';

export function Sparkline({ values, color = '#4BA3E3', height = 24, width = 60 }: { values: number[], color?: string, height?: number, width?: number }) {
  if (!values || values.length < 2) return <div style={{ height, width }} />;
  const mn = Math.min(...values), mx = Math.max(...values);
  const range = mx - mn || 0.01;
  const n = values.length;
  const pts = values.map((v, i) => [i / (n - 1) * width, (height - 2) - ((v - mn) / range) * (height - 4)]);
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="block overflow-visible">
      <path d={line} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
