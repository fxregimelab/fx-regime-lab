'use client';

import { useEffect, useId, useState } from 'react';
import { PAIRS } from '@/lib/mockData';
import { useConnectDeskWebhook } from '@/lib/queries';

type ConnectDeskModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

/** Monochrome desk webhook bridge (Slack / Discord / Symphony). */
export function ConnectDeskModal({ open, onOpenChange }: ConnectDeskModalProps) {
  const titleId = useId();
  const { mutate, reset, isPending, isError, error } = useConnectDeskWebhook();
  const [url, setUrl] = useState('');
  const [pairFilter, setPairFilter] = useState<string>('');

  useEffect(() => {
    if (open) reset();
  }, [open, reset]);

  if (!open) return null;

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutate(
      { webhookUrl: url.trim(), pairFilter: pairFilter || null },
      {
        onSuccess: () => {
          setUrl('');
          onOpenChange(false);
        },
      },
    );
  };

  return (
    <div
      className="fixed inset-0 z-[250] flex items-center justify-center bg-black/90 p-4"
      role="presentation"
      onClick={() => onOpenChange(false)}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative w-full max-w-md border border-solid border-[#222] bg-[#000000] p-5 rounded-none"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className="font-mono text-[10px] font-normal tracking-widest text-[#888]">
          [ CONNECT YOUR DESK ]
        </h2>
        <p className="mt-3 font-mono text-[10px] leading-relaxed text-[#666]">
          No accounts. No trackers. We only store an encrypted link to your desk for the 07:05 AM
          snapshot.
        </p>
        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          <div>
            <label htmlFor="desk-webhook-url" className="block font-mono text-[9px] tracking-widest text-[#555] mb-1">
              WEBHOOK URL (HTTPS)
            </label>
            <input
              id="desk-webhook-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              autoComplete="off"
              placeholder="https://hooks.slack.com/…"
              className="w-full border border-solid border-[#333] bg-[#000000] px-2 py-2 font-mono text-[11px] text-[#ccc] outline-none focus:border-[#555] rounded-none"
            />
          </div>
          <div>
            <label htmlFor="desk-pair-filter" className="block font-mono text-[9px] tracking-widest text-[#555] mb-1">
              PAIR FILTER (OPTIONAL)
            </label>
            <select
              id="desk-pair-filter"
              value={pairFilter}
              onChange={(e) => setPairFilter(e.target.value)}
              className="w-full border border-solid border-[#333] bg-[#000000] px-2 py-2 font-mono text-[11px] text-[#ccc] rounded-none"
            >
              <option value="">All pairs</option>
              {PAIRS.map((p) => (
                <option key={p.label} value={p.label}>
                  {p.display}
                </option>
              ))}
            </select>
          </div>
          {isError ? (
            <p className="font-mono text-[10px] text-[#c45] tabular-nums">
              {(error as Error).message}
            </p>
          ) : null}
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={isPending}
              className="border border-solid border-[#444] bg-[#0a0a0a] px-3 py-2 font-mono text-[10px] tracking-widest text-[#ddd] hover:border-[#666] disabled:opacity-50 rounded-none"
            >
              {isPending ? 'SENDING…' : 'REGISTER'}
            </button>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="border border-solid border-[#333] bg-transparent px-3 py-2 font-mono text-[10px] tracking-widest text-[#888] hover:text-[#ccc] rounded-none"
            >
              CLOSE
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
