'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
import {
  applyVaultImportJson,
  buildVaultExportJson,
  FX_VAULT_STATUS_SUCCESS,
  useLocalSettings,
} from '@/hooks/useLocalSettings';
import { useVerified90dEdge } from '@/lib/queries';

const W_COLLAPSED = 54;
const W_EXPANDED = 160;
const RAIL_INGRESS_FLAG = 'fxrl-rail-ingress';
const INGRESS_EASE = [0.16, 1, 0.3, 1] as const;

type RailEntryProps = {
  href: string;
  letter: string;
  label: string;
  active: boolean;
  expanded: boolean;
};

function RailEntry({ href, letter, label, active, expanded }: RailEntryProps) {
  return (
    <Link
      href={href}
      title={label}
      aria-current={active ? 'page' : undefined}
      className={`relative flex h-9 min-w-0 items-center gap-2 overflow-hidden rounded-none border-0 border-t-[0.5px] border-t-white/[0.08] border-l-[0.5px] border-l-white/[0.03] px-1.5 no-underline shadow-none transition-[background-color,color,border-color] hover:border-t-white/[0.12] ${
        active ? 'bg-[#080808] text-[#e8e8e8]' : 'bg-[#000000] text-[#888] hover:text-[#e8e8e8]'
      }`}
    >
      {active ? (
        <span
          className="pointer-events-none absolute left-0 top-0 bottom-0 w-[3px] bg-emerald-500 will-change-transform"
          aria-hidden
        />
      ) : null}
      <span className="relative z-[1] flex h-7 w-7 shrink-0 items-center justify-center font-mono text-[11px] font-bold tabular-nums">
        {letter}
      </span>
      <motion.span
        className="relative z-[1] min-w-0 font-mono text-[9px] font-normal tracking-widest text-[#888]"
        initial={false}
        animate={{
          opacity: expanded ? 1 : 0,
          maxWidth: expanded ? 120 : 0,
        }}
        transition={{ duration: 0.18, ease: [0.25, 0.1, 0.25, 1] }}
        style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}
      >
        {label}
      </motion.span>
    </Link>
  );
}

