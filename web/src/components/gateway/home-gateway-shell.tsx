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
    <div className="relative min-h-screen bg-[#000000]">
      <motion.div
        className="relative z-10 min-h-screen bg-[#000000]"
        initial={false}
        animate={gate ? { opacity: 0, scale: 1.05 } : { opacity: 1, scale: 1 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1], delay: gate ? 0 : 0.06 }}
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
            initial={{ y: 0, opacity: 1 }}
            exit={{ y: '-100%', opacity: 0 }}
            transition={{ duration: 0.52, ease: [0.22, 1, 0.36, 1] }}
          >
            <HomeLandingBody initial={initial} memosSlot={children} onAccessTerminal={() => setGate(false)} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
