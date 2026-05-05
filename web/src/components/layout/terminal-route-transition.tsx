'use client';

import type { ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { usePathname } from 'next/navigation';

/** Route-level depth transition for terminal subtree (pair desk, ledger, radar, memos). */
export function TerminalRouteTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname() || '';

  return (
    <div className="relative min-h-0 flex-1 overflow-hidden">
      <AnimatePresence mode="wait">
        <motion.div
          key={pathname}
          initial={{ scale: 0.98, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 1.02, opacity: 0 }}
          transition={{ duration: 0.22, ease: [0.25, 0.1, 0.25, 1] }}
          className="min-h-0 h-full overflow-y-auto overflow-x-hidden shadow-none"
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
