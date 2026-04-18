const PILLARS = [
  {
    n: '01',
    title: 'Rate Differential',
    body:
      '2Y and 10Y yield spreads between central banks. Wide and widening means directional pressure. Compressing signals regime exhaustion.',
  },
  {
    n: '02',
    title: 'COT Positioning',
    body:
      'CFTC Commitment of Traders, Leveraged Money and Asset Manager. 52-week percentile rank. Above 85th or below 15th flags crowding risk that can override the directional signal.',
  },
  {
    n: '03',
    title: 'Implied Volatility',
    body:
      '30-day implied vol via ^EVZ and CME CVOL. High vol degrades trend signals. Low vol confirms carry regime. Acts as a gate on the composite output.',
  },
  {
    n: '04',
    title: 'Cross-Asset',
    body:
      'VIX, DXY, and gold correlations. Context layer that does not drive the call but modifies conviction. Broken correlations flag regime transitions before price moves.',
  },
] as const;

export function SignalArchitectureSection() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-20">
      <h2 className="text-[32px] font-medium leading-tight text-neutral-900">How I read regime</h2>
      <p className="mt-3 max-w-2xl text-base text-neutral-600">
        Four signal layers. Combined into a daily composite and classified into a regime.
      </p>
      <div className="mt-12 grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-4 lg:gap-8">
        {PILLARS.map((col) => (
          <div key={col.n}>
            <p className="font-mono text-xs text-neutral-500">{col.n}</p>
            <h3 className="mt-2 font-sans text-[15px] font-semibold text-neutral-900">{col.title}</h3>
            <p className="mt-3 text-sm leading-[1.6] text-neutral-600">{col.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
