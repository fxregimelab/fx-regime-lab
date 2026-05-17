interface BrierChartProps {
  data: { date: string; value: number }[];
}

export function BrierChart({ data }: BrierChartProps) {
  if (data.length < 2) {
    return (
      <div className="w-full h-[180px] md:h-[220px] bg-black flex items-center justify-center">
        <span className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider">
          INSUFFICIENT DATA (N &lt; 2)
        </span>
      </div>
    );
  }

  const W = 1000;
  const H = 280;
  const padL = 60;
  const padR = 16;
  const padT = 16;
  const padB = 32;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const values = data.map((d) => d.value);
  let minV = Math.min(...values);
  let maxV = Math.max(...values);
  if (minV === maxV) {
    minV -= 0.05;
    maxV += 0.05;
  }
  const range = maxV - minV || 1;

  const pts = data.map((d, i) => {
    const x = padL + (i / (data.length - 1)) * chartW;
    const y = padT + chartH - ((d.value - minV) / range) * chartH;
    return { x, y, date: d.date };
  });

  const lineD = pts
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  const areaD = `M ${pts[0].x.toFixed(1)} ${padT + chartH} ${pts.map((p) => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")} L ${pts[pts.length - 1].x.toFixed(1)} ${padT + chartH} Z`;

  const yTicks = [maxV, (minV + maxV) / 2, minV];
  const xStep = Math.max(1, Math.floor(data.length / 5));
  const xLabels = pts.filter(
    (_, i) => i % xStep === 0 || i === data.length - 1,
  );

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className="w-full h-[180px] md:h-[220px] block"
    >
      <title>Brier Score Time Series</title>
      <rect width={W} height={H} fill="var(--terminal-bg)" />

      {/* horizontal grid */}
      {yTicks.map((v) => {
        const y = padT + chartH - ((v - minV) / range) * chartH;
        return (
          <line
            key={`grid-${v}`}
            x1={padL}
            y1={y}
            x2={W - padR}
            y2={y}
            stroke="var(--terminal-bg-sunken)"
            strokeWidth={1}
          />
        );
      })}

      {/* area fill */}
      <path d={areaD} fill="rgba(214,211,209,0.06)" />

      {/* line */}
      <path
        d={lineD}
        fill="none"
        stroke="var(--terminal-fg-muted)"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />

      {/* y-axis labels */}
      {yTicks.map((v) => {
        const y = padT + chartH - ((v - minV) / range) * chartH;
        return (
          <text
            key={`ylabel-${v}`}
            x={padL - 8}
            y={y + 3}
            textAnchor="end"
            fill="var(--terminal-fg-dim)"
            fontSize={10}
            fontFamily="JetBrains Mono, monospace"
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {v.toFixed(2)}
          </text>
        );
      })}

      {/* x-axis labels */}
      {xLabels.map((p) => (
        <text
          key={`xlabel-${p.date}`}
          x={p.x}
          y={H - 10}
          textAnchor="middle"
          fill="var(--terminal-fg-dim)"
          fontSize={10}
          fontFamily="JetBrains Mono, monospace"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {p.date}
        </text>
      ))}
    </svg>
  );
}
