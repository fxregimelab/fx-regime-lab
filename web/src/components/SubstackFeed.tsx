const FEED_URL = 'https://fxregimelab.substack.com/feed';

function parseRssTitles(xml: string, limit: number): string[] {
  const titles: string[] = [];
  const chunks = xml.split('<item>');
  for (let i = 1; i < chunks.length && titles.length < limit; i += 1) {
    const chunk = chunks[i] ?? '';
    const cdata = chunk.match(/<title>\s*<!\[CDATA\[([\s\S]*?)\]\]>\s*<\/title>/i);
    const plain = chunk.match(/<title>([^<]*)<\/title>/i);
    const raw = (cdata?.[1] ?? plain?.[1] ?? '').trim();
    if (raw) titles.push(raw.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>'));
  }
  return titles;
}

async function fetchHeadlines(): Promise<string[]> {
  try {
    const init: RequestInit & { next?: { revalidate: number } } = {
      headers: { Accept: 'application/rss+xml, application/xml, text/xml' },
      next: { revalidate: 3600 },
    };
    const res = await fetch(FEED_URL, init);
    if (!res.ok) return [];
    const xml = await res.text();
    return parseRssTitles(xml, 3);
  } catch {
    return [];
  }
}

/** SSG-cached Substack headlines (1h) for the gateway. */
export async function SubstackFeed() {
  const headlines = await fetchHeadlines();
  return (
    <div className="border border-[#111] bg-[#000000] p-4">
      <p className="font-mono text-[10px] text-[#666] tracking-widest mb-3 m-0">[ WEEKLY MACRO MEMOS ]</p>
      {headlines.length === 0 ? (
        <p className="font-mono text-[11px] text-[#555] m-0">—</p>
      ) : (
        <ul className="list-none m-0 p-0 flex flex-col gap-3">
          {headlines.map((h) => (
            <li key={h} className="m-0">
              <a
                href="https://fxregimelab.substack.com/"
                className="font-mono text-[11px] text-[#c8c8c8] leading-snug no-underline hover:text-white transition-colors block border-b border-[#1a1a1a] pb-2 last:border-b-0 last:pb-0"
                target="_blank"
                rel="noreferrer"
              >
                {h}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
