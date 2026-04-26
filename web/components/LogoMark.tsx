export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      className={className ?? 'h-6 w-6 shrink-0 text-[#0a0a0a]'}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
    >
      <title>FX Regime Lab mark</title>
      <path
        d="M16 2L28 10V22L16 30L4 22V10L16 2Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M16 8L22 12.5V19.5L16 24L10 19.5V12.5L16 8Z"
        fill="currentColor"
        fillOpacity="0.15"
      />
    </svg>
  );
}