/** Hover-expanding tool rail: overlays charts without resizing main column; 54px spacer in layout. */
export function TerminalContextRail() {
  const [ingressX, setIngressX] = useState(0);
  const [hover, setHover] = useState(false);
  const { sidebarExpanded, setSettings } = useLocalSettings();
  const fileRef = useRef<HTMLInputElement>(null);
  const [vaultMsg, setVaultMsg] = useState<string | null>(null);
  const [importAck, setImportAck] = useState(false);
  const path = usePathname() || '';

  useEffect(() => {
    try {
      if (sessionStorage.getItem(RAIL_INGRESS_FLAG) === '1') {
        sessionStorage.removeItem(RAIL_INGRESS_FLAG);
        setIngressX(-54);
        requestAnimationFrame(() => {
          requestAnimationFrame(() => setIngressX(0));
        });
      }
    } catch {
      /* private mode */
    }
  }, []);

  useEffect(() => {
    let hide: ReturnType<typeof setTimeout> | undefined;
    const onVaultImportOk = () => {
      setImportAck(true);
      if (hide) clearTimeout(hide);
      hide = setTimeout(() => setImportAck(false), 2000);
    };
    window.addEventListener(FX_VAULT_STATUS_SUCCESS, onVaultImportOk);
    return () => {
      window.removeEventListener(FX_VAULT_STATUS_SUCCESS, onVaultImportOk);
      if (hide) clearTimeout(hide);
    };
  }, []);
  const edgeQ = useVerified90dEdge();
  const edgePct = edgeQ.data?.hitRatePct != null ? edgeQ.data.hitRatePct.toFixed(1) : null;
  const railWide = hover || sidebarExpanded;

  const apex = path === '/terminal';
  const radar = path.startsWith('/terminal/calendar');
  const ledger = path.startsWith('/terminal/performance');
  const memos = path.startsWith('/terminal/memos');

  return (
    <motion.aside
      className="absolute left-0 top-0 z-[100] flex h-full min-h-full flex-col border-r border-[#111] bg-[#000000] will-change-transform"
      initial={false}
      animate={{ width: railWide ? W_EXPANDED : W_COLLAPSED, x: ingressX }}
      transition={{
        width: { duration: 0.22, ease: [0.25, 0.1, 0.25, 1] },
        x: { duration: 0.45, ease: INGRESS_EASE },
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      aria-label="Terminal context"
    >
      <div className="flex min-h-0 flex-1 flex-col gap-2 px-1.5 pt-3">
        <RailEntry
          href="/terminal"
          letter="A"
          label="APEX TARGET"
          active={apex}
          expanded={railWide}
        />
        <RailEntry
          href="/terminal/calendar"
          letter="R"
          label="EVENT RADAR"
          active={radar}
          expanded={railWide}
        />
        <RailEntry
          href="/terminal/performance"
          letter="L"
          label="ALPHA LEDGER"
          active={ledger}
          expanded={railWide}
        />
        <RailEntry
          href="/terminal/memos"
          letter="M"
          label="MACRO MEMO"
          active={memos}
          expanded={railWide}
        />
      </div>
      <div className="mt-auto shrink-0 border-t border-[#111] p-2 space-y-1.5">
        <button
          type="button"
          title={sidebarExpanded ? 'Unpin rail' : 'Pin rail open'}
          onClick={() => setSettings({ sidebarExpanded: !sidebarExpanded })}
          className={`relative w-full border-0 border-t-[0.5px] border-t-white/[0.08] border-l-[0.5px] border-l-white/[0.03] bg-[#000000] py-1.5 font-mono text-[8px] tracking-[0.15em] transition-all omega-haptic rounded-none flex items-center justify-center gap-2 ${
            sidebarExpanded ? 'text-emerald-500' : 'text-[#666] hover:text-[#999]'
          }`}
        >
          {sidebarExpanded ? (
            <span className="h-1 w-1 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
          ) : null}
          [ {sidebarExpanded ? 'RAIL_LOCKED' : 'RAIL_HOVER'} ]
        </button>
        <div className="flex items-stretch gap-1">
          <span className="min-w-0 flex-1 border-0 border-t-[0.5px] border-t-white/[0.08] border-l-[0.5px] border-l-white/[0.03] bg-[#000000] px-1.5 py-1 font-mono text-[9px] leading-snug tracking-widest text-[#a3a3a3] tabular-nums">
            [ EDGE: {edgePct != null ? `${edgePct}%` : '—'} ]
          </span>
          <button
            type="button"
            title="Export vault key"
            onClick={() => {
              setVaultMsg(null);
              const blob = new Blob([buildVaultExportJson()], { type: 'application/json' });
              const a = document.createElement('a');
              const u = URL.createObjectURL(blob);
              a.href = u;
              a.download = 'fx_regime_vault_key.json';
              a.click();
              URL.revokeObjectURL(u);
            }}
            className="shrink-0 border-0 border-t-[0.5px] border-t-white/[0.08] border-l-[0.5px] border-l-white/[0.03] bg-[#000000] px-1.5 font-mono text-[11px] text-[#888] hover:text-[#ccc] rounded-none omega-haptic"
          >
            ↑
          </button>
          <button
            type="button"
            title="Import vault key"
            onClick={() => fileRef.current?.click()}
            className={`shrink-0 min-w-[2.25rem] border-0 border-t-[0.5px] border-t-white/[0.08] border-l-[0.5px] border-l-white/[0.03] bg-[#000000] px-1 font-mono text-[10px] rounded-none omega-haptic ${
              importAck ? 'text-emerald-500' : 'text-[#888] hover:text-[#ccc]'
            }`}
          >
            {importAck ? '[ OK! ]' : '↓'}
          </button>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={async (e) => {
            const f = e.target.files?.[0];
            e.target.value = '';
            if (!f) return;
            const text = await f.text();
            const r = applyVaultImportJson(text);
            setVaultMsg(r.ok ? 'Vault restored.' : r.error);
          }}
        />
        {vaultMsg ? (
          <p className="font-mono text-[8px] tracking-widest text-[#777]">{vaultMsg}</p>
        ) : null}
      </div>
    </motion.aside>
  );
}
