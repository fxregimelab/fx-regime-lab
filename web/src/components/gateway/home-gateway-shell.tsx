'use client';

import { AnimatePresence, motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { TerminalNav } from '@/components/layout/terminal-nav';
import { TerminalHomeDashboard } from '@/components/terminal/terminal-home-dashboard';
import type { GatewayLandingPayload } from '@/lib/queries';
import { HomeLandingBody } from '@/components/gateway/home-landing-body';

export function HomeGatewayShell({
  initial,
  children,
}: {
  initial: GatewayLandingPayload;
  children: ReactNode;
}) {
  const [gate, setGate] = useState(true);

  return (
    <div className="relative min-h-[100dvh] bg-[#000000]">
      <motion.div
        className="relative z-10 min-h-[100dvh] bg-[#000000] will-change-[filter,transform]"
        initial={false}
        animate={
          gate
            ? { opacity: 1, scale: 1.05, filter: 'blur(10px)' }
            : { opacity: 1, scale: 1, filter: 'blur(0px)' }
        }
        transition={{ duration: 0.4, ease: 'easeOut' }}
        aria-hidden={gate}
      >
        <TerminalNav />
        <TerminalHomeDashboard />
      </motion.div>

      <AnimatePresence>
        {gate ? (
          <motion.div
            key="gateway-overlay"
            className="fixed inset-0 z-[200] bg-[#000000] overflow-y-auto"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          >
            <HomeLandingBody initial={initial} memosSlot={children} onAccessTerminal={() => setGate(false)} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
