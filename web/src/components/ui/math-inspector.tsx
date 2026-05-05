'use client';

import { useMemo, useState } from 'react';
import type { TelemetryAuditPayload } from '@/lib/queries';

type MathInspectorProps = {
  telemetryAudit: TelemetryAuditPayload | null;
};

function fmt(n: number | null | undefined, d = 4): string {
  if (n == null || Number.isNaN(n)) return '';
  return n.toFixed(d);
}

function thermalClass(n: number | null): string {
  if (n == null) return '';
  if (n > 0) return 'bg-emerald-500/5';
  if (n < 0) return 'bg-rose-500/5';
  return '';
}

function LogicArrow() {
  return (
    <span className="shrink-0 font-mono text-[10px] text-[#444] tabular-nums select-none" aria-hidden>
      ─→
    </span>
  );
}

function LogicNode({
  label,
  valueStr,
  valueNum,
}: {
  label: string;
  valueStr: string | null;
  valueNum: number | null;
}) {
  const pending = valueStr == null || valueStr === '';
  const wash = pending ? '' : thermalClass(valueNum);

  if (pending) {
    return (
      <div
        className="min-w-[7rem] border border-dashed border-[#333] bg-[#000000] px-2 py-1.5 font-mono text-[9px] tracking-widest text-[#666] will-change-[background]"
        title="Data pending"
      >
        <span className="block text-[#555]">[ {label} ]</span>
        <span className="mt-1 block text-[#d4d4d4]">[ DATA_PENDING ]</span>
      </div>
    );
  }

  return (
    <div
      className={`min-w-[7rem] border border-[#222] px-2 py-1.5 font-mono text-[9px] tracking-widest text-[#d4d4d4] will-change-[background] ${wash}`}
    >
      <span className="block text-[#555]">[ {label} ]</span>
      <span className="mt-1 block tabular-nums">{valueStr}</span>
    </div>
  );
}

export function MathInspector({ telemetryAudit }: MathInspectorProps) {
  const [open, setOpen] = useState(false);

  const chain = useMemo(() => {
    const a = telemetryAudit;
    const zT = a?.rate_z_tactical_mad ?? null;
    const zS = a?.rate_z_structural_mad ?? null;
    let sp: number | null = null;
    let spDigits = 4;
    if (a?.overnight_day_change_pct != null && !Number.isNaN(a.overnight_day_change_pct)) {
      sp = a.overnight_day_change_pct;
      spDigits = 2;
    } else if (
      zT != null &&
      zS != null &&
      !Number.isNaN(zT) &&
      !Number.isNaN(zS)
    ) {
      sp = zS - zT;
      spDigits = 4;
    }
    const beta = a?.dynamic_beta ?? null;

    return {
      nodes: [
        { label: 'Z-TACTICAL', num: zT, str: zT != null && !Number.isNaN(zT) ? fmt(zT) : null },
        { label: 'Z-STRUCTURAL', num: zS, str: zS != null && !Number.isNaN(zS) ? fmt(zS) : null },
        {
          label: 'SPREAD',
          num: sp,
          str: sp != null && !Number.isNaN(sp) ? fmt(sp, spDigits) : null,
        },
        { label: 'DYN-BETA', num: beta, str: beta != null && !Number.isNaN(beta) ? fmt(beta) : null },
      ] as const,
    };
  }, [telemetryAudit]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="border-0 border-t-[0.5px] border-t-white/[0.08] border-l-[0.5px] border-l-white/[0.03] bg-[#000000] px-2 py-1 font-mono text-[12px] text-[#d4d4d4] shadow-none hover:text-[#ffffff]"
        aria-label="Open math inspector"
      >
        [ ∫ ]
      </button>
      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#000000]/90 p-4">
          <div className="w-full max-w-3xl border border-[#222] bg-[#000000] shadow-none">
            <div className="flex items-center justify-between border-b border-[#222] px-3 py-2">
              <p className="font-mono text-[11px] text-[#e8e8e8] tracking-widest">[ LOGIC CHAIN · INSPECTOR ]</p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="border border-[#222] bg-[#000000] px-2 py-1 font-mono text-[10px] text-[#9b9b9b] hover:text-[#ffffff]"
              >
                [ CLOSE ]
              </button>
            </div>
            <div className="p-4">
              <p className="mb-3 font-mono text-[9px] tracking-widest text-[#555]">FORMULA NARRATIVE</p>
              <div className="flex flex-wrap items-stretch gap-x-1 gap-y-3">
                {chain.nodes.map((node, i) => (
                  <div key={node.label} className="flex flex-wrap items-center gap-x-1 gap-y-2">
                    {i > 0 ? <LogicArrow /> : null}
                    <LogicNode label={node.label} valueStr={node.str} valueNum={node.num} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
