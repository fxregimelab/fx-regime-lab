import Image from 'next/image';

export function LogoMark({ size = 24 }: { size?: number }) {
  return (
    <Image
      src="/logos/logo-without-bg.png"
      alt="FX Regime Lab"
      width={size}
      height={size}
      priority
      className="block shrink-0"
    />
  );
}
