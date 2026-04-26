export function EmptyState({
  title = 'No data',
  subtitle = 'Nothing to show here yet.',
  tone = 'shell',
}: {
  title?: string;
  subtitle?: string;
  tone?: 'shell' | 'terminal';
}) {
  const isT = tone === 'terminal';
  const stroke = isT ? '#2a2a2a' : '#d0d0d0';
  return (
    <div
      className={`flex flex-col items-center gap-3.5 border px-6 py-12 ${
        isT ? 'border-[#1a1a1a] bg-[#0c0c0c]' : 'border-[#e5e5e5] bg-[#fafafa]'
      }`}
    >
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden>
        <title>Empty</title>
        <rect x="4" y="4" width="24" height="24" stroke={stroke} strokeWidth="1.5" />
        <line x1="10" y1="16" x2="22" y2="16" stroke={stroke} strokeWidth="1.5" />
      </svg>
      <p
        className={`m-0 text-center font-sans text-[15px] font-semibold ${isT ? 'text-[#444]' : 'text-[#0a0a0a]'}`}
      >
        {title}
      </p>
      <p
        className={`m-0 max-w-[280px] text-center font-sans text-[13px] ${isT ? 'text-[#333]' : 'text-[#737373]'}`}
      >
        {subtitle}
      </p>
    </div>
  );
}
