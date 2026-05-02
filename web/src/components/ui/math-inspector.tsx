'use client';

import { useMemo, useState } from 'react';
import type { TelemetryAuditPayload } from '@/lib/queries';

type MathInspectorProps = {
  telemetryAudit: TelemetryAuditPayload | null;
};

export function MathInspector({ telemetryAudit }: MathInspectorProps) {
  const [open, setOpen] = useState(false);
  const payload = useMemo(
    () => JSON.stringify(telemetryAudit ?? { status: 'NO_TELEMETRY_AUDIT' }, null, 2),
    [telemetryAudit],
  );

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="font-mono text-[12px] text-[#d4d4d4] border border-[#222] px-2 py-1 bg-[#000000] hover:text-[#ffffff]"
        aria-label="Open math inspector"
      >
        [ ∫ ]
      </button>
      {open ? (
        <div className="fixed inset-0 z-50 bg-[#000000]/90 flex items-center justify-center p-4">
          <div className="w-full max-w-3xl border border-[#222] bg-[#000000]">
            <div className="flex items-center justify-between border-b border-[#222] px-3 py-2">
              <p className="font-mono text-[11px] text-[#e8e8e8] tracking-widest">
                [ RADICAL TRANSPARENCY INSPECTOR ]
              </p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="font-mono text-[10px] text-[#9b9b9b] border border-[#222] px-2 py-1 bg-[#000000] hover:text-[#ffffff]"
              >
                [ CLOSE ]
              </button>
            </div>
            <pre className="p-4 text-[11px] font-mono text-[#cfcfcf] overflow-auto max-h-[60vh]">
              {payload}
            </pre>
          </div>
        </div>
      ) : null}
    </>
  );
}
