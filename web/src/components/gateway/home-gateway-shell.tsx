'use client';

import { AnimatePresence, motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { useEffect, useRef, useState } from 'react';
import { TerminalNav } from '@/components/layout/terminal-nav';
import { TerminalHomeDashboard } from '@/components/terminal/terminal-home-dashboard';
import type { GatewayLandingPayload } from '@/lib/queries';
import { HomeLandingBody } from '@/components/gateway/home-landing-body';

const INGRESS_DURATION_S = 0.45;
const INGRESS_EASE = [0.16, 1, 0.3, 1] as const;
const RAIL_INGRESS_FLAG = 'fxrl-rail-ingress';

function VaultHandshake() {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setPhase((p) => p + 1), 90);
    const t = window.setTimeout(() => clearInterval(iv), INGRESS_DURATION_S * 1000);
    return () => {
      clearInterval(iv);
      window.clearTimeout(t);
    };
  }, []);
  const msg =
    phase % 2 === 0
      ? '[ INITIALIZING G10_SESSION... ]'
      : '[ DECRYPTING_VAULT_KEYS... ]';
  return (
    <p className="pointer-events-none m-0 max-w-[90vw] text-center font-mono text-[10px] tracking-widest text-[#a3a3a3] will-change-[contents] tabular-nums">
      {msg}
    </p>
  );
}

export function HomeGatewayShell({
  initial,
  children,
}: {
  initial: GatewayLandingPayload;
  children: ReactNode;
}) {
  const [gate, setGate] = useState(true);
  const [isEntering, setIsEntering] = useState(false);
  const gatewayScrollRef = useRef<HTMLDivElement>(null);

  const openVault = () => {
    try {
      sessionStorage.setItem(RAIL_INGRESS_FLAG, '1');
    } catch {
      /* private mode */
    }
    setIsEntering(true);
    setGate(false);
    window.setTimeout(() => setIsEntering(false), INGRESS_DURATION_S * 1000);
  };

  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-[var(--bg-void)]">
      <motion.div
        className="relative z-10 flex min-h-0 flex-1 flex-col overflow-hidden bg-[var(--bg-void)] will-change-[filter,transform,opacity]"
        initial={false}
        animate={
          gate
            ? { opacity: 0, scale: 1.05, filter: 'blur(20px)' }
            : { opacity: 1, scale: 1, filter: 'blur(0px)' }
        }
        transition={{ duration: INGRESS_DURATION_S, ease: INGRESS_EASE }}
        aria-hidden={gate}
      >
        <TerminalNav />
        <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
          <TerminalHomeDashboard />
        </div>
      </motion.div>

      <AnimatePresence>
        {gate ? (
          <motion.div
            key="gateway-overlay"
            ref={gatewayScrollRef}
            className="fixed inset-0 z-[200] bg-[var(--bg-void)] overflow-y-auto overflow-x-hidden"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, ease: INGRESS_EASE }}
          >
            <HomeLandingBody
              initial={initial}
              memosSlot={children}
              onAccessTerminal={openVault}
              scrollContainerRef={gatewayScrollRef}
            />
          </motion.div>
        ) : null}
      </AnimatePresence>

      {isEntering && !gate ? (
        <div
          className="pointer-events-none fixed inset-0 z-[250] flex items-center justify-center bg-transparent"
          aria-live="polite"
        >
          <VaultHandshake />
        </div>
      ) : null}
    </div>
  );
}
