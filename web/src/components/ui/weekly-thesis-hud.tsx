'use client';

type WeeklyThesisHudProps = {
  bullets: string[];
};

function ThesisBulletLine({ text }: { text: string }) {
  const parts = text.split(/(\b(?:bull|bear)\b)/gi);
  return (
    <li className="font-serif text-[11px] italic leading-relaxed text-[#888]">
      {parts.map((p, i) =>
        /^(bull|bear)$/i.test(p) ? (
          <span key={i} className="text-emerald-500/90 not-italic font-medium">
            {p}
          </span>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </li>
  );
}

/** Obsidian-glass sidebar block: founder weekly thesis (pair desk only). */
export function WeeklyThesisHud({ bullets }: WeeklyThesisHudProps) {
  if (bullets.length === 0) return null;

  return (
    <section
      className="shrink-0 border border-solid border-[#222] bg-[#000000] p-3 rounded-none"
      aria-label="Weekly structural thesis"
    >
      <h2 className="mb-2 font-mono text-[9px] font-normal tracking-widest text-[#888]">
        [ WEEKLY THESIS ]
      </h2>
      <ol className="m-0 list-decimal space-y-2 pl-4 marker:text-[#666]">
        {bullets.map((b, i) => (
          <ThesisBulletLine key={i} text={b} />
        ))}
      </ol>
    </section>
  );
}
