import { EmptyState, ErrorBoundaryCard } from '@/components/states';
import { pairBgClass, pairTextClass } from '@/lib/pair-styles';
import type { PairMeta } from '@/lib/types';

const HEADER_RE = /^(OUTLOOK|KEY RISKS|SCENARIOS|WATCH LEVELS)\s*$/i;

type Block = { title: string; body: string };

function parseAnalysis(text: string): Block[] {
  const parts = text.split(/\n\n+/);
  const blocks: Block[] = [];
  for (const part of parts) {
    const lines = part.split('\n');
    const first = lines[0]?.trim() ?? '';
    if (HEADER_RE.test(first)) {
      blocks.push({
        title: first.toUpperCase(),
        body: lines.slice(1).join('\n').trim(),
      });
    } else {
      const chunk = part.trim();
      if (chunk) {
        const sub = chunk.split('\n');
        const head = sub[0]?.trim() ?? '';
        if (HEADER_RE.test(head)) {
          blocks.push({
            title: head.toUpperCase(),
            body: sub.slice(1).join('\n').trim(),
          });
        } else {
          blocks.push({ title: '', body: chunk });
        }
      }
    }
  }
  return blocks;
}

export function AiTab({
  pair,
  compact,
  analysis,
  primaryDriver,
  fetchError,
}: {
  pair: PairMeta;
  compact?: boolean;
  analysis: string | null;
  primaryDriver: string | null;
  fetchError?: string | null;
}) {
  if (fetchError) {
    return <ErrorBoundaryCard tone="terminal" message={fetchError} />;
  }

  if (!analysis) {
    return (
      <EmptyState
        tone="terminal"
        title="No AI brief"
        subtitle="Cached analysis will appear here once the pipeline writes the brief row."
      />
    );
  }

  const blocks = parseAnalysis(analysis);
  const sectionTitle = (t: string) => (
    <h3
      className={`border-t border-[#1e1e1e] pt-3 font-mono text-[9px] font-normal tracking-widest ${pairTextClass(pair.label)}`}
    >
      {t}
    </h3>
  );

  return (
    <div className={compact ? 'space-y-2' : 'space-y-4'}>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[8px] text-[#555]">AI ANALYSIS</span>
        <span className={`h-1.5 w-1.5 rounded-full ${pairBgClass(pair.label)}`} />
      </div>
      {primaryDriver ? (
        <p className="font-mono text-[10px] leading-relaxed text-[#737373]">
          <span className="text-[#555]">PRIMARY DRIVER </span>
          {primaryDriver}
        </p>
      ) : null}
      {blocks.map((b) => (
        <div key={b.title + b.body.slice(0, 20)}>
          {b.title ? sectionTitle(b.title) : null}
          <div
            className={
              compact
                ? 'mt-1 space-y-1.5 font-sans text-[12px] font-normal leading-relaxed text-[#737373]'
                : 'mt-2 space-y-2 font-sans text-[13px] font-normal leading-relaxed text-[#737373]'
            }
          >
            {b.body.split('\n').map((line) => {
              const t = line.trim();
              if (!t) return null;
              if (t.startsWith('•')) {
                return (
                  <p key={t} className="pl-1">
                    {t}
                  </p>
                );
              }
              return (
                <p key={t} className="pl-0">
                  {t}
                </p>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
