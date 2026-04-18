'use client';

import { useEffect, useState } from 'react';

type PipelineStatusJson = {
  last_run_utc?: string;
};

function formatPipelineUtc(iso: string | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const y = d.getUTCFullYear();
  const mo = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  const h = String(d.getUTCHours()).padStart(2, '0');
  const min = String(d.getUTCMinutes()).padStart(2, '0');
  return `${y}-${mo}-${day} ${h}:${min} UTC`;
}

export function PipelineStatus() {
  const [line, setLine] = useState('—');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/data/pipeline_status.json', { cache: 'no-store' });
        if (!res.ok) {
          if (!cancelled) setLine('—');
          return;
        }
        const json = (await res.json()) as PipelineStatusJson;
        const formatted = formatPipelineUtc(json.last_run_utc);
        if (!cancelled) setLine(formatted);
      } catch {
        if (!cancelled) setLine('—');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <p className="mt-6 font-mono text-xs text-neutral-500">
      Pipeline last run: {line}
    </p>
  );
}
