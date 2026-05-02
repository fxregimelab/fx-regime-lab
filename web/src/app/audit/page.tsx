import fs from 'fs';
import path from 'path';

const AUDIT_OFFLINE_FALLBACK =
  '[ SYSTEM INTEGRITY LOG OFFLINE: REFER TO GITHUB FOR FULL ARCHIVE ]';

export default function AuditPage() {
  const chatPath = path.join(process.cwd(), '..', 'chat.md');
  let raw = '';
  let readFailed = false;
  try {
    raw = fs.readFileSync(chatPath, 'utf8');
  } catch {
    readFailed = true;
    raw = AUDIT_OFFLINE_FALLBACK;
  }

  const sections = readFailed ? [] : raw.split(/\n(?=## )/);

  return (
    <main className="min-h-screen bg-[#000000] text-[#c0c0c0]">
      <header className="border-b border-solid border-[#222] bg-[#000000] px-4 py-4">
        <a
          href="/terminal"
          className="font-mono text-[9px] tracking-widest text-[#666] no-underline hover:text-[#aaa]"
        >
          ← TERMINAL
        </a>
        <h1 className="mt-3 font-mono text-[11px] font-normal tracking-widest text-[#888] tabular-nums">
          [ SYSTEM INTEGRITY LOG: THE ADVERSARIAL CRUCIBLE ]
        </h1>
        <p className="mt-2 max-w-2xl font-mono text-[10px] leading-relaxed text-[#555] tabular-nums">
          Read-only development journey. Source: repository <code className="text-[#777]">chat.md</code>.
        </p>
      </header>
      <div className="mx-auto max-w-3xl space-y-3 px-4 py-6">
        {readFailed ? (
          <article className="border border-solid border-[#f0f0f0] bg-[#000000] p-5 rounded-none">
            <p className="font-mono text-[11px] font-medium leading-relaxed tracking-widest text-[#ffffff] tabular-nums">
              {AUDIT_OFFLINE_FALLBACK}
            </p>
            <p className="mt-4 font-mono text-[10px] leading-relaxed text-[#a3a3a3] tabular-nums">
              Serverless or path isolation prevented reading the live transcript. Full archive: repository{' '}
              <code className="text-[#e5e5e5]">chat.md</code> on GitHub.
            </p>
          </article>
        ) : null}
        {!readFailed
          ? sections.map((block, i) => {
              const trimmed = block.trim();
              if (!trimmed) return null;
              const lines = trimmed.split('\n');
              const first = lines[0] ?? '';
              const isH2 = first.startsWith('## ');
              const title = isH2 ? first.replace(/^##\s+/, '').trim() : null;
              const body = isH2 ? lines.slice(1).join('\n').trim() : trimmed;

              return (
                <article
                  key={i}
                  className="border border-solid border-[#222] bg-[#000000] p-4 rounded-none"
                >
                  {title ? (
                    <h2 className="mb-2 border-b border-solid border-[#1a1a1a] pb-2 font-mono text-[10px] font-normal tracking-widest text-[#888] tabular-nums">
                      {title}
                    </h2>
                  ) : null}
                  <div className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-[#9a9a9a] tabular-nums">
                    {body}
                  </div>
                </article>
              );
            })
          : null}
      </div>
    </main>
  );
}
