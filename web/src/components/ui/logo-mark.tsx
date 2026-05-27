"use client";

import Image from "next/image";
import type React from "react";

interface LogoMarkProps {
  size?: number;
  color?: string;
}

export const LogoMark: React.FC<LogoMarkProps> = ({ size = 28 }) => {
  return (
    <Image
      src="/logos/logo-without-bg.webp"
      alt="FX Regime Lab"
      width={size}
      height={size}
      className="object-contain"
      priority
    />
  );
};

export default LogoMark;
