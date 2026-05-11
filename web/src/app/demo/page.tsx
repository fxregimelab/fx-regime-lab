"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import React from "react";

export default function DemoHomePage() {
  const containerVars = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 },
    },
  };

  const itemVars = {
    hidden: { opacity: 0, y: 20 },
    show: {
      opacity: 1,
      y: 0,
      transition: { type: "spring" as const, stiffness: 100, damping: 15 },
    },
  };

  return (
    <motion.div
      className="flex flex-col items-center justify-center min-h-[80vh] text-center"
      variants={containerVars}
      initial="hidden"
      animate="show"
    >
      <motion.div
        variants={itemVars}
        className="mb-6 inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5"
      >
        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        <span className="text-xs font-mono text-white/70">
          System Operational
        </span>
      </motion.div>

      <motion.h1
        variants={itemVars}
        className="text-5xl md:text-7xl font-bold tracking-tighter mb-6 bg-gradient-to-br from-white to-white/40 bg-clip-text text-transparent"
      >
        Predictive Alpha for <br className="hidden md:block" /> FX Regimes
      </motion.h1>

      <motion.p
        variants={itemVars}
        className="text-lg text-white/50 max-w-2xl mb-10 font-light leading-relaxed"
      >
        Institutional-grade daily forecasts powered by rate differentials, COT
        positioning, and realized volatility. Validated out-of-sample. Immutable
        ledger.
      </motion.p>

      <motion.div variants={itemVars} className="flex gap-4">
        <Link
          href="/demo/terminal"
          className="px-6 py-3 rounded bg-white text-black font-medium text-sm hover:bg-white/90 transition-colors"
        >
          Launch Terminal
        </Link>
        <Link
          href="/demo/performance"
          className="px-6 py-3 rounded border border-white/20 text-white font-medium text-sm hover:bg-white/10 transition-colors"
        >
          View Track Record
        </Link>
      </motion.div>

      <motion.div
        variants={itemVars}
        className="mt-32 grid grid-cols-2 md:grid-cols-4 gap-8 w-full border-t border-white/10 pt-10"
      >
        {[
          { label: "Pairs Tracked", value: "3" },
          { label: "Total Calls", value: "1,248" },
          { label: "7D Accuracy", value: "82.4%" },
          { label: "Max Drawdown", value: "-1.2%" },
        ].map((stat) => (
          <div key={stat.label} className="text-left">
            <p className="text-3xl font-mono mb-2">{stat.value}</p>
            <p className="text-[10px] uppercase tracking-widest text-white/40 font-mono">
              {stat.label}
            </p>
          </div>
        ))}
      </motion.div>
    </motion.div>
  );
}
