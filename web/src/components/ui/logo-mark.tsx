import Image from 'next/image';

export function LogoMark({
  size = 24,
  heartbeat = false,
}: {
  size?: number;
  /** Mechanical pulse while upstream data is fetching. */
  heartbeat?: boolean;
}) {
  return (
    <span
      className={`inline-block shrink-0 ${heartbeat ? 'omega-heartbeat' : ''}`}
      style={heartbeat ? { willChange: 'opacity' } : undefined}
    >
      <Image
        src="/logos/logo-without-bg.png"
        alt="FX Regime Lab"
        width={size}
        height={size}
        priority
        className="block shrink-0"
      />
    </span>
  );
}
